# src/retriever/indexer.py
import os, json, glob, faiss
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[2]
JSONL = ROOT/'data'/'jsonl'
INDEX = ROOT/'data'/'index'
INDEX.mkdir(parents=True, exist_ok=True)

MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'  # fast + decent
embedder = SentenceTransformer(MODEL_NAME)

def load_records():
    recs = []
    for fp in JSONL.glob('*.jsonl'):
        with fp.open('r', encoding='utf-8') as f:
            for line in f:
                try:
                    recs.append(json.loads(line))
                except:
                    pass
    return recs

def run():
    recs = load_records()
    if not recs:
        print('[indexer] No JSONL clause files. Run extractor first.')
        return
    texts = [r['text'] for r in recs]
    embs = embedder.encode(texts, convert_to_numpy=True, show_progress_bar=True, normalize_embeddings=True)
    index = faiss.IndexFlatIP(embs.shape[1])
    index.add(embs.astype('float32'))
    faiss.write_index(index, str(INDEX/'faiss.index'))
    with (INDEX/'meta.json').open('w', encoding='utf-8') as f:
        json.dump({"model": MODEL_NAME, "records": recs}, f)
    print(f"[indexer] Saved index with {len(recs)} clauses.")

if __name__ == '__main__':
    run()
