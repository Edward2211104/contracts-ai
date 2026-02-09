# src/answerer/rag_api.py
import json, requests
from pathlib import Path
from fastapi import FastAPI, Body
from pydantic import BaseModel
import faiss, numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT/'data'/'index'/'faiss.index'
META  = ROOT/'data'/'index'/'meta.json'
PROMPT = (ROOT/'prompts'/'contract_qa.txt').read_text(encoding='utf-8')

OLLAMA = 'http://127.0.0.1:11434'
LLM_MODEL = 'llama3.1:latest'

app = FastAPI(title='Contracts-RAG')

class AskIn(BaseModel):
    question: str
    top_k: int = 6

def load_index():
    idx = faiss.read_index(str(INDEX))
    meta = json.loads(META.read_text(encoding='utf-8'))
    model = SentenceTransformer(meta.get("model", "nomic-embed-text:latest"))
    recs = meta["records"]
    return idx, model, recs

index, embedder, records = load_index()

@app.get('/health')
def health():
    return {"ok": True, "records": len(records)}

@app.post('/ask')
def ask(inp: AskIn):
    q = inp.question.strip()
    qemb = embedder.encode([q], convert_to_numpy=True, normalize_embeddings=True).astype('float32')
    D, I = index.search(qemb, inp.top_k)
    hits = [records[i] for i in I[0] if i < len(records)]

    # Build snippets with ids
    snippets = []
    for j, h in enumerate(hits, start=1):
        snippets.append(f"- [c{j}] \"{h['text'].replace('\"','\\\"')[:1200]}\" (doc {h['doc_id']} clause {h['clause_id']})")

    user = f"QUESTION: \"{q}\"\nSNIPPETS:\n" + "\n".join(snippets) + "\n[OUTPUT ONLY JSON]"
    prompt = f"{PROMPT}\n\n{user}"

    # Call Ollama
    r = requests.post(f"{OLLAMA}/api/generate",
                      json={"model": LLM_MODEL, "prompt": prompt, "stream": False})
    if r.status_code != 200:
        return {"ok": False, "error": r.text}

    txt = r.json().get("response","").strip()
    # Try parse JSON response
    try:
        data = json.loads(txt)
        return {"ok": True, "answer": data, "snippets": hits}
    except:
        return {"ok": True, "raw": txt, "snippets": hits}
