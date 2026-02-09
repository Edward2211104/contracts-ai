from fastapi.responses import Response
import os
from typing import Optional

import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# =========================
#   CONFIGURACIÓN LLM LOCAL
# =========================

LMSTUDIO_BASE_URL = os.environ.get(
    "LMSTUDIO_BASE_URL",
    "http://127.0.0.1:1234/v1/chat/completions",
)

LMSTUDIO_MODEL = os.environ.get(
    "LMSTUDIO_MODEL",
    "openai/gpt-oss-20b",
)

SYSTEM_PROMPT = (
    "You are ContractAI Pro, an expert assistant that analyzes legal contracts, "
    "employment agreements and commercial leases. "
    "Always answer in the same language the user used (Spanish or English). "
    "Use ONLY the contract text provided in the CONTRACT CONTEXT plus the user's question. "
    "If something is not clearly stated in the contract, say so explicitly and do not invent details. "
    "Give clear, structured answers (bullet points or numbered lists)."
)

# =========================
#        APP FASTAPI
# =========================

app = FastAPI(title="Contracts LLM Proxy")


# CORS para que la UI en http://localhost:3020 pueda llamar directo al backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3020",
        "http://127.0.0.1:3020",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str
    context: Optional[str] = None


class AskResponse(BaseModel):
    answer: str


@app.get("/health")
def health() -> dict:
    """
    Endpoint simple para comprobar que el backend está vivo.
    """
    return {"status": "ok"}
# BEGIN_EXPLICIT_OPTIONS_LLM_ASK_BASIC
# Browser CORS preflight was failing (OPTIONS 405). Handle OPTIONS explicitly.
@app.options("/llm/ask-basic")
async def options_llm_ask_basic(request: Request):
    origin = request.headers.get("origin") or "*"
    req_hdrs = request.headers.get("access-control-request-headers") or "content-type"
    headers = {
        "Access-Control-Allow-Origin": origin,
        "Vary": "Origin",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": req_hdrs,
        "Access-Control-Max-Age": "86400",
    }
    return Response(status_code=204, headers=headers)
# END_EXPLICIT_OPTIONS_LLM_ASK_BASIC



@app.post("/llm/ask-basic", response_model=AskResponse)
def ask_basic(req: AskRequest) -> AskResponse:
    """
    Endpoint principal que la UI debe llamar.
    Envía la pregunta + contexto de contrato al modelo de LM Studio.
    """
    user_content = (
        "CONTRACT CONTEXT:\\n"
        f"{(req.context or '(no context provided)').strip()}\\n\\n"
        "USER QUESTION:\\n"
        f"{req.question.strip()}"
    )

    payload = {
        "model": LMSTUDIO_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.2,
        "max_tokens": 900,
    }

    try:
        resp = requests.post(LMSTUDIO_BASE_URL, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        answer = data["choices"][0]["message"]["content"]
    except Exception as e:
        # Que la UI vea claramente el error si el modelo no responde
        answer = f"Error contacting local LLM server ({LMSTUDIO_BASE_URL}): {e}"

    return AskResponse(answer=answer)


if __name__ == "__main__":
    # Servidor uvicorn "real" del backend
    uvicorn.run(app, host="127.0.0.1", port=4050)

