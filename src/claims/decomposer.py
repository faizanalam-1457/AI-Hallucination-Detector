"""Syntactic and heuristic clause decomposition for atomic claim extraction.

Breaks compound and multi-proposition sentences into atomic, individually
verifiable factual statements while maintaining the link to the original
source sentence.

Example:
    "The scientist was born in 1980 and received an award in 2020."
    ->
    Claim(text="The scientist was born in 1980.", source_sentence="...")
    Claim(text="The scientist received an award in 2020.", source_sentence="...")
"""

import re
from typing import List


# Common coordinating conjunctions that join clauses or verb phrases
CONJUNCTIONS = [
    " and also ",
    " and later ",
    " and subsequently ",
    " and eventually ",
    " as well as ",
    " and ",
    " but ",
    " whereas ",
    " while ",
    " although ",
]

# Common past/present auxiliary and action verbs that signal a predicate
VERB_PATTERNS = re.compile(
    r"\b(is|was|were|are|am|has|have|had|served|won|received|published|born|died|graduated|joined|became|worked|discovered|invented|created|founded|led|attended|wrote|earned|developed|signed|built|moved|stated|claimed|held|defeated)\b",
    re.IGNORECASE,
)

# Pronoun subjects that can start an independent clause
PRONOUNS = {"he", "she", "it", "they", "this", "who"}


def _clean_claim_text(text: str) -> str:
    """Cleans punctuation, capitalization, and whitespace."""
    text = text.strip().strip(",;:")
    if not text:
        return ""
    # Ensure starts with uppercase
    text = text[0].upper() + text[1:]
    # Ensure ends with period if missing ending punctuation
    if not text.endswith((".", "!", "?")):
        text += "."
    return text


def _extract_subject_phrase(clause: str) -> str:
    """Attempts to identify the grammatical subject of the leading clause."""
    tokens = clause.strip().split()
    if not tokens:
        return ""

    # Look for the first verb in the clause
    verb_match = VERB_PATTERNS.search(clause)
    if verb_match and verb_match.start() > 0:
        candidate_subject = clause[: verb_match.start()].strip()
        # Clean up leading conjunctions or adverbs
        candidate_subject = re.sub(
            r"^(although|while|whereas|however|additionally|furthermore|moreover|also)\s+",
            "",
            candidate_subject,
            flags=re.IGNORECASE,
        ).strip()
        if candidate_subject and len(candidate_subject.split()) <= 6:
            return candidate_subject

    # Fallback: take first 1 to 3 words
    first_words = tokens[:min(3, len(tokens))]
    return " ".join(first_words)


def decompose_sentence(sentence: str) -> List[str]:
    """Decomposes a single sentence into atomic factual claims.

    Args:
        sentence: A single sentence string.

    Returns:
        List of atomic claim strings. If no decomposition applies,
        returns [cleaned_sentence].
    """
    cleaned = sentence.strip()
    if not cleaned:
        return []

    # First check for semicolon-delimited independent clauses
    if ";" in cleaned:
        parts = [p.strip() for p in cleaned.split(";") if p.strip()]
        if len(parts) > 1 and all(len(p.split()) >= 3 for p in parts):
            claims = []
            for part in parts:
                claims.extend(decompose_sentence(part))
            return [c for c in claims if c]

    # Check for compound predicates / coordinate clauses
    for conj in CONJUNCTIONS:
        if conj in cleaned:
            parts = cleaned.split(conj, 1)
            left, right = parts[0].strip(), parts[1].strip()

            # Both sides must have at least 2 words
            if len(left.split()) < 3 or len(right.split()) < 2:
                continue

            # Does the right side contain a verb?
            right_has_verb = bool(VERB_PATTERNS.search(right))
            if not right_has_verb:
                # E.g. "apples and oranges" - list of nouns, not a compound claim
                continue

            # Determine subject for the right side
            right_first_word = right.split()[0].lower().rstrip(",;:")
            left_subject = _extract_subject_phrase(left)

            left_claim = _clean_claim_text(left)

            if right_first_word in PRONOUNS:
                # E.g. "... and he was assassinated in 1865."
                right_claim = _clean_claim_text(right)
            elif left_subject:
                # E.g. "... and received an award in 2020." -> "The scientist received an award in 2020."
                right_claim = _clean_claim_text(f"{left_subject} {right}")
            else:
                right_claim = _clean_claim_text(right)

            # Recurse on sub-parts in case of multiple conjunctions
            left_claims = decompose_sentence(left) if any(c in left for c in CONJUNCTIONS) else [left_claim]
            right_claims = decompose_sentence(right) if any(c in right for c in CONJUNCTIONS) else [right_claim]

            combined = [c for c in left_claims + right_claims if c]
            if len(combined) >= 2:
                return combined

    return [_clean_claim_text(cleaned)]
