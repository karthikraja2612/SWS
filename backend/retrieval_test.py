from __future__ import annotations

from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = Path(__file__).resolve().parent / "chroma_db"
COLLECTION_NAME = "company_policies"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 4
QUERY = "What topics are covered in the documents?"


def load_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def load_collection():
    if not CHROMA_DIR.exists():
        raise FileNotFoundError(
            f"ChromaDB directory not found: {CHROMA_DIR}. Run backend/ingest.py first."
        )

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        return client.get_collection(name=COLLECTION_NAME)
    except Exception as exc:
        raise RuntimeError(
            f"Could not load Chroma collection '{COLLECTION_NAME}'. Run backend/ingest.py first."
        ) from exc


def build_query_embedding(model: SentenceTransformer, question: str) -> list[float]:
    embedding = model.encode([question], normalize_embeddings=True)
    return embedding[0].tolist()


def format_preview(text: str, limit: int = 180) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def main() -> None:
    model = load_embedding_model()
    collection = load_collection()
    query_embedding = build_query_embedding(model, QUERY)

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"],
    )

    documents = result.get("documents", [[]])[0] or []
    metadatas = result.get("metadatas", [[]])[0] or []
    distances = result.get("distances", [[]])[0] or []

    print(f"Query: {QUERY}")
    print("Top 4 matches:")

    for rank, (document, metadata, distance) in enumerate(zip(documents, metadatas, distances), start=1):
        source_document = metadata.get("source_file", "unknown")
        page_number = metadata.get("page_number", "unknown")
        preview = format_preview(document)

        print(f"\nRank {rank}")
        print(f"Similarity rank: {rank}")
        print(f"Source document: {source_document}")
        print(f"Page number: {page_number}")
        print(f"Chunk preview: {preview}")
        print(f"Distance: {distance}")


if __name__ == "__main__":
    main()
