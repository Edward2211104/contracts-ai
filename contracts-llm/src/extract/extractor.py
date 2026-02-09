# src/extract/extractor.py
import os, json, sys, pathlib, re
from pathlib import Path
import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT/'data'/'raw_pdfs'
OCR_PDFS = ROOT/'data'/'ocr_pdfs'
OCR_TXT = ROOT/'data'/'ocr_text'
JSONL = ROOT/'data'/'jsonl'
ONTO = json.loads((ROOT/'data'/'ontology.json').read_text(encoding='utf-8'))

def ensure_dirs():
    for p in [OCR_PDFS, OCR_TXT, JSONL]:
        p.mkdir(parents=True, exist_ok=True)

def doc_to_text(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    parts = []
    for page in doc:
        parts.append(page.get_text("text"))
    return "\n".join(parts)

def naive_clause_split(text: str):
    """Very simple split by headings / common markers; replace with something smarter later."""
    chunks = re.split(r'(?mi)^\s*(section\s+\d+\.?|article\s+\d+\.?|clause\s+\d+\.?)', text)
    out = []
    cur = []
    for ch in chunks:
        if re.match(r'(?mi)^\s*(section|article|clause)\s+\d+\.?', ch or ""):
            if cur:
                out.append("\n".join(cur).strip())
                cur = []
        cur.append(ch)
    if cur: out.append("\n".join(cur).strip())
    # fallback if nothing split:
    if len(out) <= 1: out = re.split(r'\n{2,}', text)
    return [c.strip() for c in out if c.strip()]

def tag_clause_id(clause: str):
    """Heuristic tag using ontology signals."""
    clause_l = clause.lower()
    for ct in ONTO["clause_types"]:
        if any(sig in clause_l for sig in ct["signals"]):
            return ct["id"]
    return "other"

def run():
    ensure_dirs()
    files = list(RAW.glob('*.pdf'))
    if not files:
        print('[extractor] Put PDFs in data/raw_pdfs and re-run.')
        return
    for pdf in files:
        try:
            text = doc_to_text(pdf)
        except Exception:
            # if PDF is image-based, try OCR’d PDF text (produced by ingest.ps1)
            txt_candidate = (OCR_TXT/pdf.with_suffix('.txt').name)
            if txt_candidate.exists():
                text = txt_candidate.read_text(encoding='utf-8', errors='ignore')
            else:
                print(f'[extractor] No text for {pdf.name}')
                continue
        clauses = naive_clause_split(text)
        out_path = JSONL/(pdf.stem + '.clauses.jsonl')
        with out_path.open('w', encoding='utf-8') as f:
            for i, c in enumerate(clauses):
                cid = tag_clause_id(c)
                rec = {
                    "doc_id": pdf.name,
                    "page": None,
                    "clause_id": cid,
                    "text": c
                }
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        print(f'[extractor] Wrote {out_path} ({len(clauses)} clauses)')

if __name__ == "__main__":
    run()
