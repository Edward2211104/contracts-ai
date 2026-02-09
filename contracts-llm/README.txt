Next steps:

1) Put PDFs into:
   C:\Users\Usuario\contracts-ai\contracts-llm\data\raw_pdfs

2) Ingest (OCR → extract → index):
   powershell -ExecutionPolicy Bypass -File C:\Users\Usuario\contracts-ai\contracts-llm\scripts\ingest.ps1

3) Run services (Label Studio + RAG API):
   powershell -ExecutionPolicy Bypass -File C:\Users\Usuario\contracts-ai\contracts-llm\scripts\run-services.ps1
   - RAG API docs: http://127.0.0.1:8000/docs

4) Ask the API:
   POST http://127.0.0.1:8000/ask
   {
     "question": "Can I terminate early without penalty?",
     "top_k": 6
   }

5) Backup anytime:
   powershell -ExecutionPolicy Bypass -File C:\Users\Usuario\contracts-ai\contracts-llm\scripts\backup.ps1
