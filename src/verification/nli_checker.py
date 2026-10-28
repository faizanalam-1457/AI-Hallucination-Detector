"""The core of the project: decides whether a claim is actually supported
by the retrieved evidence, using Natural Language Inference (NLI) rather
than surface-level similarity. NLI catches cases embedding similarity
misses -- e.g. "Lincoln was the seventeenth President" sits right next to
"Lincoln was the sixteenth President" in embedding space (same entities,
same topic), so a similarity-only check would call it supported. An NLI
model reads the two sentences as a (premise, hypothesis) pair and asks
"does the premise logically entail the hypothesis?" -- and correctly says
no, because sixteenth != seventeenth.

Model: cross-encoder/nli-deberta-v3-base, a DeBERTa-v3 model fine-tuned
directly for 3-way NLI classification (entailment / neutral /
contradiction) on MNLI+SNLI+FEVER. Loaded via sentence-transformers'
CrossEncoder, which scores a (premise, hypothesis) pair in one forward
pass -- unlike the bi-encoder used for retrieval, which embeds each text
separately and can only compare embeddings after the fact.

Known limitations (both verified empirically):

1. Off-topic pairs read as contradiction, not neutral. This model was
   trained on premise/hypothesis pairs that are topically related. Given
   a genuinely unrelated pair (e.g. a premise about Uruguay's population
   and a hypothesis about the Eiffel Tower), it confidently predicts
   "contradiction" instead of "neutral" -- MNLI's "neutral" label means
   "related but not fully entailed," not "unrelated." This is a real risk
   here, but a bounded one: evidence_chunks are always chunks retrieved
   for the *question* the claim's answer was generated from, so premise
   and hypothesis are rarely topically unrelated in practice.

2. Multi-sentence premises collapse the entailment signal. Cross-encoder
   NLI models are trained on single-sentence (premise, hypothesis) pairs
   (SNLI/MNLI/FEVER). Fed a whole ~150-word retrieved chunk as the
   premise, a claim that is a verbatim sentence from that chunk scored
   98.7% entailment against just that one sentence, but only 0.3%
   (99.7% "neutral") against the full chunk containing it -- the signal
   gets diluted by the surrounding, differently-focused sentences. Fixed
   below by decomposing each evidence chunk into individual sentences
   (via src/claims/extractor.py's split_into_sentences(), shared so both
   call sites behave consistently) and scoring the claim against every
   sentence from every chunk, not each chunk as one block. This matches
   the approach used in factual-consistency-checking research (e.g.
   SummaC, Laban et al. 2022) for exactly this reason.
"""

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

import numpy as np
from sentence_transformers import CrossEncoder

from src.claims.extractor import split_into_sentences
from src.config import get_config


class EntailmentLabel(Enum):
    ENTAILMENT = "entailment"
    NEUTRAL = "neutral"
    CONTRADICTION = "contradiction"


@dataclass
class VerificationResult:
    claim_text: str
    label: EntailmentLabel
    confidence: float
    supporting_chunk_id: str | None


@lru_cache(maxsize=1)
def _get_nli_model() -> CrossEncoder:
    cfg = get_config()["verification"]
    return CrossEncoder(cfg["nli_model_name"])


def _softmax(logits: np.ndarray) -> np.ndarray:
    exp = np.exp(logits - np.max(logits))
    return exp / exp.sum()


def check_claim_entailment(claim_text: str, evidence_chunks: list[dict]) -> VerificationResult:
    """Checks whether `claim_text` is entailed by any of `evidence_chunks`.

    Each chunk is first split into individual sentences (see limitation 2
    in this module's docstring for why), and the claim is scored against
    every sentence from every chunk -- not just the top retrieval hit,
    since the passage that best matches the *question* isn't always the
    one whose specific sentence best supports a given *claim*.

    A claim is judged ENTAILMENT if any evidence sentence's entailment
    probability clears entailment_threshold. Failing that, it's
    CONTRADICTION if some sentence's contradiction probability clears
    contradiction_threshold. Otherwise NEUTRAL: no retrieved evidence
    speaks to this claim either way, which -- for a hallucination
    detector -- is just as much a red flag as an outright contradiction.

    Args:
        claim_text: a single atomic claim (see src/claims/extractor.py).
        evidence_chunks: retrieved chunks, as returned by
            src/rag/retriever.py's retrieve() (each with "text" and
            "chunk_id" keys).

    Returns:
        A VerificationResult describing the strongest entailment relation
        found across all evidence sentences. supporting_chunk_id
        identifies which *chunk* the winning sentence came from.
    """
    if not evidence_chunks:
        return VerificationResult(
            claim_text=claim_text, label=EntailmentLabel.NEUTRAL, confidence=1.0, supporting_chunk_id=None
        )

    # Flatten chunks into (sentence, originating chunk_id) pairs so the
    # NLI model always sees a single-sentence premise, while we can still
    # report which chunk backs the verdict.
    sentence_chunk_ids: list[str] = []
    sentences: list[str] = []
    for chunk in evidence_chunks:
        for sentence in split_into_sentences(chunk["text"]):
            sentences.append(sentence)
            sentence_chunk_ids.append(chunk["chunk_id"])

    if not sentences:
        return VerificationResult(
            claim_text=claim_text, label=EntailmentLabel.NEUTRAL, confidence=1.0, supporting_chunk_id=None
        )

    cfg = get_config()["verification"]
    model = _get_nli_model()
    label_to_index = {label.lower(): int(idx) for idx, label in model.config.id2label.items()}

    # CrossEncoder scores a (premise, hypothesis) pair per call; premise
    # is the evidence sentence, hypothesis is the claim being checked.
    pairs = [(sentence, claim_text) for sentence in sentences]
    raw_logits = model.predict(pairs)  # shape (n_sentences, 3), NOT yet probabilities
    probs = np.array([_softmax(row) for row in raw_logits])

    entail_probs = probs[:, label_to_index["entailment"]]
    contra_probs = probs[:, label_to_index["contradiction"]]
    neutral_probs = probs[:, label_to_index["neutral"]]

    best_entail_idx = int(np.argmax(entail_probs))
    if entail_probs[best_entail_idx] >= cfg["entailment_threshold"]:
        return VerificationResult(
            claim_text=claim_text,
            label=EntailmentLabel.ENTAILMENT,
            confidence=float(entail_probs[best_entail_idx]),
            supporting_chunk_id=sentence_chunk_ids[best_entail_idx],
        )

    best_contra_idx = int(np.argmax(contra_probs))
    if contra_probs[best_contra_idx] >= cfg["contradiction_threshold"]:
        return VerificationResult(
            claim_text=claim_text,
            label=EntailmentLabel.CONTRADICTION,
            confidence=float(contra_probs[best_contra_idx]),
            supporting_chunk_id=sentence_chunk_ids[best_contra_idx],
        )

    return VerificationResult(
        claim_text=claim_text,
        label=EntailmentLabel.NEUTRAL,
        confidence=float(np.max(neutral_probs)),
        supporting_chunk_id=None,
    )


