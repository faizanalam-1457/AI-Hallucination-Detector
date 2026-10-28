"""Evidence aggregation and conflict resolution policy for VeriAI.

Combines multiple evidence passages/sentences evaluated against an atomic claim.
Implements an auditable, multi-source aggregation policy that distinguishes:
- Supported: at least one credible passage entails, with no credible conflicting passage.
- Contradicted: no passage entails, and at least one credible passage contradicts.
- Conflicting Evidence: passages from different documents or sections directly contradict each other.
- Insufficient Evidence: no retrieved evidence provides conclusive entailment or contradiction.

Does NOT manufacture certainty by averaging unrelated probability scores.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class ClaimVerdict(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"


@dataclass
class EvidencePassageScore:
    chunk_id: str
    doc_id: str
    text: str
    page_number: Optional[int]
    retrieval_similarity: float
    entailment_prob: float
    contradiction_prob: float
    neutral_prob: float
    verdict: str  # "entailment", "contradiction", "neutral"
    is_winning: bool = False


@dataclass
class AggregatedClaimResult:
    claim_text: str
    verdict: ClaimVerdict
    model_score: float  # Winning probability score
    retrieval_similarity: float  # Top similarity of relevant evidence
    verification_method: str  # "nli", "embedding", "adaptive"
    model_identifier: str
    supporting_evidence: List[EvidencePassageScore] = field(default_factory=list)
    primary_passage: Optional[EvidencePassageScore] = None
    plain_english_explanation: str = ""
    requires_human_review: bool = False
    limitations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


def aggregate_evidence(
    claim_text: str,
    passage_scores: List[EvidencePassageScore],
    entailment_threshold: float = 0.5,
    contradiction_threshold: float = 0.5,
    method: str = "nli",
    model_name: str = "cross-encoder/nli-deberta-v3-base",
) -> AggregatedClaimResult:
    """Aggregates per-passage NLI or similarity scores according to VeriAI policy.

    Args:
        claim_text: The atomic claim under evaluation.
        passage_scores: Evaluated evidence passages with individual probabilities.
        entailment_threshold: Cutoff for considering a passage entailing.
        contradiction_threshold: Cutoff for considering a passage contradicting.
        method: Verification method name.
        model_name: Model identifier.

    Returns:
        AggregatedClaimResult containing audit trail, verdict, and explanation.
    """
    if not passage_scores:
        return AggregatedClaimResult(
            claim_text=claim_text,
            verdict=ClaimVerdict.INSUFFICIENT_EVIDENCE,
            model_score=0.0,
            retrieval_similarity=0.0,
            verification_method=method,
            model_identifier=model_name,
            plain_english_explanation="No relevant evidence passages were found to verify this claim.",
            requires_human_review=True,
            limitations=["Empty evidence set: retrieval returned zero matching passages."],
        )

    # Sort passage scores by entailment and contradiction
    entailing = [p for p in passage_scores if p.entailment_prob >= entailment_threshold]
    contradicting = [p for p in passage_scores if p.contradiction_prob >= contradiction_threshold]

    best_sim = max((p.retrieval_similarity for p in passage_scores), default=0.0)

    # Check for cross-passage conflict (both strong entailment and strong contradiction)
    if entailing and contradicting:
        top_entail = max(entailing, key=lambda p: p.entailment_prob)
        top_contra = max(contradicting, key=lambda p: p.contradiction_prob)

        # Mark both as winning highlights
        top_entail.is_winning = True
        top_contra.is_winning = True

        return AggregatedClaimResult(
            claim_text=claim_text,
            verdict=ClaimVerdict.CONFLICTING_EVIDENCE,
            model_score=max(top_entail.entailment_prob, top_contra.contradiction_prob),
            retrieval_similarity=best_sim,
            verification_method=method,
            model_identifier=model_name,
            supporting_evidence=passage_scores,
            primary_passage=top_contra,
            plain_english_explanation=(
                f"Conflicting evidence detected across retrieved sources. Passage from '{top_entail.doc_id}' "
                f"supports the claim ({top_entail.entailment_prob:.1%}), while passage from '{top_contra.doc_id}' "
                f"directly contradicts it ({top_contra.contradiction_prob:.1%})."
            ),
            requires_human_review=True,
            limitations=["Cross-source disagreement requires human editorial review."],
        )

    if entailing:
        best_passage = max(entailing, key=lambda p: p.entailment_prob)
        best_passage.is_winning = True
        is_borderline = abs(best_passage.entailment_prob - entailment_threshold) < 0.08
        page_str = f" on page {best_passage.page_number}" if best_passage.page_number is not None else ""

        return AggregatedClaimResult(
            claim_text=claim_text,
            verdict=ClaimVerdict.SUPPORTED,
            model_score=best_passage.entailment_prob,
            retrieval_similarity=best_passage.retrieval_similarity,
            verification_method=method,
            model_identifier=model_name,
            supporting_evidence=passage_scores,
            primary_passage=best_passage,
            plain_english_explanation=(
                f"Supported by document '{best_passage.doc_id}'{page_str} with {best_passage.entailment_prob:.1%} entailment confidence."
            ),
            requires_human_review=is_borderline,
            limitations=["Confidence is model-derived; verify primary source for critical decisions."]
            if is_borderline
            else [],
        )

    if contradicting:
        best_passage = max(contradicting, key=lambda p: p.contradiction_prob)
        best_passage.is_winning = True
        is_borderline = abs(best_passage.contradiction_prob - contradiction_threshold) < 0.08
        page_str = f" on page {best_passage.page_number}" if best_passage.page_number is not None else ""

        return AggregatedClaimResult(
            claim_text=claim_text,
            verdict=ClaimVerdict.CONTRADICTED,
            model_score=best_passage.contradiction_prob,
            retrieval_similarity=best_passage.retrieval_similarity,
            verification_method=method,
            model_identifier=model_name,
            supporting_evidence=passage_scores,
            primary_passage=best_passage,
            plain_english_explanation=(
                f"Contradicted by document '{best_passage.doc_id}'{page_str} with {best_passage.contradiction_prob:.1%} contradiction confidence."
            ),
            requires_human_review=is_borderline,
            limitations=["Off-topic context can occasionally trigger false contradiction flags."]
            if is_borderline
            else [],
        )

    # Neither threshold met -> Inconclusive / Insufficient Evidence
    highest_score_passage = max(passage_scores, key=lambda p: max(p.entailment_prob, p.contradiction_prob))
    return AggregatedClaimResult(
        claim_text=claim_text,
        verdict=ClaimVerdict.INSUFFICIENT_EVIDENCE,
        model_score=highest_score_passage.neutral_prob,
        retrieval_similarity=best_sim,
        verification_method=method,
        model_identifier=model_name,
        supporting_evidence=passage_scores,
        primary_passage=highest_score_passage,
        plain_english_explanation=(
            "Available evidence neither explicitly confirms nor refutes this claim (inconclusive relation)."
        ),
        requires_human_review=True,
        limitations=["Retrieved passages lack specific factual statements addressing this claim."],
    )
