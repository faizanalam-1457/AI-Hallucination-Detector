"""Breaks a generated answer into individual "atomic claims" -- short,
self-contained factual statements -- so each one can be checked against
the retrieved documents independently. A hallucination often hides inside
one clause of an otherwise-supported sentence, so claim-level checking is
more precise than checking the whole answer as one block.

Current approach: sentence splitting. Each sentence in the answer becomes
one Claim. This is the simplest possible decomposition -- it doesn't split
compound sentences ("Lincoln was president and he was assassinated in
1865" stays one claim, even though it asserts two facts), and a regex
splitter will mis-split on abbreviations (e.g. "Gen. Grant" reads as two
sentences). Both are known, accepted limitations at this stage.

Planned upgrade: replace this with an LLM prompt ("list the atomic
factual claims in this text") to decompose compound sentences into
single-fact statements, similar to the decomposition step used in the
RAGTruth / FActScore literature. The Claim dataclass already separates
`text` (the claim) from `source_sentence` (what it was extracted from) so
that upgrade doesn't require changing this module's public interface --
today they're identical, but a future LLM-based splitter would produce
multiple Claims per source_sentence.

split_into_sentences() below is also reused by
verification/nli_checker.py to break retrieved evidence chunks into
sentence-level premises before NLI scoring -- cross-encoder NLI models
are trained on single-sentence (premise, hypothesis) pairs and their
entailment signal degrades badly on multi-sentence premises (verified
empirically: the same true claim scored 98.7% entailment against its
single source sentence but only 0.3% against the full ~150-word chunk
containing that sentence). Keeping one sentence-splitting implementation
means both call sites inherit the same (documented) behavior and
limitations rather than drifting apart.
"""

import re
from dataclasses import dataclass

from src.claims.decomposer import decompose_sentence

# Splits on a sentence-ending punctuation mark (. ! ?) followed by
# whitespace and the start of a new sentence (uppercase letter, digit, or
# opening quote). The lookbehind/lookahead keeps the punctuation attached
# to the sentence it ends, rather than consuming it as a separator.
_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9"\'])')


@dataclass
class Claim:
    text: str
    source_sentence: str


def split_into_sentences(text: str) -> list[str]:
    """Splits `text` into sentences using the punctuation + capitalization
    heuristic described in this module's docstring. Returns an empty list
    for empty/whitespace-only input.
    """
    text = text.strip()
    if not text:
        return []
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def _find_best_source_sentence(claim_text: str, sentences: list[str]) -> str:
    """Finds the most likely source sentence in answer that corresponds to claim_text."""
    if not sentences:
        return claim_text
    claim_lower = claim_text.lower()
    for s in sentences:
        if claim_lower in s.lower():
            return s
    # Word overlap heuristic
    claim_words = set(claim_lower.split())
    best_sentence = sentences[0]
    best_overlap = -1
    for s in sentences:
        overlap = len(claim_words.intersection(set(s.lower().split())))
        if overlap > best_overlap:
            best_overlap = overlap
            best_sentence = s
    return best_sentence


def extract_claims(answer: str, method: str = "sentence") -> list[Claim]:
    """Splits `answer` into atomic claims.

    Args:
        answer: The generated answer text to decompose.
        method: Extraction strategy.
            - "gemini" / "llm": Google Gemini API structured extraction (falls back to clause decomposition).
            - "hf_router" / "deepseek": Hugging Face Router endpoint extraction.
            - "decomposed" / "clause": Rule-based compound sentence and clause decomposition.
            - "sentence" (default): 1 Claim per sentence baseline.

    Returns:
        A list of Claim objects, in the order they appear in `answer`.
        Returns an empty list for empty/whitespace-only input.
    """
    sentences = split_into_sentences(answer)
    if not sentences:
        return []

    # Gemini API extraction
    if method in ("gemini", "llm"):
        from src.services.gemini_service import extract_claims_gemini

        raw_claims = extract_claims_gemini(answer)
        if raw_claims:
            return [
                Claim(text=c, source_sentence=_find_best_source_sentence(c, sentences))
                for c in raw_claims
            ]

    # Hugging Face Router extraction
    if method in ("hf_router", "deepseek"):
        from src.services.gemini_service import extract_claims_hf_router

        raw_claims = extract_claims_hf_router(answer)
        if raw_claims:
            return [
                Claim(text=c, source_sentence=_find_best_source_sentence(c, sentences))
                for c in raw_claims
            ]

    # Rule-based clause decomposition
    if method in ("decomposed", "clause", "atomic"):
        claims = []
        for sentence in sentences:
            sub_claims = decompose_sentence(sentence)
            for sub in sub_claims:
                claims.append(Claim(text=sub, source_sentence=sentence))
        return claims

    # Default sentence-level extraction
    return [Claim(text=s, source_sentence=s) for s in sentences]


def extract_decomposed_claims(answer: str) -> list[Claim]:
    """Convenience helper for atomic claim decomposition."""
    return extract_claims(answer, method="decomposed")


def extract_gemini_claims(answer: str) -> list[Claim]:
    """Convenience helper for Gemini-assisted atomic claim extraction."""
    return extract_claims(answer, method="gemini")

