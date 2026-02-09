import os
import logging
from typing import Optional, List

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --------------------------------------------------
# Config
# --------------------------------------------------

# Base de LM Studio: NO incluye /v1 ni /chat/completions
LM_BASE_URL = os.getenv("LM_BASE_URL", "http://127.0.0.1:1234")

SYSTEM_PROMPT = (
    "You are ContractAI Pro, a senior contracts lawyer. "
    "You analyze contracts, identify risks, explain clauses in plain language, "
    "and propose concrete redlines / alternative wording when appropriate. "
    "Always be concise, structured with headings and bullet points."
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("contracts-llm")

# --------------------------------------------------
# Modelos de datos
# --------------------------------------------------

class AskRequest(BaseModel):
    question: str
    context: str = ""
    extra_context: Optional[str] = None

class AskResponse(BaseModel):
    ok: bool
    answer: str
    error: Optional[str] = None
    detail: Optional[str] = None

# --------------------------------------------------
# FastAPI app
# --------------------------------------------------

app = FastAPI(title="Contracts-AI LLM Backend", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# Utilidad: descubrir modelo por defecto desde LM Studio
# --------------------------------------------------

_cached_model_id: Optional[str] = None

async def get_default_model_id() -> str:
    global _cached_model_id
    if _cached_model_id:
        return _cached_model_id

    url = f"{LM_BASE_URL}/v1/models"
    logger.info("Querying LLM models from %s", url)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    models: List[dict] = data.get("data") or []
    if not models:
        raise RuntimeError("No models available from LLM server.")

    # coge el primero de la lista
    _cached_model_id = models[0].get("id")
    if not _cached_model_id:
        raise RuntimeError("Could not determine a valid model id from /v1/models response.")

    logger.info("Using LLM model: %s", _cached_model_id)
    return _cached_model_id

# --------------------------------------------------
# Endpoint principal
# --------------------------------------------------

@app.post("/llm/ask-basic", response_model=AskResponse)
async def ask_basic(req: AskRequest) -> AskResponse:
    """
    Punto de entrada que usa el Contracts-AI UI.
    Pregunta + contexto de contrato => llamada a LM Studio => respuesta.
    """
    try:
        # Construir el mensaje de usuario combinando pregunta + contexto
        parts = [req.question.strip()]
        if req.context:
            parts.append("\\n\\n--- CONTRACT TEXT START ---\\n")
            parts.append(req.context.strip())
            parts.append("\\n--- CONTRACT TEXT END ---\\n")
        if req.extra_context:
            parts.append("\\n\\n[Extra context]\\n")
            parts.append(req.extra_context.strip())

        user_content = "\\n".join(parts)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        model_id = await get_default_model_id()

        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 800,
        }

        url = f"{LM_BASE_URL}/v1/chat/completions"
        logger.info("Calling LLM at %s with model %s", url, model_id)

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)

        if resp.status_code != 200:
            text = resp.text
            logger.error("LLM HTTP %s: %s", resp.status_code, text[:500])
            return AskResponse(
                ok=False,
                answer=f"LM call failed with HTTP {resp.status_code}",
                error="lm_http_error",
                detail=text,
            )

        data = resp.json()
        logger.debug("LLM raw response: %s", str(data)[:500])

        choices = data.get("choices") or []
        if not choices:
            return AskResponse(
                ok=False,
                answer="LM call returned no choices.",
                error="no_choices",
                detail=str(data),
            )

        message = choices[0].get("message") or {}
        content = (message.get("content") or "").strip()

        if not content:
            return AskResponse(
                ok=False,
                answer="LM call returned an empty message.",
                error="empty_answer",
                detail=str(data),
            )

        return AskResponse(ok=True, answer=content)

    except Exception as e:
        logger.exception("Unexpected error in /llm/ask-basic")
        return AskResponse(
            ok=False,
            answer="LM call failed unexpectedly.",
            error="exception",
            detail=str(e),
        )

@app.get("/")
async def root():
    return {"status": "ok", "message": "Contracts-AI LLM backend is running."}
