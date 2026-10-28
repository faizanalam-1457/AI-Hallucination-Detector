"""Benchmarks and Dataset inspection endpoints for VeriAI."""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query

from src.benchmark.datasets import get_available_datasets_meta, load_benchmark_dataset

router = APIRouter(prefix="/benchmarks", tags=["Benchmarks"])


@router.get("/datasets", response_model=List[Dict[str, Any]])
def list_benchmark_datasets():
    """Returns metadata, schemas, and licenses for supported hallucination benchmarks."""
    return get_available_datasets_meta()


@router.get("/datasets/{dataset_id}/sample")
def get_dataset_samples(dataset_id: str, limit: int = Query(5, ge=1, le=20)):
    """Returns sample rows from a benchmark dataset for inspection."""
    try:
        examples = load_benchmark_dataset(dataset_id, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load dataset '{dataset_id}': {str(e)}")

    return [
        {
            "question": e.question,
            "context_preview": e.context[0][:300] if e.context else "",
            "answer": e.answer,
            "is_hallucinated": e.is_hallucinated,
            "ground_truth_label": "HALLUCINATED" if e.is_hallucinated else "SUPPORTED",
        }
        for e in examples
    ]
