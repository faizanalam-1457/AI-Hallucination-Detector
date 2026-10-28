"""Research Lab Experiment Runner & Comparison endpoints."""

import csv
import io
import time
import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query, Response

from src.api.database import (
    get_experiment_by_id,
    get_experiments,
    save_experiment_record,
)
from src.api.schemas import ExperimentResponse, RunExperimentRequest
from src.benchmark.datasets import load_benchmark_dataset
from src.benchmark.metrics import compute_extended_metrics
from src.claims.extractor import extract_claims
from src.config import get_config
from src.verification.adaptive_checker import verify_claim_adaptive
from src.verification.embedding_checker import verify_claim_embedding
from src.verification.nli_checker import verify_claim_nli

router = APIRouter(prefix="/experiments", tags=["Research Lab"])


def _as_evidence(context: List[str]) -> List[Dict[str, Any]]:
    return [{"chunk_id": f"ctx-{i}", "doc_id": "Context", "text": text} for i, text in enumerate(context)]


@router.post("/run", response_model=ExperimentResponse)
def run_experiment(req: RunExperimentRequest):
    """Executes an experimental evaluation across a labeled hallucination benchmark."""
    try:
        examples = load_benchmark_dataset(req.dataset_name, limit=req.sample_limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load dataset '{req.dataset_name}': {str(e)}")

    if not examples:
        raise HTTPException(status_code=400, detail="Dataset returned zero examples.")

    exp_id = f"exp-{uuid.uuid4().hex[:10]}"
    name = req.name or f"{req.method.upper()} on {req.dataset_name} (N={len(examples)})"

    cfg = get_config()
    model_name = (
        cfg.get("verification", {}).get("nli_model_name", "cross-encoder/nli-deberta-v3-base")
        if req.method in ("nli", "adaptive")
        else cfg.get("embedding", {}).get("model_name", "sentence-transformers/all-MiniLM-L6-v2")
    )

    y_true: List[bool] = []
    y_pred: List[bool] = []
    y_probs: List[float] = []

    t0 = time.perf_counter()
    claim_count = 0

    for ex in examples:
        y_true.append(ex.is_hallucinated)
        evidence = _as_evidence(ex.context)
        claims = extract_claims(ex.answer, method=req.extraction_method)
        claim_count += len(claims)

        claim_results = []
        for c in claims:
            if req.method == "embedding":
                r = verify_claim_embedding(c.text, evidence)
                # Hallucinated if not supported
                is_h = not r.verdict.value.startswith("SUPPORTED")
                score = 1.0 - r.model_score
            elif req.method == "nli":
                r = verify_claim_nli(c.text, evidence)
                is_h = r.verdict.value != "SUPPORTED"
                score = r.model_score if is_h else (1.0 - r.model_score)
            else:  # "adaptive"
                r, _ = verify_claim_adaptive(c.text, evidence)
                is_h = r.verdict.value != "SUPPORTED"
                score = r.model_score if is_h else (1.0 - r.model_score)

            claim_results.append((is_h, score))

        # Whole answer hallucination verdict: true if ANY claim is hallucinated/unsupported
        ans_hallucinated = any(is_h for is_h, _ in claim_results) if claim_results else False
        ans_score = max((s for _, s in claim_results), default=0.5) if claim_results else 0.5

        y_pred.append(ans_hallucinated)
        y_probs.append(ans_score)

    total_latency_ms = (time.perf_counter() - t0) * 1000.0
    latency_per_claim_ms = total_latency_ms / max(claim_count, 1)

    # Compute comprehensive research metrics
    metrics = compute_extended_metrics(y_true, y_pred, y_probs)

    record = {
        "id": exp_id,
        "name": name,
        "method": req.method,
        "model_name": model_name,
        "dataset_name": req.dataset_name,
        "sample_size": len(examples),
        "decision_threshold": req.decision_threshold,
        "macro_f1": metrics["macro_f1"],
        "accuracy": metrics["accuracy"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "supported_f1": metrics["supported_f1"],
        "hallucinated_f1": metrics["hallucinated_f1"],
        "latency_per_claim_ms": latency_per_claim_ms,
        "total_latency_ms": total_latency_ms,
        "confusion_matrix": metrics["confusion_matrix"],
        "metrics": metrics,
        "config": {
            "dataset": req.dataset_name,
            "method": req.method,
            "extraction_method": req.extraction_method,
            "threshold": req.decision_threshold,
            "claim_count": claim_count,
        },
    }

    save_experiment_record(record)
    saved = get_experiment_by_id(exp_id)
    if not saved:
        raise HTTPException(status_code=500, detail="Failed to save experiment.")

    return saved


@router.get("", response_model=List[ExperimentResponse])
def list_experiments(limit: int = Query(50, ge=1, le=100)):
    """Lists past research benchmark experiments."""
    return get_experiments(limit=limit)


@router.get("/{exp_id}", response_model=ExperimentResponse)
def get_single_experiment(exp_id: str):
    """Retrieves full metrics and configuration of an experiment."""
    exp = get_experiment_by_id(exp_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{exp_id}' not found.")
    return exp


@router.get("/{exp_id}/export")
def export_experiment(exp_id: str, format: str = Query("json", pattern="^(json|csv)$")):
    """Exports experiment results as formatted JSON or CSV."""
    exp = get_experiment_by_id(exp_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{exp_id}' not found.")

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Experiment ID", exp["id"]])
        writer.writerow(["Name", exp["name"]])
        writer.writerow(["Method", exp["method"]])
        writer.writerow(["Model", exp["model_name"]])
        writer.writerow(["Dataset", exp["dataset_name"]])
        writer.writerow(["Sample Size", exp["sample_size"]])
        writer.writerow(["Accuracy", f"{exp['accuracy']:.4f}"])
        writer.writerow(["Macro F1", f"{exp['macro_f1']:.4f}"])
        writer.writerow(["Precision (Hallucination)", f"{exp['precision']:.4f}"])
        writer.writerow(["Recall (Hallucination)", f"{exp['recall']:.4f}"])
        writer.writerow(["Supported F1", f"{exp['supported_f1']:.4f}"])
        writer.writerow(["Hallucinated F1", f"{exp['hallucinated_f1']:.4f}"])
        writer.writerow(["Latency per Claim (ms)", f"{exp['latency_per_claim_ms']:.2f}"])
        writer.writerow(["Total Latency (ms)", f"{exp['total_latency_ms']:.2f}"])
        writer.writerow(["True Positives", exp["confusion_matrix"].get("tp", 0)])
        writer.writerow(["False Positives", exp["confusion_matrix"].get("fp", 0)])
        writer.writerow(["True Negatives", exp["confusion_matrix"].get("tn", 0)])
        writer.writerow(["False Negatives", exp["confusion_matrix"].get("fn", 0)])

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={exp_id}.csv"},
        )

    return exp
