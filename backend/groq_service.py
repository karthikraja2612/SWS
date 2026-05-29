from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from groq import Groq


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
MODEL_NAME = "llama-3.3-70b-versatile"
FALLBACK_ANSWER = "I don't have that information in the company documents."

load_dotenv(ENV_PATH)


@lru_cache(maxsize=1)
def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set in the environment or .env file")
    return Groq(api_key=api_key)


def build_context(retrieved_chunks: list[dict[str, Any]]) -> str:
    blocks: list[str] = []

    for index, chunk in enumerate(retrieved_chunks, start=1):
        chunk_text = str(chunk.get("chunk_text", "")).strip()
        metadata = chunk.get("metadata", {}) or {}
        source_file = metadata.get("source_file", "unknown")
        page_number = metadata.get("page_number", "unknown")
        chunk_index = metadata.get("chunk_index", "unknown")

        blocks.append(
            f"[Chunk {index}]\n"
            f"Source: {source_file}\n"
            f"Page: {page_number}\n"
            f"Chunk Index: {chunk_index}\n"
            f"Text: {chunk_text}"
        )

    return "\n\n".join(blocks)


def build_prompt(question: str, retrieved_chunks: list[dict[str, Any]]) -> str:
    context = build_context(retrieved_chunks)
    return (
        "You are an internal company policy assistant.\n\n"
        "Answer ONLY using the provided context.\n"
        "If the answer cannot be found in the context, reply exactly:\n\n"
        f"{FALLBACK_ANSWER}\n\n"
        "Include concise and professional answers.\n\n"
        f"Question: {question}\n\n"
        f"Context:\n{context}\n"
    )


def generate_answer(question: str, retrieved_chunks: list[dict[str, Any]]) -> str:
    prompt = build_prompt(question, retrieved_chunks)
    client = get_groq_client()

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an internal company policy assistant. Answer only from the provided context. "
                    f"If the answer is not in the context, reply exactly: {FALLBACK_ANSWER}"
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        top_p=1,
    )

    answer = (response.choices[0].message.content or "").strip()
    if not answer:
        return FALLBACK_ANSWER

    if FALLBACK_ANSWER.lower() in answer.lower():
        return FALLBACK_ANSWER

    return answer


if __name__ == "__main__":
    sample_chunks = [
        {
            "chunk_text": "Employees are entitled to 12 sick leave days per calendar year.",
            "metadata": {
                "source_file": "sick_leave_policy.pdf",
                "page_number": 2,
                "chunk_index": 0,
            },
        }
    ]
    print(generate_answer("How many sick leave days do employees get?", sample_chunks))
