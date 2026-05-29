from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = Path(__file__).resolve().parent / "chroma_db"
COLLECTION_NAME = "company_policies"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 4

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_text: str
    metadata: dict[str, Any]


def load_embedding_model() -> SentenceTransformer:
    """Load the sentence-transformer model used during ingestion."""
    logger.info("Loading embedding model: %s", EMBEDDING_MODEL_NAME)
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def load_collection() -> chromadb.api.models.Collection.Collection:
    """Load the persisted ChromaDB collection from disk."""
    if not CHROMA_DIR.exists():
        raise FileNotFoundError(
            f"ChromaDB directory not found: {CHROMA_DIR}. Run ingest.py first."
        )

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception as exc:
        raise RuntimeError(
            f"Could not load Chroma collection '{COLLECTION_NAME}'. Run ingest.py first."
        ) from exc

    return collection


def build_query_embedding(model: SentenceTransformer, question: str) -> list[float]:
    """Embed a user question using the same model and normalization as ingest."""
    embedding = model.encode([question], normalize_embeddings=True)
    return embedding[0].tolist()


def retrieve_relevant_chunks(question: str, top_k: int = TOP_K) -> dict[str, Any]:
    """Retrieve the most relevant stored chunks for a question."""
    cleaned_question = question.strip()
    if not cleaned_question:
        raise ValueError("question must not be empty")

    model = load_embedding_model()
    collection = load_collection()
    query_embedding = build_query_embedding(model, cleaned_question)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = results.get("documents", [[]])[0] or []
    metadatas = results.get("metadatas", [[]])[0] or []

    retrieved_chunks: list[RetrievedChunk] = []
    source_documents: list[str] = []
    seen_sources: set[str] = set()

    for document, metadata in zip(documents, metadatas):
        normalized_metadata = dict(metadata or {})
        chunk = RetrievedChunk(chunk_text=document, metadata=normalized_metadata)
        retrieved_chunks.append(chunk)

        source_file = normalized_metadata.get("source_file")
        if isinstance(source_file, str) and source_file not in seen_sources:
            seen_sources.add(source_file)
            source_documents.append(source_file)

    return {
        "chunks": [
            {
                "chunk_text": item.chunk_text,
                "metadata": item.metadata,
            }
            for item in retrieved_chunks
        ],
        "source_documents": source_documents,
    }


if __name__ == "__main__":
    sample_question = "What is the policy for remote work?"
    response = retrieve_relevant_chunks(sample_question)
    logger.info("Retrieved %d chunks", len(response["chunks"]))
    logger.info("Source documents: %s", response["source_documents"])