def verify_claim_nli(claim_text: str, evidence_chunks: list[dict]):
    """Full-featured NLI verification returning an AggregatedClaimResult.

    Decomposes evidence into individual sentences, scores each against
    claim_text via cross-encoder, and aggregates according to VeriAI policy.
    """
    from src.verification.aggregation import EvidencePassageScore, aggregate_evidence

    if not evidence_chunks:
        from src.verification.aggregation import AggregatedClaimResult, ClaimVerdict

        return AggregatedClaimResult(
            claim_text=claim_text,
            verdict=ClaimVerdict.INSUFFICIENT_EVIDENCE,
            model_score=0.0,
            retrieval_similarity=0.0,
            verification_method="nli",
            model_identifier="cross-encoder/nli-deberta-v3-base",
            plain_english_explanation="No evidence passages provided.",
            requires_human_review=True,
            limitations=["Empty evidence set."],
        )

    sentence_records = []
    for chunk in evidence_chunks:
        for sentence in split_into_sentences(chunk["text"]):
            sentence_records.append(
                {
                    "sentence": sentence,
                    "chunk_id": chunk.get("chunk_id", "c0"),
                    "doc_id": chunk.get("doc_id", "doc"),
                    "page_number": chunk.get("page_number"),
                    "similarity": float(chunk.get("distance", 0.0)),
                }
            )

    if not sentence_records:
        from src.verification.aggregation import AggregatedClaimResult, ClaimVerdict

        return AggregatedClaimResult(
            claim_text=claim_text,
            verdict=ClaimVerdict.INSUFFICIENT_EVIDENCE,
            model_score=0.0,
            retrieval_similarity=0.0,
            verification_method="nli",
            model_identifier="cross-encoder/nli-deberta-v3-base",
            plain_english_explanation="No parsable sentences in evidence chunks.",
        )

    cfg = get_config()["verification"]
    model = _get_nli_model()
    label_to_index = {label.lower(): int(idx) for idx, label in model.config.id2label.items()}

    pairs = [(rec["sentence"], claim_text) for rec in sentence_records]
    raw_logits = model.predict(pairs)
    probs = np.array([_softmax(row) for row in raw_logits])

    entail_thresh = cfg.get("entailment_threshold", 0.5)
    contra_thresh = cfg.get("contradiction_threshold", 0.5)

    passage_scores = []
    for i, rec in enumerate(sentence_records):
        ep = float(probs[i, label_to_index["entailment"]])
        cp = float(probs[i, label_to_index["contradiction"]])
        np_prob = float(probs[i, label_to_index["neutral"]])

        if ep >= entail_thresh:
            v = "entailment"
        elif cp >= contra_thresh:
            v = "contradiction"
        else:
            v = "neutral"

        passage_scores.append(
            EvidencePassageScore(
                chunk_id=rec["chunk_id"],
                doc_id=rec["doc_id"],
                text=rec["sentence"],
                page_number=rec["page_number"],
                retrieval_similarity=rec["similarity"],
                entailment_prob=ep,
                contradiction_prob=cp,
                neutral_prob=np_prob,
                verdict=v,
            )
        )

    return aggregate_evidence(
        claim_text=claim_text,
        passage_scores=passage_scores,
        entailment_threshold=entail_thresh,
        contradiction_threshold=contra_thresh,
        method="nli",
        model_name="cross-encoder/nli-deberta-v3-base",
    )

