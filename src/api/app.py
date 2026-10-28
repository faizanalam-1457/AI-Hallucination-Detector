"""FastAPI Application for VeriAI — AI Hallucination Detection & Evidence Verification Platform."""

import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import analysis, benchmarks, dashboard, documents, experiments, settings
from src.config import get_config, PROJECT_ROOT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("veriai.api")

app = FastAPI(
    title="VeriAI — AI Hallucination Detection & Evidence Verification Platform",
    description=(
        "Research-grade hallucination detection platform. Decomposes AI-generated text into atomic claims, "
        "retrieves evidence with page-level citations, performs NLI entailment and adaptive verification, "
        "and benchmarks detection performance against empirical datasets."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Enable CORS for React/Vite development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error handling {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


# Health & Model Discovery
@app.get("/api/health", tags=["System"])
def health_check():
    """Health check endpoint confirming API status and SQLite connectivity."""
    from src.api.database import get_db_path

    db_ok = get_db_path().exists()
    return {
        "status": "healthy",
        "service": "VeriAI Platform",
        "version": "1.0.0",
        "database_connected": db_ok,
    }


@app.get("/api/models", tags=["System"])
def list_available_models():
    """Returns available and active models for generation, verification, and embedding."""
    cfg = get_config()
    from src.services.gemini_service import get_provider_status
    provider_status = get_provider_status()
    return {
        "verification_models": [
            {
                "id": "cross-encoder/nli-deberta-v3-base",
                "name": "DeBERTa-v3 Base NLI Cross-Encoder",
                "type": "nli_cross_encoder",
                "params": "184M",
                "labels": ["entailment", "neutral", "contradiction"],
                "active": True,
            },
            {
                "id": "embedding_similarity_baseline",
                "name": "Cosine Similarity Baseline (all-MiniLM-L6-v2)",
                "type": "bi_encoder_similarity",
                "params": "22.7M",
                "active": True,
            },
            {
                "id": "adaptive_verification_cascade",
                "name": "Adaptive Verification Engine (Two-Stage Cascade)",
                "type": "adaptive_cascade",
                "active": True,
            },
        ],
        "embedding_models": [
            {
                "id": cfg.get("embedding", {}).get("model_name", "sentence-transformers/all-MiniLM-L6-v2"),
                "name": "all-MiniLM-L6-v2",
                "dimension": 384,
                "active": True,
            }
        ],
        "generation_models": [
            {
                "id": cfg.get("generation", {}).get("local_model_name", "google/flan-t5-base"),
                "name": "FLAN-T5 Base (Local Seq2Seq)",
                "active": cfg.get("generation", {}).get("backend") == "local",
            }
        ],
        "claim_extraction_providers": [
            {
                "id": "gemini",
                "name": "Google Gemini API (Structured Output)",
                "model": provider_status["gemini"]["model"],
                "configured": provider_status["gemini"]["configured"],
            },
            {
                "id": "hf_router",
                "name": "Hugging Face Router (DeepSeek)",
                "model": provider_status["hf_router"]["model"],
                "configured": provider_status["hf_router"]["configured"],
            },
            {
                "id": "decomposed",
                "name": "Atomic Clause Decomposer (Local)",
                "configured": True,
            },
            {
                "id": "sentence",
                "name": "Sentence Splitting Baseline (Local)",
                "configured": True,
            },
        ],
    }


# Register all sub-routers under /api
app.include_router(analysis.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(experiments.router, prefix="/api")
app.include_router(benchmarks.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(settings.router, prefix="/api")

# Serve frontend build if exists
dist_dir = PROJECT_ROOT / "frontend" / "dist"
if dist_dir.exists() and (dist_dir / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")
