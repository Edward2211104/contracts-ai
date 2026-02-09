from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Local Contracts LLM", version="0.1.0")


class AskRequest(BaseModel):
    question: str
    contractText: str = ""
    extraContext: str = ""


class AskResponse(BaseModel):
    answer: str


def analyze_contract(question: str, contract_text: str, extra_context: str = "") -> str:
    """
    Analizador local sencillo. NO usa OpenAI ni ningún servicio externo.
    Puedes reemplazar esta función por tu modelo entrenado cuando lo tengas listo.
    """
    q = (question or "").strip()
    text = (contract_text or "").strip()
    extra = (extraContext or "").strip() if (extraContext := extra_context) is not None else ""

    if not text:
        return (
            "I don't have any contract text to analyze for this question yet. "
            "Make sure the contract text is available and sent as 'contractText' "
            "when calling /llm/ask-basic."
        )

    q_low = q.lower()
    t_low = text.lower()

    parts: list[str] = []

    # 1) Fechas de vigencia
    if any(w in q_low for w in ["until when", "valid", "end date", "until what date", "vigente", "vencimiento"]):
        parts.append(
            "From the contract text I have, the validity period appears in the clause you provided. "
            "Please check the dates carefully; the contract is valid for that period unless "
            "another clause says otherwise."
        )

    # 2) Water damage / responsabilidad
    if "water damage" in q_low or "daño por agua" in q_low:
        if "not responsible" in t_low or "not liable" in t_low or "no será responsable" in t_low:
            parts.append(
                "Regarding water damage: the contract states that the landlord is NOT responsible "
                "for water damage, especially where it is caused by tenant negligence."
            )
        elif "responsible" in t_low or "liable" in t_low or "será responsable" in t_low:
            parts.append(
                "Regarding water damage: the contract assigns responsibility to the landlord/insurer "
                "in the clause you shared. Review that clause for the exact conditions and limits."
            )

    # 3) Si no encontramos nada específico, devolvemos un resumen corto del texto
    if not parts:
        snippet = text.replace("\n", " ")
        if len(snippet) > 900:
            snippet = snippet[:900] + "..."
        parts.append("Here is a summary of the relevant contract text I received:\n\n" + snippet)

    # 4) Añadir contexto extra si viene algo
    if extra:
        parts.append("\nAdditional context supplied:\n" + extra)

    return "\n".join(parts)


@app.post("/llm/ask-basic", response_model=AskResponse)
async def ask_basic(req: AskRequest) -> AskResponse:
    """
    Endpoint principal que usa el analizador local.
    """
    answer = analyze_contract(
        question=req.question,
        contract_text=req.contractText,
        extra_context=req.extraContext,
    )
    return AskResponse(answer=answer)
