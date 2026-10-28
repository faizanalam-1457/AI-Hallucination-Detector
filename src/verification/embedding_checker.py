"""The "simple baseline" that verification/nli_checker.py is benchmarked
against. Instead of true entailment reasoning, this scores a claim as
"supported" purely by embedding-similarity to the evidence -- the approach
many naive RAG-QA validators actually ship with.

This exists to demonstrate *why* similarity alone is insufficient: a claim
can be semantically close to a chunk about the same topic while still
asserting something that chunk doesn't say, or directly contradicts. E.g.
"Lincoln was the seventeenth President" sits right next to "Lincoln was
the sixteenth President" in embedding space -- they're about the exact
same entities and topic, so similarity is high even though the claim is
false. NLI-based checking (nli_checker.py) is what catches that; this
baseline can't.
"""

from dataclasses import dataclass

import numpy as np

from src.config import get_config
from src.rag.embedding import embed_texts


@dataclass
class EmbeddingVerificationResult:
    claim_text: str
    max_similarity: float
    is_supported: bool
    most_similar_chunk_id: str | None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def check_claim_similarity(claim_text: str, evidence_chunks: list[dict]) -> EmbeddingVerificationResult:
    """Scores `claim_text` by embedding-similarity to `evidence_chunks`.

    Args:
        claim_text: a single atomic claim (see src/claims/extractor.py).
        evidence_chunks: retrieved chunks, as returned by
            src/rag/retriever.py's retrieve() (each with "text" and
            "chunk_id" keys).

    Returns:
        An EmbeddingVerificationResult with the best similarity score
        found and a supported/unsupported decision against
        config.yaml's verification.embedding_similarity_threshold.
    """
    if not evidence_chunks:
        return EmbeddingVerificationResult(
            claim_text=claim_text, max_similarity=0.0, is_supported=False, most_similar_chunk_id=None
        )

    threshold = get_config()["verification"]["embedding_similarity_threshold"]

    # Embed the claim and all chunks in one batched call.
    texts = [claim_text] + [chunk["text"] for chunk in evidence_chunks]
    embeddings = embed_texts(texts)
    claim_embedding, chunk_embeddings = embeddings[0], embeddings[1:]

    similarities = [_cosine_similarity(claim_embedding, emb) for emb in chunk_embeddings]
    best_idx = int(np.argmax(similarities))
    best_score = similarities[best_idx]

    return EmbeddingVerificationResult(
        claim_text=claim_text,
        max_similarity=best_score,
        is_supported=best_score >= threshold,
        most_similar_chunk_id=evidence_chunks[best_idx]["chunk_id"],
    )


def verify_claim_embedding(claim_text: str, evidence_chunks: list[dict]):
    """Scores claim by embedding similarity, returning an AggregatedClaimResult.

    Demonstrates baseline limitations: high similarity does NOT guarantee
    factual correctness.
    """
    from src.verification.aggregation import AggregatedClaimResult, ClaimVerdict, EvidencePassageScore

    res = check_claim_similarity(claim_text, evidence_chunks)
    threshold = get_config()["verification"]["embedding_similarity_threshold"]

    verdict = ClaimVerdict.SUPPORTED if res.is_supported else ClaimVerdict.INSUFFICIENT_EVIDENCE

    best_chunk = None
    if res.most_similar_chunk_id and evidence_chunks:
        best_chunk = next((c for c in evidence_chunks if c.get("chunk_id") == res.most_similar_chunk_id), evidence_chunks[0])

    passage = None
    if best_chunk:
        passage = EvidencePassageScore(
            chunk_id=best_chunk.get("chunk_id", "c0"),
            doc_id=best_chunk.get("doc_id", "doc"),
            text=best_chunk.get("text", ""),
            page_number=best_chunk.get("page_number"),
            retrieval_similarity=res.max_similarity,
            entailment_prob=res.max_similarity,
            contradiction_prob=0.0,
            neutral_prob=1.0 - res.max_similarity,
            verdict="entailment" if res.is_supported else "neutral",
            is_winning=True,
        )

    explanation = (
        f"Embedding similarity to closest chunk is {res.max_similarity:.1%}, which clears the threshold ({threshold:.1%}). "
        "Caution: Embedding similarity measures topical relatedness rather than factual entailment."
        if res.is_supported
        else f"Maximum embedding similarity ({res.max_similarity:.1%}) fails the threshold ({threshold:.1%})."
    )

    return AggregatedClaimResult(
        claim_text=claim_text,
        verdict=verdict,
        model_score=res.max_similarity,
        retrieval_similarity=res.max_similarity,
        verification_method="embedding",
        model_identifier=get_config()["embedding"]["model_name"],
        supporting_evidence=[passage] if passage else [],
        primary_passage=passage,
        plain_english_explanation=explanation,
        requires_human_review=not res.is_supported,
        limitations=[
            "Embedding similarity baseline cannot detect factual contradiction when entities and vocabulary match."
        ],
    )

