from fastapi.responses import Response
import os
import logging
from typing import Optional

import httpx
from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

# --- Logging básico ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("contracts-llm-backend")

# --- Configuración de LM Studio ---
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://127.0.0.1:1234")
LM_MODEL = os.getenv("LM_MODEL", "deepseek-r1-distill-llama-8b:3")

app = FastAPI(title="Contracts LLM Backend")


# BEGIN_FORCE_OPTIONS_CORS_PATCH
# Fix browser CORS preflight: OPTIONS /llm/ask-basic was returning 405
@app.middleware("http")
async def _force_options_cors(request: Request, call_next):
    origin = request.headers.get("origin")
    req_hdrs = request.headers.get("access-control-request-headers", "content-type")
    allow_origin = origin if origin else "*"

    if request.method.upper() == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": allow_origin,
            "Vary": "Origin",
            "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": req_hdrs,
            "Access-Control-Max-Age": "86400",
        }
        return Response(status_code=204, headers=headers)

    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = allow_origin
    response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response
# END_FORCE_OPTIONS_CORS_PATCH

class AskRequest(BaseModel):
    question: str
    contractText: Optional[str] = ""
    extraContext: Optional[str] = ""

class AskResponse(BaseModel):
    ok: bool
    answer: Optional[str] = None
    error: Optional[str] = None
    detail: Optional[str] = None

def build_user_prompt(question: str, contract_text: str, extra_context: str) -> str:
    """
    Construye el prompt para el modelo, limitando el tamaño del contrato
    para evitar errores de contexto en LM Studio.
    """
    contract_text = (contract_text or "").strip()
    extra_context = (extra_context or "").strip()
    question = (question or "").strip()

    # Limitar longitud del contrato (en caracteres) para no explotar el contexto
    max_chars = 16000
    if len(contract_text) > max_chars:
        contract_text = contract_text[-max_chars:]

    user_content = f"""You are a senior contracts lawyer. Answer clearly, in plain English.

CONTRACT TEXT (may be truncated):
{contract_text}

EXTRA CONTEXT (metadata or notes, may be empty):
{extra_context}

QUESTION:
{question}
"""
    return user_content

@app.post("/llm/ask-basic", response_model=AskResponse)
async def ask_basic(req: AskRequest) -> AskResponse:
    """
    Endpoint principal llamado por el servidor Node (server.js) y por la UI.
    """
    question = (req.question or "").strip()
    if not question:
        return AskResponse(ok=False, error="missing_question", detail="Question is empty.")

    contract_text = req.contractText or ""
    extra_context = req.extraContext or ""

    user_prompt = build_user_prompt(question, contract_text, extra_context)

    payload = {
        "model": LM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert contract lawyer. "
                    "You explain risks, clauses, and negotiation strategy in clear, concise language."
                ),
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        "temperature": 0.2,
        "max_tokens": 512,
    }

    logger.info("contracts-llm-backend: Calling LM Studio at %s/v1/chat/completions with model=%s", LM_STUDIO_URL, LM_MODEL)
    print(f"DEBUG: Calling LM Studio at {LM_STUDIO_URL}/v1/chat/completions model={LM_MODEL}", flush=True)

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(f"{LM_STUDIO_URL}/v1/chat/completions", json=payload)
            status = resp.status_code
            logger.info("contracts-llm-backend: LM Studio HTTP %s", status)
            print(f"DEBUG: LM Studio HTTP {status}", flush=True)
            # Guardar texto de respuesta recortado para debug
            preview = resp.text[:400].replace("\n", " ")
            logger.info("contracts-llm-backend: LM Studio response preview: %s", preview)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        msg = f"LM Studio HTTP error: {e}"
        logger.error("contracts-llm-backend: %s", msg)
        print("ERROR:", msg, flush=True)
        return AskResponse(ok=False, error="lm_http_error", detail=msg)
    except Exception as e:
        msg = f"Unexpected backend exception: {e}"
        logger.exception("contracts-llm-backend: %s", msg)
        print("ERROR:", msg, flush=True)
        return AskResponse(ok=False, error="backend_exception", detail=msg)

    try:
        answer = data["choices"][0]["message"]["content"]
    except Exception as e:
        msg = f"Could not parse LM Studio response: {e}"
        logger.exception("contracts-llm-backend: %s", msg)
        print("ERROR:", msg, flush=True)
        return AskResponse(ok=False, error="parse_error", detail=msg)

    return AskResponse(ok=True, answer=answer)

@app.get("/health")
async def health():
    return {"status": "ok", "lm_studio_url": LM_STUDIO_URL, "model": LM_MODEL}

if __name__ == "__main__":
    # Arrancar Uvicorn cuando ejecutas: python .\simple_backend.py
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=4050,
        log_level="info",
    )

