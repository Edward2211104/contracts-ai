import os
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

# Cargar variables de entorno desde .env.llm o .env si existen
for env_file in (".env.llm", ".env"):
    if os.path.exists(env_file):
        load_dotenv(env_file)

LLM_API_BASE = os.getenv("LLM_API_BASE", "http://localhost:1234/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")  # pon aquí el modelo de LM Studio / OpenAI

SYSTEM_PROMPT = """
You are ContractAI Pro, an expert legal contract analyst.
You specialize in:
- Risk analysis and red-flag detection
- Clause review and alternative wording
- Negotiation strategy and trade-offs
- Plain-language explanations for non-lawyers

When answering:
- Always reference specific clauses or sections when possible.
- Be precise, conservative and risk-aware.
- Clearly separate: RISKS, OPPORTUNITIES, RECOMMENDATIONS.
- If something is unclear or missing in the contract, say it explicitly.
"""

app = FastAPI(
    title="Contracts LLM Server",
    description="Specialized LLM API for contract analysis",
    version="0.1.0",
)


class HistoryMessage(BaseModel):
    role: str
    content: str


class ContractChatRequest(BaseModel):
    contract_text: str
    question: str
    history: Optional[List[HistoryMessage]] = None


class ContractChatResponse(BaseModel):
    answer: str
    raw_provider_response: Optional[Dict[str, Any]] = None


@app.get("/health")
async def health() -> Dict[str, str]:
    """Simple health-check endpoint."""
    return {"status": "ok", "message": "contracts-llm server running"}


async def call_llm(messages: List[Dict[str, str]]) -> str:
    """Llama a un endpoint tipo OpenAI / LM Studio."""
    base = LLM_API_BASE.rstrip("/")
    url = f"{base}/chat/completions"

    headers = {}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": 0.15,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Upstream LLM error: {e}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unexpected response format from LLM provider",
        )


@app.post("/chat/contracts", response_model=ContractChatResponse)
async def chat_contracts(body: ContractChatRequest) -> ContractChatResponse:
    """
    Main endpoint para la app:
    - Recibe el texto del contrato
    - Recibe la pregunta del usuario
    - Opcionalmente historial
    - Devuelve respuesta experta
    """
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT.strip()},
    ]

    # Historial previo (si viene del backend)
    if body.history:
        for m in body.history:
            messages.append({"role": m.role, "content": m.content})

    # Mensaje actual con contrato + pregunta
    user_content = (
        "You are analyzing the following contract.\n\n"
        "=== CONTRACT TEXT START ===\n"
        f"{body.contract_text}\n"
        "=== CONTRACT TEXT END ===\n\n"
        f"User question: {body.question}"
    )

    messages.append({"role": "user", "content": user_content})

    answer = await call_llm(messages)
    return ContractChatResponse(answer=answer)
