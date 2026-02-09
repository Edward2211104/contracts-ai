"""
ingest_policies.py

Reads insurance policy PDFs from data/policies_raw/,
extracts text, splits into chunks, and saves structured JSON
under data/policies_processed/.

Run with:
    .venv\\Scripts\\python.exe ingest_policies.py
"""

import json
from pathlib import Path
from typing import List

import pdfplumber

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "policies_raw"
OUT_DIR = BASE_DIR / "data" / "policies_processed"

CHUNK_SIZE = 1200   # characters per chunk
CHUNK_OVERLAP = 200 # characters of overlap between chunks


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Simple sliding-window chunking in characters."""
    text = " ".join(text.split())
    n = len(text)
    chunks: List[str] = []
    if n == 0:
        return chunks

    start = 0
    while start < n:
        end = min(start + size, n)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == n:
            break
        start += size - overlap
    return chunks


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from all pages of a PDF using pdfplumber."""
    parts: List[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            if txt.strip():
                parts.append(txt)
    return "\n\n".join(parts).strip()


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = list(RAW_DIR.rglob("*.pdf"))
    if not pdf_files:
        print(f"[WARN] No PDF files found in {RAW_DIR}")
        print("       Put public insurance policies there and run again.")
        return

    print(f"[INFO] Found {len(pdf_files)} PDF file(s) in {RAW_DIR}")

    for pdf_path in pdf_files:
        print(f"[INFO] Processing {pdf_path.name} ...")
        try:
            text = extract_pdf_text(pdf_path)
        except Exception as e:  # noqa: BLE001
            print(f"[ERROR] Failed to read {pdf_path}: {e}")
            continue

        if not text:
            print(f"[WARN] No text extracted from {pdf_path}")
            continue

        chunks = chunk_text(text)
        policy_id = pdf_path.stem

        out_data = {
            "policy_id": policy_id,
            "source_file": str(pdf_path.relative_to(BASE_DIR)),
            "num_chunks": len(chunks),
            "chunks": [
                {
                    "id": f"{policy_id}_{i}",
                    "index": i,
                    "text": chunk,
                }
                for i, chunk in enumerate(chunks)
            ],
        }

        out_path = OUT_DIR / f"{policy_id}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(out_data, f, ensure_ascii=False, indent=2)

        print(f"[OK] Saved processed policy to {out_path}")

    print("[DONE] Policy ingestion finished.")


if __name__ == "__main__":
    main()
