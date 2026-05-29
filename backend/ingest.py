from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import chromadb
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:  # pragma: no cover - fallback for older LangChain installs
    from langchain.text_splitters import RecursiveCharacterTextSplitter


BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
CHROMA_DIR = Path(__file__).resolve().parent / "chroma_db"
COLLECTION_NAME = "company_policies"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
BATCH_SIZE = 64

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    text: str
    source_file: str
    page_number: int
    chunk_index: int

    def to_metadata(self) -> dict:
        return {
            "source_file": self.source_file,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
        }


def get_pdf_files(directory: Path) -> List[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"Documents directory not found: {directory}")

    pdf_files = sorted(path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".pdf")
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in: {directory}")

    return pdf_files


def extract_page_text(pdf_path: Path) -> Iterable[tuple[int, str]]:
    with fitz.open(pdf_path) as document:
        for page_index, page in enumerate(document, start=1):
            text = page.get_text("text") or ""
            cleaned_text = text.strip()
            if cleaned_text:
                yield page_index, cleaned_text


def build_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
        length_function=len,
    )


def chunk_document(pdf_path: Path, splitter: RecursiveCharacterTextSplitter) -> list[ChunkRecord]:
    records: list[ChunkRecord] = []
    chunk_index = 0

    for page_number, page_text in extract_page_text(pdf_path):
        chunks = splitter.split_text(page_text)
        for chunk_text in chunks:
            normalized_chunk = chunk_text.strip()
            if not normalized_chunk:
                continue

            chunk_id = f"{pdf_path.stem}-p{page_number}-c{chunk_index}"
            records.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    text=normalized_chunk,
                    source_file=pdf_path.name,
                    page_number=page_number,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

    return records


def load_all_chunks() -> list[ChunkRecord]:
    splitter = build_splitter()
    records: list[ChunkRecord] = []

    for pdf_path in get_pdf_files(DOCS_DIR):
        logger.info("Processing %s", pdf_path.name)
        records.extend(chunk_document(pdf_path, splitter))

    if not records:
        raise RuntimeError("No extractable text was found in the PDF documents.")

    return records


def get_collection() -> chromadb.api.models.Collection.Collection:
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info("Removed existing collection %s", COLLECTION_NAME)
    except Exception as exc:  # pragma: no cover - collection may not exist yet
        logger.debug("Skipping collection deletion: %s", exc)

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def embed_texts(model: SentenceTransformer, texts: list[str]) -> list[list[float]]:
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    return embeddings.tolist()


def batch_items(items: list[ChunkRecord], size: int) -> Iterable[list[ChunkRecord]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def ingest() -> dict[str, int]:
    logger.info("Starting ingestion")
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    chunks = load_all_chunks()
    logger.info("Prepared %d chunks", len(chunks))

    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    collection = get_collection()

    total_inserted = 0
    for batch in batch_items(chunks, BATCH_SIZE):
        texts = [item.text for item in batch]
        embeddings = embed_texts(model, texts)
        ids = [item.chunk_id for item in batch]
        metadatas = [item.to_metadata() for item in batch]

        collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        total_inserted += len(batch)
        logger.info("Inserted %d/%d chunks", total_inserted, len(chunks))

    logger.info("Ingestion complete. Persisted collection at %s", CHROMA_DIR)
    return {"chunks_indexed": total_inserted}


def main() -> None:
    try:
        result = ingest()
        logger.info("Done: %s", result)
    except Exception:
        logger.exception("Ingestion failed")
        raise


if __name__ == "__main__":
    main()
