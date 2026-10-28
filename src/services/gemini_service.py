"""Google Gemini API service and LLM provider integration for VeriAI.

Provides:
1. Secure client initialization using GEMINI_API_KEY from environment.
2. Structured atomic claim extraction with schema validation and bounded retries.
3. Fallback to local rule-based decomposition when unconfigured or on transient failure.
4. Grounded, evidence-conditioned explanation generation (strictly adhering to verification verdicts).
5. Secondary support for OpenAI-compatible Hugging Face Router endpoint.
6. Diagnostic health checking without secret leakage.
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.claims.decomposer import decompose_sentence
from src.claims.extractor import split_into_sentences
from src.config import get_config

logger = logging.getLogger(__name__)


class ExtractedClaimsPayload(BaseModel):
    """Pydantic schema for structured output from Gemini."""
    claims: List[str] = Field(
        default_factory=list,
        description="List of distinct, self-contained atomic factual assertions extracted from the text.",
    )


def get_gemini_api_key() -> Optional[str]:
    """Retrieves the Gemini API key securely from environment variables.
    Checks GEMINI_API_KEY and Gemini_API_KEY.
    """
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("Gemini_API_KEY")
    if key and key.strip():
        return key.strip()
    return None


def get_hf_token() -> Optional[str]:
    """Retrieves the Hugging Face token securely from environment variables."""
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if token and token.strip():
        return token.strip()
    return None


def is_gemini_configured() -> bool:
    """Returns True if a non-empty Gemini API key is configured in the environment."""
    return get_gemini_api_key() is not None


def is_hf_router_configured() -> bool:
    """Returns True if a non-empty Hugging Face token is configured in the environment."""
    return get_hf_token() is not None


def get_gemini_model_name() -> str:
    """Returns the configured Gemini model name."""
    cfg = get_config()
    default_from_cfg = cfg.get("gemini", {}).get("default_model", "gemini-2.5-flash")
    return os.environ.get("GEMINI_MODEL", default_from_cfg)


def get_hf_router_model_name() -> str:
    """Returns the configured Hugging Face Router model name."""
    cfg = get_config()
    default_from_cfg = cfg.get("hf_router", {}).get("default_model", "deepseek-ai/DeepSeek-V4.1-Flash-1017:novita")
    return os.environ.get("HF_MODEL", default_from_cfg)


def get_hf_router_base_url() -> str:
    """Returns the Hugging Face Router base URL."""
    cfg = get_config()
    default_from_cfg = cfg.get("hf_router", {}).get("base_url", "https://router.huggingface.co/v1")
    return os.environ.get("HF_ROUTER_BASE_URL", default_from_cfg)


def get_provider_status() -> Dict[str, Any]:
    """Returns public diagnostic status for LLM providers without exposing raw keys."""
    gemini_key = get_gemini_api_key()
    hf_token = get_hf_token()

    masked_gemini = None
    if gemini_key:
        if len(gemini_key) > 8:
            masked_gemini = f"{gemini_key[:4]}...{gemini_key[-4:]}"
        else:
            masked_gemini = "***configured***"

    masked_hf = None
    if hf_token:
        if len(hf_token) > 8:
            masked_hf = f"{hf_token[:4]}...{hf_token[-4:]}"
        else:
            masked_hf = "***configured***"

    return {
        "gemini": {
            "configured": is_gemini_configured(),
            "model": get_gemini_model_name(),
            "masked_key": masked_gemini,
            "provider": "google-genai",
            "limits_notice": "Subject to Google AI Studio rate limits and quota tier.",
        },
        "hf_router": {
            "configured": is_hf_router_configured(),
            "model": get_hf_router_model_name(),
            "base_url": get_hf_router_base_url(),
            "masked_key": masked_hf,
            "provider": "huggingface-router",
            "limits_notice": "Subject to Hugging Face Inference Router credits and rate limits.",
        },
    }


def extract_claims_gemini(answer: str, max_retries: int = 2) -> List[str]:
    """Extracts atomic factual claims using the official Google GenAI SDK.

    Uses structured JSON output to guarantee a list of claims.
    If the API key is missing or an error occurs, gracefully falls back
    to local rule-based clause decomposition without raising an unhandled exception.

    Args:
        answer: The text to decompose into atomic factual claims.
        max_retries: Number of bounded retries for transient errors.

    Returns:
        List of atomic claim strings.
    """
    answer_clean = answer.strip() if answer else ""
    if not answer_clean:
        return []

    api_key = get_gemini_api_key()
    if not api_key:
        logger.info("GEMINI_API_KEY not configured. Falling back to local rule-based clause decomposer.")
        return _fallback_local_extraction(answer_clean)

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.warning("google-genai library is not installed. Falling back to local decomposition.")
        return _fallback_local_extraction(answer_clean)

    prompt = (
        "You are an expert NLP fact-checking assistant for VeriAI. "
        "Your task is to decompose the provided text into individual, atomic factual claims. "
        "\n\nRules:"
        "\n1. Preserve the factual meaning of the original text exactly."
        "\n2. Separate compound sentences and conjunctions into distinct, self-contained propositions."
        "\n3. Do NOT add external facts, extrapolate, or invent information not asserted in the text."
        "\n4. Omit personal opinions, rhetorical questions, and conversational pleasantries."
        "\n5. Avoid duplicate claims."
        "\n6. Ensure each extracted claim is a coherent, standalone sentence suitable for verification."
        f"\n\nInput Text:\n\"\"\"{answer_clean}\"\"\""
    )

    model_name = get_gemini_model_name()
    attempt = 0
    last_error: Optional[Exception] = None

    while attempt <= max_retries:
        try:
            client = genai.Client(api_key=api_key)
            config = types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=ExtractedClaimsPayload,
            )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )

            raw_text = response.text if hasattr(response, "text") and response.text else ""
            if not raw_text:
                logger.warning("Gemini returned empty response text. Falling back to local extraction.")
                return _fallback_local_extraction(answer_clean)

            parsed = json.loads(raw_text)
            claims_raw = parsed.get("claims", [])
            claims = [str(c).strip() for c in claims_raw if str(c).strip()]

            # Deduplicate while preserving order
            seen = set()
            unique_claims = []
            for c in claims:
                c_norm = c.lower()
                if c_norm not in seen:
                    seen.add(c_norm)
                    unique_claims.append(c)

            if unique_claims:
                return unique_claims
            else:
                logger.warning("Gemini returned empty claims list. Falling back to local extraction.")
                return _fallback_local_extraction(answer_clean)

        except Exception as exc:
            last_error = exc
            attempt += 1
            err_str = str(exc)
            # Check for transient rate limit or network errors
            is_transient = "429" in err_str or "quota" in err_str.lower() or "503" in err_str or "timeout" in err_str.lower()
            if is_transient and attempt <= max_retries:
                backoff = min(1.5 * (2 ** (attempt - 1)), 5.0)
                logger.warning(f"Gemini API transient error (attempt {attempt}/{max_retries+1}): {err_str[:120]}. Retrying in {backoff:.1f}s...")
                time.sleep(backoff)
                continue
            else:
                logger.error(f"Gemini extraction failed: {err_str[:200]}. Falling back safely to local extraction.")
                break

    return _fallback_local_extraction(answer_clean)


def extract_claims_hf_router(answer: str, max_retries: int = 1) -> List[str]:
    """Extracts atomic factual claims using the Hugging Face Router (OpenAI-compatible) endpoint."""
    answer_clean = answer.strip() if answer else ""
    if not answer_clean:
        return []

    token = get_hf_token()
    if not token:
        logger.info("HF_TOKEN not configured. Falling back to local rule-based clause decomposer.")
        return _fallback_local_extraction(answer_clean)

    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai library not installed. Falling back to local decomposition.")
        return _fallback_local_extraction(answer_clean)

    base_url = get_hf_router_base_url()
    model_name = get_hf_router_model_name()

    prompt = (
        "Decompose the following text into individual atomic factual claims. "
        "Return a JSON object with a single key 'claims' containing an array of string claims. "
        "Do not invent facts. Return only valid JSON.\n\n"
        f"Text:\n{answer_clean}"
    )

    try:
        client = OpenAI(base_url=base_url, api_key=token, timeout=20.0)
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a precise factual claim extraction engine. Always output JSON."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = completion.choices[0].message.content or "{}"
        data = json.loads(content)
        claims = data.get("claims", [])
        clean_claims = [str(c).strip() for c in claims if str(c).strip()]
        if clean_claims:
            return clean_claims
    except Exception as exc:
        logger.warning(f"HF Router extraction failed: {str(exc)[:150]}. Falling back to local extraction.")

    return _fallback_local_extraction(answer_clean)


def generate_grounded_explanation(
    claim: str,
    evidence_passages: List[Dict[str, Any]],
    verdict: str,
    model_score: float,
    provider: str = "gemini",
) -> str:
    """Synthesizes a concise, evidence-grounded explanation justifying why the
    evidence supports, contradicts, or is insufficient for the given claim.

    Rules:
    1. Must strictly uphold the verification verdict (e.g., SUPPORTED, CONTRADICTED).
    2. Must cite the provided evidence passages and never hallucinate external facts or citations.
    3. If evidence is insufficient, explicitly states why the retrieved text fails to substantiate.
    4. Falls back to a deterministic explanation on any error or missing key.

    Args:
        claim: The verified atomic claim.
        evidence_passages: List of evidence passages (dicts with 'doc_id', 'text', 'page_number').
        verdict: Verification verdict (SUPPORTED, CONTRADICTED, INSUFFICIENT_EVIDENCE).
        model_score: Winning probability score from the NLI or cascade model.
        provider: 'gemini' or 'hf_router' or 'local'.

    Returns:
        1-2 sentence evidence-grounded explanation.
    """
    if provider == "local" or not is_gemini_configured():
        return _deterministic_explanation(claim, evidence_passages, verdict, model_score)

    api_key = get_gemini_api_key()
    if not api_key:
        return _deterministic_explanation(claim, evidence_passages, verdict, model_score)

    # Format passages for the prompt
    passages_summary = []
    for i, p in enumerate(evidence_passages[:3]):
        doc_ref = p.get("doc_title") or p.get("doc_id", "Evidence Doc")
        page_ref = f" (Page {p['page_number']})" if p.get("page_number") else ""
        text_snippet = p.get("text", "").strip()[:300]
        passages_summary.append(f"Passage {i+1} [{doc_ref}{page_ref}]: \"{text_snippet}\"")

    passages_block = "\n".join(passages_summary) if passages_summary else "No retrieved passages."

    prompt = (
        "You are an epistemic audit explainer for VeriAI. "
        "Write a concise 1 to 2 sentence justification explaining WHY the retrieved evidence "
        f"leads to the verdict: {verdict}.\n\n"
        f"Claim: \"{claim}\"\n"
        f"Verification Verdict: {verdict} (Model entailment/confidence: {model_score:.1%})\n"
        f"Retrieved Evidence:\n{passages_block}\n\n"
        "Strict Guidelines:\n"
        f"1. You MUST uphold the verdict: {verdict}. Never contradict this verdict.\n"
        "2. Directly reference details from the retrieved passages.\n"
        "3. Never hallucinate outside facts, citations, or document names.\n"
        "4. If INSUFFICIENT_EVIDENCE, state that the retrieved evidence does not contain facts to prove or disprove the claim.\n"
        "5. Output ONLY the 1-2 sentence explanation, without quotes or prefixes."
    )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=150,
        )
        response = client.models.generate_content(
            model=get_gemini_model_name(),
            contents=prompt,
            config=config,
        )
        explanation = response.text.strip() if hasattr(response, "text") and response.text else ""
        if explanation:
            return explanation
    except Exception as exc:
        logger.warning(f"Gemini explanation generation failed: {str(exc)[:120]}. Using deterministic explanation.")

    return _deterministic_explanation(claim, evidence_passages, verdict, model_score)


def _deterministic_explanation(
    claim: str,
    evidence_passages: List[Dict[str, Any]],
    verdict: str,
    model_score: float,
) -> str:
    """Deterministic fallback explanation based on passage metadata."""
    if not evidence_passages:
        return "No relevant evidence passages were found to verify this claim."

    winning = next((p for p in evidence_passages if p.get("is_winning")), evidence_passages[0])
    doc_id = winning.get("doc_title") or winning.get("doc_id", "source")
    page_str = f" on page {winning['page_number']}" if winning.get("page_number") is not None else ""

    if verdict == "SUPPORTED":
        return f"Supported by '{doc_id}'{page_str} with {model_score:.1%} entailment confidence."
    elif verdict == "CONTRADICTED":
        return f"Contradicted by '{doc_id}'{page_str} with {model_score:.1%} contradiction confidence."
    elif verdict == "CONFLICTING_EVIDENCE":
        return f"Conflicting evidence detected across retrieved documents regarding this claim."
    else:
        return "Available evidence neither explicitly confirms nor refutes this claim (inconclusive relation)."


def _fallback_local_extraction(text: str) -> List[str]:
    """Local fallback using sentence splitting and clause decomposition."""
    sentences = split_into_sentences(text)
    if not sentences:
        return []
    claims = []
    for s in sentences:
        sub_claims = decompose_sentence(s)
        for sub in sub_claims:
            if sub.strip():
                claims.append(sub.strip())
    return claims if claims else sentences
