import os
from typing import Optional

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# =========================
#  Configuración principal
# =========================

# Endpoint de LM Studio (modo OpenAI compatible)
LM_STUDIO_URL = os.getenv(
    "LM_STUDIO_URL",
    "http://127.0.0.1:1234/v1/chat/completions",
)

SYSTEM_PROMPT_BASE = (
    "You are ContractAI Pro, an expert legal assistant specialized in analysing contracts. "
    "Always answer in clear professional English unless the question is clearly in Spanish, "
    "then respond in Spanish.\n\n"
    "When contract text is provided, base your answer ONLY on that text. "
    "If the user asks something outside the contract, explain that limitation."
)

app = FastAPI(title="Contracts LLM Backend")

# CORS para permitir llamadas desde http://localhost:3020
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # si quieres, luego lo restringimos a ["http://localhost:3020"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str
    context: Optional[str] = ""


class AskResponse(BaseModel):
    ok: bool
    answer: Optional[str] = None
    error: Optional[str] = None
    detail: Optional[str] = None


# =========================
#  Endpoint principal
# =========================

@app.post("/llm/ask-basic", response_model=AskResponse)
async def ask_basic(req: AskRequest) -> AskResponse:
    """
    Recibe { question, context } desde la UI y reenvía la pregunta a LM Studio
    usando el endpoint OpenAI-compatible /v1/chat/completions.
    """

    question = (req.question or "").strip()
    context = (req.context or "").strip()

    if not question:
        return AskResponse(ok=False, error="Missing 'question' field.")

    # Construimos los mensajes para el modelo tipo ChatGPT
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_BASE},
    ]

    if context:
        messages.append(
            {
                "role": "system",
                "content": "Contract text (use this as context, do NOT ignore it):\n" + context,
            }
        )

    messages.append({"role": "user", "content": question})

    payload = {
        # LM Studio solo requiere que 'model' exista; el valor no importa mucho.
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 1024,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(LM_STUDIO_URL, json=payload)
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                # 4xx / 5xx de LM Studio
                text = await resp.aread()
                return AskResponse(
                    ok=False,
                    error=f"LM call failed with HTTP {resp.status_code}",
                    detail=text.decode(errors="ignore"),
                )

            data = resp.json()
    except Exception as e:
        # Error de red, conexión rechazada, etc.
        return AskResponse(
            ok=False,
            error="Unexpected error calling language model server.",
            detail=str(e),
        )

    # Extraer la respuesta en formato OpenAI:
    # {
    #   "choices": [
    #       {
    #           "message": {"role": "assistant", "content": "texto..."},
    #           ...
    #       }
    #   ],
    #   ...
    # }
    answer = None
    try:
        if isinstance(data, dict):
            choices = data.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    msg = first.get("message")
                    if isinstance(msg, dict):
                        answer = msg.get("content")
    except Exception:
        answer = None

    if not answer:
        # Si no pudimos extraer el texto, devolvemos el JSON entero como string
        answer = str(data)

    return AskResponse(ok=True, answer=answer)


# =========================
#  main (para ejecución directa)
# =========================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "simple_backend:app",
        host="127.0.0.1",
        port=4050,
        reload=False,
    )
