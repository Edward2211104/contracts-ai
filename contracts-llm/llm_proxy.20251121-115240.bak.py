from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import requests
import textwrap

app = FastAPI(title="Contracts-AI LLM backend")


# BEGIN_FORCE_OPTIONS_CORS_PATCH
# Fix browser CORS preflight: OPTIONS /llm/ask-basic returning 405
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

# BEGIN_FASTAPI_CORS_PATCH
# Allow browser UI (localhost:3020) to call the LLM API (127.0.0.1:4050)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3020",
        "http://127.0.0.1:3020",
        "http://localhost:3010",
        "http://127.0.0.1:3010"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
# END_FASTAPI_CORS_PATCH
# Intentamos soportar varias variables de entorno, por si ya usabas alguna antes.
UPSTREAM_URL = (
    os.environ.get("UPSTREAM_LLM_URL")
    or os.environ.get("LM_STUDIO_URL")
    or os.environ.get("LOCAL_LLM_URL")
    or "http://localhost:1234/v1/chat/completions"
)

UPSTREAM_MODEL = (
    os.environ.get("UPSTREAM_LLM_MODEL")
    or os.environ.get("LM_STUDIO_MODEL")
    or os.environ.get("LOCAL_LLM_MODEL")
    or "llama-3.1-8b-instruct"
)

MAX_TOKENS = int(os.environ.get("UPSTREAM_LLM_MAX_TOKENS", "768"))

BASE_SYSTEM_PROMPT = """
You are an expert lawyer in commercial, insurance, and residential contracts.
Answer only using the information contained in the contract text and any extra
context I provide. When possible, quote or paraphrase the relevant clauses and
explain your reasoning step by step in clear, concise language. If the answer
is not clearly determined by the contract, say so explicitly and explain why.
""".strip()


class AskRequest(BaseModel):
    question: str
    contractText: str = ""
    extraContext: str = ""
    systemPrompt: Optional[str] = None


def _build_messages(req: AskRequest):
    system_prompt = BASE_SYSTEM_PROMPT
    if req.systemPrompt:
        system_prompt += "\n\nAdditional instructions:\n" + req.systemPrompt.strip()

    context_parts = []
    if req.contractText:
        context_parts.append("CONTRACT TEXT:\n" + req.contractText.strip())
    if req.extraContext:
        context_parts.append("EXTRA CONTEXT:\n" + req.extraContext.strip())

    if context_parts:
        context_block = "\n\n".join(context_parts)
    else:
        context_block = "No contract text was provided. If you cannot answer safely, say so."

    user_prompt = textwrap.dedent(f"""
    You will receive contract text and a question.

    1) Carefully read the contract text.
    2) Identify the clauses that are relevant to the question.
    3) Answer the question STRICTLY based on the contract text.
    4) When possible, quote or paraphrase the specific clauses you are using.

    Contract and context:
    {context_block}

    Question:
    {req.question}
    """).strip()

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _call_upstream(req: AskRequest) -> str:
    messages = _build_messages(req)
    payload = {
        "model": UPSTREAM_MODEL,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": MAX_TOKENS,
        "stream": False,
    }

    try:
        resp = requests.post(UPSTREAM_URL, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error calling upstream LLM: {exc}") from exc

    try:
        choices = data.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content")
            if content:
                return content.strip()
        # Fallback: devolvemos todo el JSON si el formato es raro
        return str(data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected response format from LLM: {exc}") from exc


@app.post("/rag/ask")
def rag_ask(req: AskRequest):
    """
    Main endpoint used by the UI. Performs contract-aware reasoning using the upstream LLM.
    """
    answer = _call_upstream(req)
    return {"ok": True, "answer": answer}


@app.post("/llm/ask-basic")
def ask_basic(req: AskRequest):
    """
    Backwards compatible endpoint; currently identical to /rag/ask.
    """
    answer = _call_upstream(req)
    return {"ok": True, "answer": answer}


@app.get("/health")
def health():
    return {"status": "ok"}


