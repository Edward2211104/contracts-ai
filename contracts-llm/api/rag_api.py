import os, re, numpy as np, pandas as pd, faiss
from sentence_transformers import SentenceTransformer
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
IDXD = os.path.join(BASE_DIR, "data", "index")
INDEX = os.path.join(IDXD, "faiss.index")
META  = os.path.join(IDXD, "meta.parquet")
if not (os.path.exists(INDEX) and os.path.exists(META)):
    raise RuntimeError("Index not found. Run ingestion first.")

index = faiss.read_index(INDEX)
meta  = pd.read_parquet(META)
model = SentenceTransformer("all-MiniLM-L6-v2")

app = FastAPI(title="Contracts RAG API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"ok": True, "has_index": True, "chunks": int(meta.shape[0])}

@app.post("/search")
def search(question: str = Query(..., min_length=3), k: int = 5):
    if meta.shape[0] == 0:
        raise HTTPException(500, "Empty index")
    emb = model.encode([question], normalize_embeddings=True)
    D, I = index.search(np.asarray(emb, dtype="float32"), k)
    rows = meta.iloc[I[0]].copy()
    rows = rows.assign(score=D[0])
    return {"ok": True, "results": rows.to_dict(orient="records")}

# ---- Simple /ask: extractivo + "riesgo" heurístico + citas  -----------------
def classify_risk(answer:str)->str:
    a = (answer or "").lower()
    if any(w in a for w in ["terminate immediately","material breach","liquidated damages","penalty","default","forfeit"]): return "high"
    if any(w in a for w in ["notice","30 days","cure period","renewal","termination","late fee","indemn"]): return "medium"
    return "low"

@app.post("/ask")
def ask(question: str = Query(..., min_length=3), top_k: int = 12, return_k: int = 5):
    if meta.shape[0] == 0:
        raise HTTPException(500, "Empty index")

    # Retrieve top_k
    qemb = model.encode([question], normalize_embeddings=True)
    D, I = index.search(np.asarray(qemb, dtype="float32"), int(top_k))
    cands = meta.iloc[I[0]].copy()
    cands = cands.assign(score=D[0])

    # "Reranking" simple por score (ya es IP); cortar a return_k
    cands = cands.sort_values("score", ascending=False).head(int(return_k))

    # Respuesta extractiva básica: concatenar fragmentos más relevantes
    snippets = cands["text"].tolist()
    joined = "\n".join(snippets)
    # pequeña extracción de frases que contienen palabras de la pregunta
    toks = [t for t in re.split(r"[^a-zA-Z0-9]+", question.lower()) if t]
    keep = []
    for sent in re.split(r"(?<=[\.\!\?])\s+", joined):
        sL = sent.lower()
        if any(t and t in sL for t in toks):
            keep.append(sent)
        if len(keep) >= 6:
            break
    answer = ("\n".join(keep) or snippets[0] if snippets else "(no context)").strip()

    risk = classify_risk(answer)
    citations = [
        {"owner": r["owner"], "text": r["text"], "score": float(r["score"])}
        for _, r in cands.iterrows()
    ]
    return {"answer": answer, "risk": risk, "citations": citations}