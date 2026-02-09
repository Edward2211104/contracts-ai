import os, re, json, numpy as np, pandas as pd
from tqdm import tqdm

BASE = os.path.dirname(os.path.dirname(__file__))
RAW  = os.path.join(BASE, "data", "raw_pdfs")
IDXD = os.path.join(BASE, "data", "index")
os.makedirs(IDXD, exist_ok=True)
LOGF = os.path.join(IDXD, "ingest.log")

def log(msg):
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(str(msg).rstrip()+"\n")

def read_pdf(path):
    # Try PyMuPDF first
    try:
        import fitz
        doc = fitz.open(path)
        text = []
        for p in doc:
            text.append(p.get_text("text"))
        return "\n".join(text)
    except Exception as e:
        # Fallback: pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            return "\n".join(pages)
        except Exception as e2:
            raise RuntimeError(f"PDF unreadable: {e} // {e2}")

def chunk_text(t, size=800, overlap=200):
    t = re.sub(r"\s+", " ", t or "").strip()
    if not t: return []
    out, i = [], 0
    while i < len(t):
        out.append(t[i:i+size])
        i += (size - overlap)
    return out

def main():
    import faiss
    from sentence_transformers import SentenceTransformer

    pdfs = [f for f in os.listdir(RAW) if f.lower().endswith(".pdf")]
    if not pdfs:
        raise SystemExit(f"No PDFs in {RAW}. Add files and rerun.")

    rows, skipped = [], 0
    for name in tqdm(pdfs, desc="Reading PDFs"):
        path = os.path.join(RAW, name)
        try:
            if os.path.getsize(path) <= 0:
                raise RuntimeError("Empty file")
            text = read_pdf(path)
            if not text.strip():
                raise RuntimeError("No text extracted")
            for ch in chunk_text(text):
                rows.append({"owner": name, "text": ch})
        except Exception as e:
            skipped += 1
            log(f"SKIP {name}: {e}")
            continue

    if not rows:
        raise RuntimeError("No chunks generated. Check PDFs and logs.")

    df = pd.DataFrame(rows)
    meta_path = os.path.join(IDXD, "meta.parquet")
    df.to_parquet(meta_path, index=False)

    model = SentenceTransformer("all-MiniLM-L6-v2")
    vecs = model.encode(df["text"].tolist(), normalize_embeddings=True)
    vecs = np.asarray(vecs, dtype="float32")

    index = faiss.IndexFlatIP(vecs.shape[1])
    index.add(vecs)
    faiss.write_index(index, os.path.join(IDXD, "faiss.index"))

    print(json.dumps({"ok": True, "chunks": int(df.shape[0]), "owners": int(df['owner'].nunique())}, ensure_ascii=False))

if __name__ == "__main__":
    main()