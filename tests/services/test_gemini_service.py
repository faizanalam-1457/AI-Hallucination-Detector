"""Unit and mock tests for Google Gemini API service and provider integration.

Tests verify:
1. Successful structured claim extraction with mock Gemini responses.
2. Empty and whitespace input handling.
3. Missing API key graceful fallback to local clause decomposition.
4. Malformed JSON handling and fallback.
5. Transient rate limit (429) retry logic.
6. Persistent error handling without application crashes.
7. Claim extractor integration with method="gemini".
8. Evidence-grounded explanation synthesis.
9. Deterministic explanation fallback when unconfigured.
10. Secret masking in status endpoints (no key leakage).
"""

from unittest.mock import MagicMock, patch
import pytest

from src.claims.extractor import extract_claims, Claim
from src.services.gemini_service import (
    extract_claims_gemini,
    extract_claims_hf_router,
    generate_grounded_explanation,
    get_provider_status,
    is_gemini_configured,
)


def test_empty_input_returns_empty_list():
    assert extract_claims_gemini("") == []
    assert extract_claims_gemini("   ") == []


def test_missing_api_key_falls_back_to_local_decomposition(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("Gemini_API_KEY", raising=False)

    answer = "India became independent in 1947 and New Delhi is the capital."
    claims = extract_claims_gemini(answer)
    assert len(claims) >= 1
    assert any("1947" in c for c in claims)


def test_successful_gemini_claim_extraction(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-gemini-key-123456789")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = (
        '{"claims": ['
        '"India became independent in 1947.",'
        '"New Delhi is the capital of India.",'
        '"The Sun revolves around the Earth."'
        "]}"
    )
    mock_client.models.generate_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client):
        answer = "India became independent in 1947. New Delhi is the capital of India. The Sun revolves around the Earth."
        claims = extract_claims_gemini(answer)

        assert len(claims) == 3
        assert claims[0] == "India became independent in 1947."
        assert claims[1] == "New Delhi is the capital of India."
        assert claims[2] == "The Sun revolves around the Earth."


def test_malformed_json_falls_back_to_local(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-gemini-key-123456789")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is not valid JSON at all."
    mock_client.models.generate_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client):
        answer = "Alexander Fleming discovered penicillin in 1928."
        claims = extract_claims_gemini(answer)

        # Must not crash, should fall back to rule-based decomposition
        assert len(claims) >= 1
        assert "penicillin" in claims[0].lower()


def test_transient_rate_limit_retry_succeeds(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-gemini-key-123456789")

    mock_client = MagicMock()
    mock_success = MagicMock()
    mock_success.text = '{"claims": ["Paris is the capital of France."]}'

    # Fail on first call with 429, succeed on second call
    mock_client.models.generate_content.side_effect = [
        Exception("Error 429: Resource has been exhausted (e.g. check quota)"),
        mock_success,
    ]

    with patch("google.genai.Client", return_value=mock_client):
        with patch("time.sleep", return_value=None):  # Avoid waiting in unit tests
            claims = extract_claims_gemini("Paris is the capital of France.")
            assert len(claims) == 1
            assert claims[0] == "Paris is the capital of France."
            assert mock_client.models.generate_content.call_count == 2


def test_persistent_api_error_falls_back_gracefully(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-gemini-key-123456789")

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("Internal 500 error from API")

    with patch("google.genai.Client", return_value=mock_client):
        answer = "DNA has a double helix structure."
        claims = extract_claims_gemini(answer)
        assert len(claims) >= 1
        assert "DNA" in claims[0]


def test_extract_claims_with_method_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-gemini-key-123456789")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"claims": ["Lincoln was the sixteenth President.", "He was assassinated in 1865."]}'
    mock_client.models.generate_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client):
        answer = "Lincoln was the sixteenth President and he was assassinated in 1865."
        claim_objects = extract_claims(answer, method="gemini")

        assert len(claim_objects) == 2
        assert all(isinstance(c, Claim) for c in claim_objects)
        assert claim_objects[0].text == "Lincoln was the sixteenth President."
        assert "1865" in claim_objects[1].text


def test_hf_router_extraction_with_mock(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_dummy_token_123456")

    mock_openai = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"claims": ["Water freezes at 0 degrees Celsius."]}'
    mock_openai.return_value.chat.completions.create.return_value.choices = [mock_choice]

    with patch("openai.OpenAI", mock_openai):
        claims = extract_claims_hf_router("Water freezes at 0 degrees Celsius.")
        assert len(claims) == 1
        assert "Water freezes" in claims[0]


def test_grounded_explanation_generation_with_mock(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-gemini-key-123456789")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Supported by Document 1 which confirms Lincoln served as the 16th US President."
    mock_client.models.generate_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client):
        evidence = [
            {"doc_id": "us_presidents.txt", "text": "Abraham Lincoln was the 16th president.", "page_number": 1}
        ]
        explanation = generate_grounded_explanation(
            claim="Lincoln was the 16th President",
            evidence_passages=evidence,
            verdict="SUPPORTED",
            model_score=0.98,
            provider="gemini",
        )
        assert "Supported by Document 1" in explanation


def test_grounded_explanation_fallback_when_unconfigured(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("Gemini_API_KEY", raising=False)

    evidence = [
        {"doc_id": "lincoln_bio.pdf", "text": "Lincoln was the 16th president.", "page_number": 3, "is_winning": True}
    ]
    explanation = generate_grounded_explanation(
        claim="Lincoln was the 16th President",
        evidence_passages=evidence,
        verdict="SUPPORTED",
        model_score=0.95,
        provider="gemini",
    )
    assert "Supported by 'lincoln_bio.pdf' on page 3 with 95.0% entailment confidence." in explanation


def test_get_provider_status_masks_secrets(monkeypatch):
    test_key = "dummy-test-key-for-masking-123456789"
    monkeypatch.setenv("GEMINI_API_KEY", test_key)

    status = get_provider_status()
    gemini_info = status["gemini"]

    assert gemini_info["configured"] is True
    assert gemini_info["masked_key"] == "dumm...6789"
    # Crucial security guarantee: full key is never in public status
    assert test_key not in str(gemini_info)
