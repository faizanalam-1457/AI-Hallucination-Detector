"""Analysis endpoints for VeriAI."""

import time
import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query

from src.api.database import (
    clear_all_analyses,
    delete_analysis,
    get_analyses,
    get_analysis_by_id,
    save_analysis,
)
from src.api.schemas import (
    AnalysisResponse,
    AnalyzeRequest,
    ClaimResultSchema,
    EvidencePassageSchema,
)
from src.claims.extractor import extract_claims
from src.config import get_config
from src.rag.retriever import retrieve_evidence
from src.verification.adaptive_checker import verify_claim_adaptive
from src.verification.embedding_checker import verify_claim_embedding
from src.verification.nli_checker import verify_claim_nli

router = APIRouter(prefix="/analyses", tags=["Analysis"])


@router.post("", response_model=AnalysisResponse)
def analyze_answer(request: AnalyzeRequest):
    """Analyzes an AI-generated answer, decomposes it into atomic claims,
    retrieves evidence, and verifies each claim against the retrieved sources.
    """
    t0 = time.perf_counter()
    analysis_id = f"anl-{uuid.uuid4().hex[:10]}"

    # Stage 1: Decompose claims
    claims = extract_claims(request.answer, method=request.extraction_method)
    if not claims:
        # Fallback to entire answer if decomposition produced nothing
        from src.claims.extractor import Claim

        claims = [Claim(text=request.answer.strip(), source_sentence=request.answer.strip())]

    # Stage 2: Retrieve relevant evidence
    query = f"{request.question or ''} {request.answer}".strip()
    evidence_chunks = retrieve_evidence(
        query=query,
        top_k=request.top_k,
        raw_context=request.evidence_text,
    )

    # Stage 3: Verify each claim
    verified_claims_data: List[Dict[str, Any]] = []
    cfg = get_config()
    model_name = cfg.get("verification", {}).get("nli_model_name", "cross-encoder/nli-deberta-v3-base")

    for idx, claim in enumerate(claims):
        if request.method == "embedding":
            res = verify_claim_embedding(claim.text, evidence_chunks)
            audit_meta = {}
        elif request.method == "nli":
            res = verify_claim_nli(claim.text, evidence_chunks)
            audit_meta = {}
        else:  # "adaptive" (default)
            res, audit = verify_claim_adaptive(
                claim.text,
                evidence_chunks,
                low_threshold=request.adaptive_low_threshold,
                high_threshold=request.adaptive_high_threshold,
            )
            audit_meta = res.metadata.get("adaptive_audit", {})

        primary_dict = None
        if res.primary_passage:
            primary_dict = {
                "chunk_id": res.primary_passage.chunk_id,
                "doc_id": res.primary_passage.doc_id,
                "doc_title": getattr(res.primary_passage, "doc_title", res.primary_passage.doc_id),
                "page_number": res.primary_passage.page_number,
                "text": res.primary_passage.text,
                "retrieval_similarity": res.primary_passage.retrieval_similarity,
                "entailment_prob": res.primary_passage.entailment_prob,
                "contradiction_prob": res.primary_passage.contradiction_prob,
                "neutral_prob": res.primary_passage.neutral_prob,
                "verdict": res.primary_passage.verdict,
                "is_winning": True,
            }

        evidence_list = []
        for p in res.supporting_evidence:
            evidence_list.append(
                {
                    "chunk_id": p.chunk_id,
                    "doc_id": p.doc_id,
                    "doc_title": getattr(p, "doc_title", p.doc_id),
                    "page_number": p.page_number,
                    "text": p.text,
                    "retrieval_similarity": p.retrieval_similarity,
                    "entailment_prob": p.entailment_prob,
                    "contradiction_prob": p.contradiction_prob,
                    "neutral_prob": p.neutral_prob,
                    "verdict": p.verdict,
                    "is_winning": p.is_winning,
                }
            )

        # Stage 3b: Evidence-grounded explanation synthesis
        explanation = res.plain_english_explanation
        explanation_provider = "deterministic"
        if request.use_gemini_explanations:
            from src.services.gemini_service import is_gemini_configured, generate_grounded_explanation
            if is_gemini_configured():
                explanation = generate_grounded_explanation(
                    claim=claim.text,
                    evidence_passages=evidence_list,
                    verdict=res.verdict.value,
                    model_score=float(res.model_score),
                    provider="gemini",
                )
                explanation_provider = "gemini"

        verified_claims_data.append(
            {
                "id": f"{analysis_id}-c{idx}",
                "claim_index": idx,
                "claim_text": claim.text,
                "source_sentence": claim.source_sentence,
                "verdict": res.verdict.value,
                "model_score": float(res.model_score),
                "retrieval_similarity": float(res.retrieval_similarity),
                "verification_method": res.verification_method,
                "model_identifier": res.model_identifier,
                "requires_human_review": res.requires_human_review,
                "plain_english_explanation": explanation,
                "explanation_provider": explanation_provider,
                "limitations": res.limitations,
                "primary_passage": primary_dict,
                "supporting_evidence": evidence_list,
                "audit": audit_meta,
            }
        )

    latency_ms = (time.perf_counter() - t0) * 1000.0

    meta = {
        "extraction_method": request.extraction_method,
        "evidence_source": "direct_input" if request.evidence_text else "indexed_documents",
        "retrieved_chunk_count": len(evidence_chunks),
        "explanation_provider": "gemini" if request.use_gemini_explanations else "deterministic",
    }

    # Stage 4: Persist to SQLite
    save_analysis(
        analysis_id=analysis_id,
        question=request.question,
        answer=request.answer,
        method=request.method,
        model_name=model_name,
        claims=verified_claims_data,
        latency_ms=latency_ms,
        metadata=meta,
    )

    # Retrieve saved analysis to guarantee consistent schema
    saved = get_analysis_by_id(analysis_id)
    if not saved:
        raise HTTPException(status_code=500, detail="Failed to persist analysis record.")

    return saved


@router.get("", response_model=List[Dict[str, Any]])
def list_analyses(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    """Returns paginated list of past verification runs."""
    return get_analyses(limit=limit, offset=offset)


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis_details(analysis_id: str):
    """Retrieves full claim-level and evidence details for a specific analysis."""
    anl = get_analysis_by_id(analysis_id)
    if not anl:
        raise HTTPException(status_code=404, detail=f"Analysis '{analysis_id}' not found.")
    return anl


@router.delete("/{analysis_id}")
def delete_single_analysis(analysis_id: str):
    """Deletes an analysis and all its claim records."""
    success = delete_analysis(analysis_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Analysis '{analysis_id}' not found.")
    return {"status": "deleted", "id": analysis_id}


@router.delete("")
def clear_history():
    """Clears all local analysis history."""
    clear_all_analyses()
    return {"status": "cleared", "message": "All analyses and claim records cleared."}
