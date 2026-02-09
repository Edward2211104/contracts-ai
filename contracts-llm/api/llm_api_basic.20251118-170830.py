import os
import json
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import requests

try:
    import openai
except ImportError:
    openai = None

# Cargar variables desde .env.llm si existe
if os.path.exists(".env.llm"):
    load_dotenv(".env.llm")

PROVIDER = (os.getenv("LLM_PROVIDER") or "ollama").lower()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

app = FastAPI(title="Contracts-LLM service", version="0.1.0")

class AskRequest(BaseModel):
    question: str
    contract_text: str
    extra_context: Optional[str] = None

def build_prompt(question: str, contract_text: str, extra_context: Optional[str]) -> str:
    system_prompt = """
You are an expert contract analysis assistant.
You specialize in consignment agreements, leases, and insurance policies.
You must:

1) Identify the most relevant clauses for the question.
2) Answer in clear, simple English for non-lawyers.
3) Quote or reference the exact clause(s) or paragraph(s) you used.
4) If something is not clearly stated in the text, clearly say that it is not specified.
"""
    extra = extra_context or "(none)"
    return f"""
SYSTEM INSTRUCTIONS:
{system_prompt}

USER QUESTION:
\"\"\"{question}\"\"\"

ADDITIONAL CONTEXT (structured data, if any):
{extra}

CONTRACT TEXT (may be truncated):
--------------------
{contract_text}
--------------------

Now provide a concise answer in English, with:
- a short direct answer first (Yes/No or short sentence),
- then bullet points citing the relevant clause(s) or paragraph(s),
- and any important exceptions or limitations.
"""

def ask_openai(prompt: str) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set but LLM_PROVIDER=openai")
    if openai is None:
        raise RuntimeError("openai package is not installed")

    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a contract-specialist AI assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()

def ask_ollama(prompt: str) -> str:
    url = OLLAMA_URL.rstrip("/") + "/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    r = requests.post(url, json=payload, timeout=120)
    if not r.ok:
        raise RuntimeError(f"Ollama error: {r.status_code} {r.text}")
    data = r.json()
    return (data.get("response") or "").strip()

def ask_llm(prompt: str) -> str:
    if PROVIDER == "openai":
        return ask_openai(prompt)
    return ask_ollama(prompt)

@app.get("/health")
async def health():
    return {"status": "ok", "provider": PROVIDER}

@app.post("/llm/ask-basic")
async def llm_ask_basic(body: AskRequest):
    try:
        # Por ahora el chunking/etc se hará en Node o en otra fase;
        # aquí solo construimos el prompt y preguntamos al modelo.
        prompt = build_prompt(body.question, body.contract_text, body.extra_context)
        answer = ask_llm(prompt)
        return {"ok": True, "answer": answer}
    except Exception as e:
        return {"ok": False, "error": str(e)}
