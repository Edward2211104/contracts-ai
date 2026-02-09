"""
build_vector_index.py

Loads processed policy JSON files from data/policies_processed/,
computes embeddings for each chunk using sentence-transformers,
and saves them in data/vector_index/ for later retrieval.

Run with:
    .venv\\Scripts\\python.exe build_vector_index.py
"""

import json
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = BASE_DIR / "data" / "policies_processed"
INDEX_DIR = BASE_DIR / "data" / "vector_index"

INDEX_FILE = INDEX_DIR / "policy_chunks_index.npz"
META_FILE = INDEX_DIR / "policy_chunks_meta.json"

MODEL_NAME = "all-MiniLM-L6-v2"


def load_chunks() -> List[Dict[str, Any]]:
    """Load all chunks from processed policy JSON files."""
    items: List[Dict[str, Any]] = []
    if not PROCESSED_DIR.exists():
        return items

    for json_path in PROCESSED_DIR.glob("*.json"):
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        policy_id = data.get("policy_id", json_path.stem)
        for chunk in data.get("chunks", []):
            items.append(
                {
                    "chunk_id": chunk.get("id"),
                    "policy_id": policy_id,
                    "text": chunk.get("text", ""),
                }
            )
    return items


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    items = load_chunks()
    if not items:
        print(f"[WARN] No processed policy JSON files found in {PROCESSED_DIR}")
        print("       Run ingest_policies.py first.")
        return

    print(f"[INFO] Loaded {len(items)} chunks from processed policies.")
    print(f"[INFO] Loading embedding model '{MODEL_NAME}' ...")
    model = SentenceTransformer(MODEL_NAME)

    texts = [item["text"] for item in items]
    print("[INFO] Computing embeddings...")
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
    )

    np.savez_compressed(INDEX_FILE, embeddings=embeddings)
    with META_FILE.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"[OK] Saved embeddings to {INDEX_FILE}")
    print(f"[OK] Saved metadata to {META_FILE}")
    print("[DONE] Vector index built successfully.")


if __name__ == "__main__":
    main()
