import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.database import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True


def test_list_models():
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert "verification_models" in data
    assert any(m["id"] == "cross-encoder/nli-deberta-v3-base" for m in data["verification_models"])


def test_dashboard_stats_empty_or_populated():
    response = client.get("/api/stats/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "total_analyses" in data
    assert "total_claims" in data
    assert "supported_claims" in data
    assert "contradicted_claims" in data


def test_list_benchmark_datasets():
    response = client.get("/api/benchmarks/datasets")
    assert response.status_code == 200
    datasets = response.json()
    ids = [d["id"] for d in datasets]
    assert "smoke_test" in ids
    assert "halueval" in ids
    assert "ragtruth" in ids


def test_get_settings():
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "active_models" in data
    assert "device" in data
    assert "calibration_notice" in data


def test_analyze_with_direct_evidence_text():
    payload = {
        "question": "Was Lincoln the sixteenth President?",
        "answer": "Lincoln was the sixteenth President. He was born in 1809.",
        "evidence_text": "Abraham Lincoln was the sixteenth President of the United States. He was born on February 12, 1809.",
        "method": "embedding",  # fast test without heavy cross-encoder download
        "extraction_method": "decomposed",
        "top_k": 3,
        "decision_threshold": 0.5,
    }
    response = client.post("/api/analyses", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"].startswith("anl-")
    assert data["num_claims"] >= 2
    assert len(data["claims"]) >= 2
    assert all("verdict" in c for c in data["claims"])

    # Verify listed in /api/analyses
    list_res = client.get("/api/analyses")
    assert list_res.status_code == 200
    analyses = list_res.json()
    assert any(a["id"] == data["id"] for a in analyses)

    # Verify single fetch
    get_res = client.get(f"/api/analyses/{data['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == data["id"]
