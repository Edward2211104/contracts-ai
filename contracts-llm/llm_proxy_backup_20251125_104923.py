import os
import logging
from typing import Optional

from pydantic import BaseModel
from openai import OpenAI

logger = logging.getLogger(__name__)

# =============================================================================
# Configuración de upstream LLM (LM Studio u otro servidor OpenAI-compatible)
# =============================================================================

UPSTREAM_LLM_BASE_URL = os.getenv("UPSTREAM_LLM_BASE_URL", "http://localhost:1234")
UPSTREAM_LLM_MODEL = os.getenv("UPSTREAM_LLM_MODEL", "openai/gpt-oss-20b")
UPSTREAM_LLM_API_KEY = os.getenv("UPSTREAM_LLM_API_KEY", "not-needed")

client = OpenAI(
    base_url=f"{UPSTREAM_LLM_BASE_URL}/v1",
    api_key=UPSTREAM_LLM_API_KEY,
)

# =============================================================================
# Modelos de datos
# =============================================================================

class BasicAskResponse(BaseModel):
    ok: bool
    answer: str

# =============================================================================
# Función principal usada por FastAPI: ask_basic_llm
# =============================================================================

def ask_basic_llm(question: str, context: str, has_contract: bool = False) -> BasicAskResponse:
    """
    Llama al modelo LLM upstream para responder una pregunta legal,
    usando (si existe) el contexto RAG de pólizas / contratos.
    NUNCA lanza excepciones: siempre devuelve BasicAskResponse.
    """

    system_parts = [
        "You are an expert legal assistant for insurance and contract questions.",
        "Explain things in clear, plain English while keeping legal accuracy.",
    ]

    if has_contract:
        system_parts.append(
            "The user is asking about a specific uploaded contract; "
            "prefer information from that contract when possible."
        )

    if context and context.strip():
        system_parts.append(
            "You also have access to policy excerpts in the provided context. "
            "Use them when relevant, and cite them conceptually in your explanation."
        )

    system_prompt = " ".join(system_parts)

    user_prompt = f"""Context from knowledge base (may be empty):

{context or "(no extra context provided)"}

User question:
{question}
"""

    try:
        response = client.chat.completions.create(
            model=UPSTREAM_LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )

        answer_text = ""
        try:
            if response and response.choices:
                answer_text = response.choices[0].message.content or ""
        except Exception:
            logger.exception("Unexpected structure in upstream LLM response")
            answer_text = ""

        if not answer_text:
            answer_text = (
                "The upstream language model returned an empty answer. "
                "Please try rephrasing the question."
            )

        return BasicAskResponse(ok=True, answer=answer_text)

    except Exception as exc:
        # Muy importante: NO dejamos que la excepción suba a FastAPI
        # para evitar errores 500 hacia el frontend.
        logger.exception("Error calling upstream LLM")
        return BasicAskResponse(
            ok=False,
            answer=f"Internal LLM error while calling upstream model: {exc}",
        )
