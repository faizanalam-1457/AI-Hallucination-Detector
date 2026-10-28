from src.claims.extractor import extract_claims, extract_decomposed_claims
from src.claims.decomposer import decompose_sentence


def test_compound_sentence_splits_into_two_atomic_claims():
    text = "The scientist was born in 1980 and received an award in 2020."
    claims = extract_claims(text, method="decomposed")
    assert len(claims) == 2
    assert "born in 1980" in claims[0].text
    assert "received an award in 2020" in claims[1].text
    assert all(c.source_sentence == text for c in claims)


def test_independent_clauses_with_pronoun_split():
    text = "Lincoln was president and he was assassinated in 1865."
    claims = extract_decomposed_claims(text)
    assert len(claims) == 2
    assert claims[0].text == "Lincoln was president."
    assert claims[1].text == "He was assassinated in 1865."


def test_semicolon_clauses_split():
    text = "Paris is the capital of France; Rome is the capital of Italy."
    claims = extract_decomposed_claims(text)
    assert len(claims) == 2
    assert "Paris is the capital of France" in claims[0].text
    assert "Rome is the capital of Italy" in claims[1].text


def test_plain_sentence_remains_single_claim():
    text = "Montevideo is the capital of Uruguay."
    claims = extract_decomposed_claims(text)
    assert len(claims) == 1
    assert claims[0].text == "Montevideo is the capital of Uruguay."


def test_noun_list_not_falsely_split():
    # E.g. "He likes apples and oranges." - no verb after "and", so should remain one claim
    text = "He likes apples and oranges."
    claims = extract_decomposed_claims(text)
    assert len(claims) == 1
    assert claims[0].text == "He likes apples and oranges."
