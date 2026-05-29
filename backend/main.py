from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rag import retrieve_relevant_chunks


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
GEMINI_MODEL_NAME = "gemini-1.5-flash"
NOT_FOUND_RESPONSE = "I don't have that information in the company documents."

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


class ContextChunk(BaseModel):
    chunk_text: str
    metadata: dict


class RetrievalResult(BaseModel):
    chunks: list[ContextChunk]
    source_documents: list[str]


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


@lru_cache(maxsize=1)
def get_gemini_model() -> genai.GenerativeModel:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    genai.configure(api_key=api_key)
    generation_config = {
        "temperature": 0.0,
        "top_p": 1.0,
        "top_k": 1,
        "max_output_tokens": 512,
    }
    return genai.GenerativeModel(
        model_name=GEMINI_MODEL_NAME,
        generation_config=generation_config,
    )


def build_context_prompt(question: str, chunks: list[dict]) -> str:
    context_blocks: list[str] = []

    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk.get("metadata", {}) or {}
        source_file = metadata.get("source_file", "unknown")
        page_number = metadata.get("page_number", "unknown")
        chunk_index = metadata.get("chunk_index", "unknown")
        chunk_text = chunk.get("chunk_text", "")

        context_blocks.append(
            f"[Chunk {index}]\n"
            f"Source: {source_file}\n"
            f"Page: {page_number}\n"
            f"Chunk Index: {chunk_index}\n"
            f"Text: {chunk_text}"
        )

    context = "\n\n".join(context_blocks)

    return (
        "You are a strict company policy assistant.\n"
        "Answer only from the provided context.\n"
        "Never use outside knowledge, never guess, and never hallucinate.\n"
        f"If the answer is not explicitly supported by the context, reply exactly: {NOT_FOUND_RESPONSE}\n\n"
        f"Question: {question}\n\n"
        f"Context:\n{context}\n\n"
        "Return a concise, direct answer grounded only in the context."
    )


def generate_grounded_answer(question: str, retrieval_result: dict) -> str:
    chunks = retrieval_result.get("chunks", [])
    if not chunks:
        return NOT_FOUND_RESPONSE

    model = get_gemini_model()
    prompt = build_context_prompt(question, chunks)

    try:
        response = model.generate_content(prompt)
    except Exception as exc:
        logger.exception("Gemini generation failed")
        raise HTTPException(status_code=500, detail="Failed to generate answer") from exc

    answer = (getattr(response, "text", "") or "").strip()
    if not answer:
        return NOT_FOUND_RESPONSE

    if NOT_FOUND_RESPONSE.lower() in answer.lower():
        return NOT_FOUND_RESPONSE

    return answer


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

    answer = generate_grounded_answer(question, retrieval)
    sources = retrieval.get("source_documents", [])

    return ChatResponse(answer=answer, sources=sources)


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)