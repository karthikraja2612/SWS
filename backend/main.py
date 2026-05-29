from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from groq_service import generate_answer
from rag import retrieve_relevant_chunks


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


load_dotenv(ENV_PATH)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]


app = FastAPI(
    title="Company Policy RAG Chatbot",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def extract_source_documents(retrieved_chunks: list[dict]) -> list[str]:
    source_documents: list[str] = []
    seen_sources: set[str] = set()

    for chunk in retrieved_chunks:
        metadata = chunk.get("metadata", {}) or {}
        source_file = metadata.get("source_file")
        if isinstance(source_file, str) and source_file not in seen_sources:
            seen_sources.add(source_file)
            source_documents.append(source_file)

    return source_documents


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question must not be empty")

    try:
        retrieval = retrieve_relevant_chunks(question, top_k=4)
    except Exception as exc:
        logger.exception("Retrieval failed")
        raise HTTPException(status_code=500, detail="Failed to retrieve context") from exc

    retrieved_chunks = retrieval.get("chunks", [])
    sources = retrieval.get("source_documents") or extract_source_documents(retrieved_chunks)

    try:
        answer = generate_answer(question, retrieved_chunks)
    except Exception as exc:
        logger.exception("Answer generation failed")
        raise HTTPException(status_code=500, detail="Failed to generate answer") from exc

    return ChatResponse(answer=answer, sources=sources)


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)