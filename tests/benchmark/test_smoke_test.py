from src.benchmark.datasets import load_smoke_test, load_ragtruth, get_available_datasets_meta, load_benchmark_dataset
from src.benchmark.metrics import compute_extended_metrics, compute_expected_calibration_error


def test_smoke_test_is_balanced_and_non_empty():
    examples = load_smoke_test()
    assert len(examples) == 16
    supported = [e for e in examples if not e.is_hallucinated]
    hallucinated = [e for e in examples if e.is_hallucinated]
    assert len(supported) == 8
    assert len(hallucinated) == 8
    assert all(e.question and e.context and e.answer for e in examples)


def test_ragtruth_mock_fallback_returns_examples():
    examples = load_ragtruth(mock_fallback=True, limit=4)
    assert len(examples) == 4
    assert any(e.is_hallucinated for e in examples)
    assert any(not e.is_hallucinated for e in examples)


def test_get_available_datasets_meta():
    meta = get_available_datasets_meta()
    ids = [d["id"] for d in meta]
    assert "smoke_test" in ids
    assert "halueval" in ids
    assert "ragtruth" in ids


def test_load_benchmark_dataset_by_name():
    smoke = load_benchmark_dataset("smoke_test")
    assert len(smoke) == 16
    rag = load_benchmark_dataset("ragtruth", limit=2)
    assert len(rag) == 2


def test_compute_extended_metrics():
    y_true = [True, True, False, False]
    y_pred = [True, False, False, False]
    y_probs = [0.9, 0.4, 0.1, 0.2]
    metrics = compute_extended_metrics(y_true, y_pred, y_probs)

    assert "macro_f1" in metrics
    assert "supported_f1" in metrics
    assert "hallucinated_f1" in metrics
    assert "confusion_matrix" in metrics
    cm = metrics["confusion_matrix"]
    assert cm["tp"] == 1
    assert cm["fn"] == 1
    assert cm["tn"] == 2
    assert cm["fp"] == 0
    assert "ece" in metrics
    assert "brier_score" in metrics
