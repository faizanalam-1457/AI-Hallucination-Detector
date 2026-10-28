"""SQLite database persistence layer for VeriAI.

Stores analyses, claim-level audits, uploaded document metadata, and research
benchmark experiment results. Provides thread-safe connections with WAL mode.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import get_config, PROJECT_ROOT


def get_db_path() -> Path:
    cfg = get_config()
    db_rel = cfg.get("paths", {}).get("database_path", "data/veriai.db")
    db_path = PROJECT_ROOT / db_rel
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_connection() -> sqlite3.Connection:
    """Creates a SQLite connection with Row factory and WAL mode enabled."""
    conn = sqlite3.connect(str(get_db_path()), timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    """Initializes the database schema if tables do not exist."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                page_count INTEGER NOT NULL,
                chunk_count INTEGER NOT NULL,
                is_indexed INTEGER NOT NULL DEFAULT 1,
                is_scanned_warning INTEGER NOT NULL DEFAULT 0,
                warning_message TEXT,
                storage_path TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                question TEXT,
                answer_summary TEXT NOT NULL,
                full_answer TEXT NOT NULL,
                method TEXT NOT NULL,
                model_name TEXT NOT NULL,
                num_claims INTEGER NOT NULL,
                supported_count INTEGER NOT NULL,
                contradicted_count INTEGER NOT NULL,
                insufficient_count INTEGER NOT NULL,
                conflicting_count INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                metadata_json TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS claims (
                id TEXT PRIMARY KEY,
                analysis_id TEXT NOT NULL,
                claim_index INTEGER NOT NULL,
                claim_text TEXT NOT NULL,
                source_sentence TEXT NOT NULL,
                verdict TEXT NOT NULL,
                model_score REAL NOT NULL,
                retrieval_similarity REAL NOT NULL,
                verification_method TEXT NOT NULL DEFAULT 'nli',
                model_identifier TEXT NOT NULL DEFAULT 'cross-encoder/nli-deberta-v3-base',
                requires_human_review INTEGER NOT NULL,
                plain_english_explanation TEXT,
                explanation_provider TEXT NOT NULL DEFAULT 'deterministic',
                primary_chunk_id TEXT,
                primary_doc_id TEXT,
                primary_page_number INTEGER,
                evidence_json TEXT,
                FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                method TEXT NOT NULL,
                model_name TEXT NOT NULL,
                dataset_name TEXT NOT NULL,
                sample_size INTEGER NOT NULL,
                decision_threshold REAL NOT NULL,
                macro_f1 REAL NOT NULL,
                accuracy REAL NOT NULL,
                precision REAL NOT NULL,
                recall REAL NOT NULL,
                supported_f1 REAL NOT NULL,
                hallucinated_f1 REAL NOT NULL,
                latency_per_claim_ms REAL NOT NULL,
                total_latency_ms REAL NOT NULL,
                confusion_matrix_json TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                config_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_claims_analysis_id ON claims(analysis_id);
            CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_experiments_created_at ON experiments(created_at DESC);
            """
        )
        try:
            conn.execute("ALTER TABLE claims ADD COLUMN explanation_provider TEXT DEFAULT 'deterministic'")
        except sqlite3.OperationalError:
            pass

# Initialize DB on module load
init_db()


# ---------------------------------------------------------------------------
# Analyses DAO
# ---------------------------------------------------------------------------

def save_analysis(
    analysis_id: str,
    question: Optional[str],
    answer: str,
    method: str,
    model_name: str,
    claims: List[Dict[str, Any]],
    latency_ms: float,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    answer_summary = answer[:150] + ("..." if len(answer) > 150 else "")

    supported = sum(1 for c in claims if c.get("verdict") == "SUPPORTED")
    contradicted = sum(1 for c in claims if c.get("verdict") == "CONTRADICTED")
    insufficient = sum(1 for c in claims if c.get("verdict") == "INSUFFICIENT_EVIDENCE")
    conflicting = sum(1 for c in claims if c.get("verdict") == "CONFLICTING_EVIDENCE")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO analyses (
                id, question, answer_summary, full_answer, method, model_name,
                num_claims, supported_count, contradicted_count, insufficient_count,
                conflicting_count, latency_ms, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analysis_id,
                question,
                answer_summary,
                answer,
                method,
                model_name,
                len(claims),
                supported,
                contradicted,
                insufficient,
                conflicting,
                latency_ms,
                json.dumps(metadata or {}),
                created_at,
            ),
        )

        for idx, c in enumerate(claims):
            cid = f"{analysis_id}-c{idx}"
            primary = c.get("primary_passage") or {}
            conn.execute(
                """
                INSERT INTO claims (
                    id, analysis_id, claim_index, claim_text, source_sentence,
                    verdict, model_score, retrieval_similarity, verification_method,
                    model_identifier, requires_human_review, plain_english_explanation,
                    explanation_provider, primary_chunk_id, primary_doc_id, primary_page_number, evidence_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cid,
                    analysis_id,
                    idx,
                    c.get("claim_text", ""),
                    c.get("source_sentence", c.get("claim_text", "")),
                    c.get("verdict", "INSUFFICIENT_EVIDENCE"),
                    float(c.get("model_score", 0.0)),
                    float(c.get("retrieval_similarity", 0.0)),
                    c.get("verification_method", method),
                    c.get("model_identifier", model_name),
                    1 if c.get("requires_human_review") else 0,
                    c.get("plain_english_explanation", ""),
                    c.get("explanation_provider", "deterministic"),
                    primary.get("chunk_id"),
                    primary.get("doc_id"),
                    primary.get("page_number"),
                    json.dumps(c.get("supporting_evidence", [])),
                ),
            )


