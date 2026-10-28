"""Question -> top-k relevant chunks.

Separated from vectorstore.py so callers (pipeline.py, and later
verification/ modules that need "what evidence backs this claim") depend
on a small, stable interface instead of Chroma's query API directly.
"""

from src.config import get_config
from src.rag.vectorstore import query_top_k, query_custom_documents
from src.rag.chunking import chunk_text


def retrieve(question: str, top_k: int | None = None) -> list[dict]:
    """Returns the top_k chunks most relevant to `question` from default corpus.

    top_k falls back to config.yaml's retrieval.top_k when not given
    explicitly, so most call sites don't need to know the default.
    """
    if top_k is None:
        top_k = get_config()["retrieval"]["top_k"]
    return query_top_k(question, top_k)


def retrieve_evidence(
    query: str,
    top_k: int = 3,
    doc_id: str | None = None,
    raw_context: str | None = None,
) -> list[dict]:
    """Retrieves evidence chunks from raw text, custom uploaded documents, or demo corpus.

    Priority:
    1. If `raw_context` is provided: chunks raw text into candidate evidence chunks.
    2. If uploaded custom documents exist: queries `veriai_documents` collection.
    3. Falls back to default corpus collection.
    """
    if raw_context and raw_context.strip():
        chunks = chunk_text("user_provided_context", raw_context.strip())
        return [
            {
                "chunk_id": c.chunk_id,
                "text": c.text,
                "doc_id": "Direct Evidence Input",
                "doc_title": "Direct Evidence Input",
                "page_number": 1,
                "distance": 0.0,
                "similarity": 1.0,
            }
            for c in chunks
        ]

    # Try custom uploaded documents
    custom_hits = query_custom_documents(query, top_k=top_k, doc_id=doc_id)
    if custom_hits:
        return custom_hits

    # Fallback to demo corpus if populated
    try:
        from src.rag.vectorstore import is_populated

        if is_populated():
            return retrieve(query, top_k=top_k)
    except Exception:
        pass

    return []

