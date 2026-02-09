import os
import logging
from typing import Optional

import requests
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class BasicAskResponse(BaseModel):
    ok: bool
    answer: str


def _get_upstream_config():
    """
    Lee la config de entorno para conectar con LM Studio / servidor OpenAI-compatible.
    """
    base_url = os.getenv("UPSTREAM_LLM_BASE_URL", "http://localhost:1234").rstrip("/")
    # Endpoint tipo OpenAI chat completions
    api_url = os.getenv("UPSTREAM_LLM_URL", "").strip() or f"{base_url}/v1/chat/completions"
    model = os.getenv("UPSTREAM_LLM_MODEL", "openai/gpt-oss-20b")
    return api_url, model


def _chat_completion(system_prompt: str, user_prompt: str) -> str:
    """
    Llama al endpoint /v1/chat/completions del upstream (LM Studio).
    """
    api_url, model = _get_upstream_config()

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    logger.info("Calling upstream LLM at %s with model %s", api_url, model)

    resp = requests.post(api_url, json=payload, timeout=120)
    # Si LM Studio devolviera algo distinto a 2xx, lanzará excepción aquí
    resp.raise_for_status()
    data = resp.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not parse upstream response: %s", data)
        raise RuntimeError(f"Unexpected upstream response format: {e}") from e

    return content


def ask_basic(
    question: str,
    context: str = "",
    has_contract: bool = False,
) -> BasicAskResponse:
    """
    Función principal que usará el backend /llm/ask-basic.
    Construye un prompt legal sencillo y llama al upstream.
    """
    system_prompt = "You are a helpful legal assistant specialized in contract analysis."

    if has_contract and context:
        user_prompt = f"{question}\n\nContract context:\n{context}"
    elif context:
        user_prompt = f"{question}\n\nContext:\n{context}"
    else:
        user_prompt = question

    try:
        answer = _chat_completion(system_prompt=system_prompt, user_prompt=user_prompt)
        return BasicAskResponse(ok=True, answer=answer)
    except Exception as e:  # noqa: BLE001
        logger.exception("Error calling upstream LLM: %s", e)
        # Importante: NO reventar el servidor, devolvemos ok=False
        return BasicAskResponse(ok=False, answer=f"[LLM error] {e}")


def ask_basic_llm(
    question: str,
    context: str,
    has_contract: bool = False,
) -> BasicAskResponse:
    """
    Wrapper de compatibilidad para el import:
        from llm_proxy import ask_basic_llm
    """
    return ask_basic(question=question, context=context, has_contract=has_contract)
