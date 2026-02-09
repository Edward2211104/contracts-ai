from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

from llm_proxy import ask_basic_llm

app = FastAPI(
    title="Contracts LLM Backend",
    version="0.1.0",
    description="Backend LLM service for Contracts-AI"
)


class AskBasicRequest(BaseModel):
    """Request body for /llm/ask-basic."""
    question: str
    context: Optional[str] = None


class AskBasicResponse(BaseModel):
    """Response body for /llm/ask-basic."""
    ok: bool = True
    answer: str


@app.get("/health")
async def health() -> dict:
    """Simple health check."""
    return {"status": "ok"}


@app.post("/llm/ask-basic", response_model=AskBasicResponse)
async def llm_ask_basic(req: AskBasicRequest) -> AskBasicResponse:
    """
    Basic LLM endpoint used by the Contracts-AI app.
    It delegates to llm_proxy.ask_basic_llm(...).
    """
    answer = ask_basic_llm(question=req.question, context=req.context)
    return AskBasicResponse(ok=True, answer=answer)


if __name__ == "__main__":
    import uvicorn

    # Run directly with:  .venv\\Scripts\\python.exe main.py
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=4050,
        reload=True,
    )

