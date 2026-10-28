"""Persistent ChromaDB collection used to store and query chunk embeddings.

Chroma handles both the vector index and metadata storage, so this module
just wraps its client with the two operations the pipeline needs: build
(add chunks once) and query (top-k nearest chunks for a question).
"""

import chromadb

from src.config import get_config, PROJECT_ROOT
from src.rag.embedding import embed_texts
from src.rag.chunking import Chunk


def get_collection():
    cfg = get_config()["vectorstore"]
    persist_path = PROJECT_ROOT / cfg["persist_dir"]
    persist_path.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(persist_path))
    return client.get_or_create_collection(name=cfg["collection_name"])


def is_populated() -> bool:
    return get_collection().count() > 0


def index_chunks(chunks: list[Chunk], batch_size: int = 256) -> None:
    """Embeds and stores chunks. Safe to call once; re-running against an
    already-populated collection would create duplicate IDs, so callers
    should check is_populated() first (see rag/pipeline.py).
    """
    collection = get_collection()

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        texts = [c.text for c in batch]
        embeddings = embed_texts(texts)

        collection.add(
            ids=[c.chunk_id for c in batch],
            embeddings=embeddings,
            documents=texts,
            metadatas=[{"doc_id": c.doc_id} for c in batch],
        )


def query_top_k(query_text: str, top_k: int) -> list[dict]:
    """Returns the top_k chunks most similar to query_text, each as
    {"chunk_id", "text", "doc_id", "distance"}.
    """
    collection = get_collection()
    query_embedding = embed_texts([query_text])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    hits = []
    if results["ids"] and len(results["ids"]) > 0:
        for i in range(len(results["ids"][0])):
            hits.append(
                {
                    "chunk_id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "doc_id": results["metadatas"][0][i].get("doc_id", ""),
                    "distance": results["distances"][0][i],
                }
            )
    return hits


def get_custom_documents_collection():
    """Collection dedicated to user-uploaded PDF and TXT documents."""
    cfg = get_config()["vectorstore"]
    persist_path = PROJECT_ROOT / cfg["persist_dir"]
    persist_path.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(persist_path))
    return client.get_or_create_collection(name="veriai_documents")


def index_document_chunks(chunks, batch_size: int = 128) -> int:
    """Indexes processed DocumentChunk instances into the veriai_documents collection."""
    if not chunks:
        return 0

    collection = get_custom_documents_collection()
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        texts = [c.text for c in batch]
        embeddings = embed_texts(texts)

        metadatas = [
            {
                "doc_id": c.doc_id,
                "doc_title": getattr(c, "doc_title", c.doc_id),
                "page_number": c.page_number if c.page_number is not None else 1,
                "chunk_index": getattr(c, "chunk_index", 0),
            }
            for c in batch
        ]

        collection.add(
            ids=[c.chunk_id for c in batch],
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
    return len(chunks)


def delete_document_chunks(doc_id: str) -> None:
    """Removes all indexed chunks associated with a document ID."""
    collection = get_custom_documents_collection()
    try:
        collection.delete(where={"doc_id": doc_id})
    except Exception:
        # Fallback if where filter is unsupported in some environments
        pass


def query_custom_documents(query_text: str, top_k: int = 5, doc_id: str | None = None) -> list[dict]:
    """Queries user-uploaded documents for relevant evidence chunks."""
    collection = get_custom_documents_collection()
    count = collection.count()
    if count == 0:
        return []

    query_embedding = embed_texts([query_text])[0]
    effective_k = min(top_k, count)

    where_filter = {"doc_id": doc_id} if doc_id else None
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=effective_k,
        where=where_filter,
    )

    hits = []
    if results["ids"] and len(results["ids"]) > 0:
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            # Convert cosine distance to similarity score
            dist = float(results["distances"][0][i])
            sim = max(0.0, 1.0 - dist / 2.0)
            hits.append(
                {
                    "chunk_id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "doc_id": meta.get("doc_id", ""),
                    "doc_title": meta.get("doc_title", meta.get("doc_id", "")),
                    "page_number": meta.get("page_number"),
                    "distance": dist,
                    "similarity": sim,
                }
            )
    return hits