def get_analyses(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, question, answer_summary, method, model_name,
                   num_claims, supported_count, contradicted_count,
                   insufficient_count, conflicting_count, latency_ms, created_at
            FROM analyses
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def get_analysis_by_id(analysis_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        if not row:
            return None
        analysis = dict(row)
        analysis["metadata"] = json.loads(analysis.get("metadata_json") or "{}")

        claim_rows = conn.execute(
            "SELECT * FROM claims WHERE analysis_id = ? ORDER BY claim_index ASC", (analysis_id,)
        ).fetchall()

        claims = []
        for cr in claim_rows:
            cd = dict(cr)
            cd["requires_human_review"] = bool(cd["requires_human_review"])
            evidence_list = json.loads(cd.get("evidence_json") or "[]")
            cd["supporting_evidence"] = evidence_list

            primary = None
            if cd.get("primary_chunk_id"):
                matching_ev = next((e for e in evidence_list if e.get("chunk_id") == cd["primary_chunk_id"]), None)
                if matching_ev:
                    primary = matching_ev
                else:
                    primary = {
                        "chunk_id": cd["primary_chunk_id"],
                        "doc_id": cd.get("primary_doc_id", "doc"),
                        "doc_title": cd.get("primary_doc_id", "doc"),
                        "page_number": cd.get("primary_page_number"),
                        "text": "",
                        "retrieval_similarity": cd.get("retrieval_similarity", 0.0),
                        "entailment_prob": cd.get("model_score", 0.0) if cd.get("verdict") == "SUPPORTED" else 0.0,
                        "contradiction_prob": cd.get("model_score", 0.0) if cd.get("verdict") == "CONTRADICTED" else 0.0,
                        "neutral_prob": 0.0,
                        "verdict": cd.get("verdict", "").lower(),
                        "is_winning": True,
                    }
            cd["primary_passage"] = primary
            cd["explanation_provider"] = cd.get("explanation_provider") or "deterministic"
            cd["limitations"] = []
            claims.append(cd)

        analysis["claims"] = claims
        return analysis



def delete_analysis(analysis_id: str) -> bool:
    with get_connection() as conn:
        res = conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
        return res.rowcount > 0


def clear_all_analyses() -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM claims;")
        conn.execute("DELETE FROM analyses;")


# ---------------------------------------------------------------------------
# Documents DAO
# ---------------------------------------------------------------------------

def save_document_record(
    doc_id: str,
    filename: str,
    file_type: str,
    file_size_bytes: int,
    page_count: int,
    chunk_count: int,
    is_scanned_warning: bool = False,
    warning_message: Optional[str] = None,
    storage_path: Optional[str] = None,
) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO documents (
                id, filename, file_type, file_size_bytes, page_count,
                chunk_count, is_indexed, is_scanned_warning, warning_message,
                storage_path, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            """,
            (
                doc_id,
                filename,
                file_type,
                file_size_bytes,
                page_count,
                chunk_count,
                1 if is_scanned_warning else 0,
                warning_message,
                storage_path,
                created_at,
            ),
        )


def get_all_documents() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
        docs = []
        for r in rows:
            d = dict(r)
            d["is_indexed"] = bool(d["is_indexed"])
            d["is_scanned_warning"] = bool(d["is_scanned_warning"])
            docs.append(d)
        return docs


def get_document_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["is_indexed"] = bool(d["is_indexed"])
        d["is_scanned_warning"] = bool(d["is_scanned_warning"])
        return d


def delete_document_record(doc_id: str) -> bool:
    with get_connection() as conn:
        res = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        return res.rowcount > 0


# ---------------------------------------------------------------------------
# Experiments DAO
# ---------------------------------------------------------------------------

def save_experiment_record(record: Dict[str, Any]) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO experiments (
                id, name, method, model_name, dataset_name, sample_size,
                decision_threshold, macro_f1, accuracy, precision, recall,
                supported_f1, hallucinated_f1, latency_per_claim_ms,
                total_latency_ms, confusion_matrix_json, metrics_json,
                config_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["name"],
                record["method"],
                record["model_name"],
                record["dataset_name"],
                record["sample_size"],
                float(record.get("decision_threshold", 0.5)),
                float(record["macro_f1"]),
                float(record["accuracy"]),
                float(record["precision"]),
                float(record["recall"]),
                float(record["supported_f1"]),
                float(record["hallucinated_f1"]),
                float(record["latency_per_claim_ms"]),
                float(record["total_latency_ms"]),
                json.dumps(record.get("confusion_matrix", {})),
                json.dumps(record.get("metrics", {})),
                json.dumps(record.get("config", {})),
                created_at,
            ),
        )


def get_experiments(limit: int = 50) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM experiments ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        exps = []
        for r in rows:
            d = dict(r)
            d["confusion_matrix"] = json.loads(d.get("confusion_matrix_json") or "{}")
            d["metrics"] = json.loads(d.get("metrics_json") or "{}")
            d["config"] = json.loads(d.get("config_json") or "{}")
            exps.append(d)
        return exps


def get_experiment_by_id(exp_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM experiments WHERE id = ?", (exp_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["confusion_matrix"] = json.loads(d.get("confusion_matrix_json") or "{}")
        d["metrics"] = json.loads(d.get("metrics_json") or "{}")
        d["config"] = json.loads(d.get("config_json") or "{}")
        return d


# ---------------------------------------------------------------------------
# Dashboard Analytics DAO
# ---------------------------------------------------------------------------

def get_dashboard_stats() -> Dict[str, Any]:
    with get_connection() as conn:
        total_analyses = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        total_claims = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]

        verdict_counts = conn.execute(
            """
            SELECT
                SUM(supported_count) as supported,
                SUM(contradicted_count) as contradicted,
                SUM(insufficient_count) as insufficient,
                SUM(conflicting_count) as conflicting
            FROM analyses
            """
        ).fetchone()

        method_distribution_rows = conn.execute(
            "SELECT method, COUNT(*) as count FROM analyses GROUP BY method"
        ).fetchall()
        method_distribution = {r["method"]: r["count"] for r in method_distribution_rows}

        activity_rows = conn.execute(
            """
            SELECT SUBSTR(created_at, 1, 10) as day, COUNT(*) as count
            FROM analyses
            GROUP BY day
            ORDER BY day ASC
            LIMIT 14
            """
        ).fetchall()
        activity = [{"date": r["day"], "analyses": r["count"]} for r in activity_rows]

        recent = conn.execute(
            """
            SELECT id, question, answer_summary, method, num_claims,
                   supported_count, contradicted_count, insufficient_count,
                   created_at
            FROM analyses
            ORDER BY created_at DESC
            LIMIT 5
            """
        ).fetchall()

        total_docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        total_experiments = conn.execute("SELECT COUNT(*) FROM experiments").fetchone()[0]

        return {
            "total_analyses": total_analyses,
            "total_claims": total_claims,
            "supported_claims": verdict_counts["supported"] or 0,
            "contradicted_claims": verdict_counts["contradicted"] or 0,
            "insufficient_claims": verdict_counts["insufficient"] or 0,
            "conflicting_claims": verdict_counts["conflicting"] or 0,
            "total_documents": total_docs,
            "total_experiments": total_experiments,
            "method_distribution": method_distribution,
            "activity_over_time": activity,
            "recent_analyses": [dict(r) for r in recent],
        }
