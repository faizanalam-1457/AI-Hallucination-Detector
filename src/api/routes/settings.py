"""System settings and configuration endpoints for VeriAI."""

import torch
from fastapi import APIRouter
from src.api.schemas import SettingsResponse, SettingsUpdateRequest
from src.config import get_config

router = APIRouter(prefix="/settings", tags=["Settings"])

# In-memory runtime override overrides for demo sessions
_RUNTIME_OVERRIDES = {}


def get_active_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps (Apple Silicon GPU)"
    return "cpu"


@router.get("", response_model=SettingsResponse)
def get_system_settings():
    """Returns active models, compute device, threshold configurations, and calibration advisory."""
    cfg = get_config()
    vcfg = cfg.get("verification", {})
    dcfg = cfg.get("documents", {})

    top_k = _RUNTIME_OVERRIDES.get("retrieval_top_k", cfg.get("retrieval", {}).get("top_k", 3))
    dec_thresh = _RUNTIME_OVERRIDES.get("decision_threshold", vcfg.get("entailment_threshold", 0.5))
    high_thresh = _RUNTIME_OVERRIDES.get("adaptive_high_threshold", vcfg.get("adaptive_high_threshold", 0.88))
    low_thresh = _RUNTIME_OVERRIDES.get("adaptive_low_threshold", vcfg.get("adaptive_low_threshold", 0.35))
    chunk_size = _RUNTIME_OVERRIDES.get("chunk_size_words", dcfg.get("chunk_size_words", 150))
    chunk_overlap = _RUNTIME_OVERRIDES.get("chunk_overlap_words", dcfg.get("chunk_overlap_words", 30))
    theme = _RUNTIME_OVERRIDES.get("theme", "dark")
    logging_level = _RUNTIME_OVERRIDES.get("logging_level", "INFO")

    from src.services.gemini_service import get_provider_status
    provider_status = get_provider_status()

    return SettingsResponse(
        active_models={
            "nli_cross_encoder": vcfg.get("nli_model_name", "cross-encoder/nli-deberta-v3-base"),
            "embedding_bi_encoder": cfg.get("embedding", {}).get("model_name", "sentence-transformers/all-MiniLM-L6-v2"),
            "generator": cfg.get("generation", {}).get("local_model_name", "google/flan-t5-base"),
            "gemini_extractor": provider_status["gemini"]["model"],
            "hf_router_model": provider_status["hf_router"]["model"],
        },
        device=get_active_device(),
        retrieval_top_k=top_k,
        decision_threshold=dec_thresh,
        adaptive_high_threshold=high_thresh,
        adaptive_low_threshold=low_thresh,
        chunk_size_words=chunk_size,
        chunk_overlap_words=chunk_overlap,
        max_upload_size_mb=dcfg.get("max_upload_size_mb", 25),
        data_retention_days=30,
        theme=theme,
        logging_level=logging_level,
        calibration_notice=(
            "Research Notice: Confidence scores produced by the NLI cross-encoder and bi-encoder models "
            "are raw softmax / cosine similarity outputs. They reflect relative model confidence and are not "
            "inherently calibrated probabilities unless explicitly calibrated using temperature scaling or isotonic "
            "regression against a held-out validation distribution."
        ),
        providers=provider_status,
    )


@router.get("/providers")
def get_providers():
    """Returns status and configuration details for external LLM providers (Gemini, HuggingFace Router)."""
    from src.services.gemini_service import get_provider_status
    return get_provider_status()


@router.post("", response_model=SettingsResponse)
def update_system_settings(req: SettingsUpdateRequest):
    """Updates runtime threshold and performance settings for the session."""
    if req.retrieval_top_k is not None:
        _RUNTIME_OVERRIDES["retrieval_top_k"] = req.retrieval_top_k
    if req.decision_threshold is not None:
        _RUNTIME_OVERRIDES["decision_threshold"] = req.decision_threshold
    if req.adaptive_high_threshold is not None:
        _RUNTIME_OVERRIDES["adaptive_high_threshold"] = req.adaptive_high_threshold
    if req.adaptive_low_threshold is not None:
        _RUNTIME_OVERRIDES["adaptive_low_threshold"] = req.adaptive_low_threshold
    if req.chunk_size_words is not None:
        _RUNTIME_OVERRIDES["chunk_size_words"] = req.chunk_size_words
    if req.chunk_overlap_words is not None:
        _RUNTIME_OVERRIDES["chunk_overlap_words"] = req.chunk_overlap_words
    if req.theme is not None:
        _RUNTIME_OVERRIDES["theme"] = req.theme
    if req.logging_level is not None:
        _RUNTIME_OVERRIDES["logging_level"] = req.logging_level

    return get_system_settings()
