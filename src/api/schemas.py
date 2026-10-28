"""Pydantic v2 validation schemas for VeriAI API endpoints."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidencePassageSchema(BaseModel):
    chunk_id: str
    doc_id: str
    doc_title: Optional[str] = None
    page_number: Optional[int] = None
    text: str
    retrieval_similarity: float = 0.0
    entailment_prob: float = 0.0
    contradiction_prob: float = 0.0
    neutral_prob: float = 0.0
    verdict: str = "neutral"
    is_winning: bool = False


class ClaimResultSchema(BaseModel):
    id: Optional[str] = None
    claim_index: int = 0
    claim_text: str
    source_sentence: str
    verdict: str
    model_score: float
    retrieval_similarity: float
    verification_method: str
    model_identifier: str
    requires_human_review: bool = False
    plain_english_explanation: str = ""
    explanation_provider: Optional[str] = "deterministic"
    limitations: List[str] = Field(default_factory=list)
    primary_passage: Optional[EvidencePassageSchema] = None
    supporting_evidence: List[EvidencePassageSchema] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    question: Optional[str] = None
    answer: str = Field(..., min_length=1, description="AI-generated answer text to verify")
    evidence_text: Optional[str] = Field(None, description="Optional raw context or evidence text")
    document_ids: Optional[List[str]] = Field(default_factory=list, description="IDs of uploaded documents to search")
    method: str = Field("adaptive", description="Verification method: 'adaptive', 'nli', 'embedding'")
    extraction_method: str = Field("gemini", description="Claim extraction: 'gemini', 'hf_router', 'decomposed', 'sentence'")
    use_gemini_explanations: bool = Field(True, description="Whether to generate evidence-grounded explanations with Gemini")
    top_k: int = Field(3, ge=1, le=20, description="Max evidence passages to retrieve")
    decision_threshold: float = Field(0.5, ge=0.0, le=1.0)
    adaptive_low_threshold: Optional[float] = Field(0.35, ge=0.0, le=1.0)
    adaptive_high_threshold: Optional[float] = Field(0.88, ge=0.0, le=1.0)


class ProviderInfo(BaseModel):
    configured: bool
    model: str
    masked_key: Optional[str] = None
    provider: str
    base_url: Optional[str] = None
    limits_notice: Optional[str] = None


class ProvidersStatusResponse(BaseModel):
    gemini: ProviderInfo
    hf_router: ProviderInfo


class AnalysisResponse(BaseModel):
    id: str
    question: Optional[str] = None
    answer_summary: str
    full_answer: str
    method: str
    model_name: str
    num_claims: int
    supported_count: int
    contradicted_count: int
    insufficient_count: int
    conflicting_count: int
    latency_ms: float
    created_at: str
    claims: List[ClaimResultSchema] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size_bytes: int
    page_count: int
    chunk_count: int
    is_indexed: bool
    is_scanned_warning: bool
    warning_message: Optional[str] = None
    created_at: str


class RunExperimentRequest(BaseModel):
    name: Optional[str] = None
    method: str = Field("adaptive", description="'adaptive', 'nli', 'embedding'")
    dataset_name: str = Field("smoke_test", description="'smoke_test', 'halueval', 'ragtruth'")
    sample_limit: int = Field(16, ge=2, le=500)
    decision_threshold: float = Field(0.5, ge=0.1, le=0.9)
    extraction_method: str = Field("sentence", description="'sentence' or 'decomposed'")


class ExperimentResponse(BaseModel):
    id: str
    name: str
    method: str
    model_name: str
    dataset_name: str
    sample_size: int
    decision_threshold: float
    macro_f1: float
    accuracy: float
    precision: float
    recall: float
    supported_f1: float
    hallucinated_f1: float
    latency_per_claim_ms: float
    total_latency_ms: float
    confusion_matrix: Dict[str, int]
    metrics: Dict[str, Any]
    config: Dict[str, Any]
    created_at: str


class DashboardStatsResponse(BaseModel):
    total_analyses: int
    total_claims: int
    supported_claims: int
    contradicted_claims: int
    insufficient_claims: int
    conflicting_claims: int
    total_documents: int
    total_experiments: int
    method_distribution: Dict[str, int]
    activity_over_time: List[Dict[str, Any]]
    recent_analyses: List[Dict[str, Any]]


class SettingsResponse(BaseModel):
    active_models: Dict[str, str]
    device: str
    retrieval_top_k: int
    decision_threshold: float
    adaptive_high_threshold: float
    adaptive_low_threshold: float
    chunk_size_words: int
    chunk_overlap_words: int
    max_upload_size_mb: int
    data_retention_days: int
    theme: str
    logging_level: str
    calibration_notice: str
    providers: Optional[Dict[str, Any]] = None


class SettingsUpdateRequest(BaseModel):
    retrieval_top_k: Optional[int] = Field(None, ge=1, le=20)
    decision_threshold: Optional[float] = Field(None, ge=0.1, le=0.99)
    adaptive_high_threshold: Optional[float] = Field(None, ge=0.5, le=0.99)
    adaptive_low_threshold: Optional[float] = Field(None, ge=0.1, le=0.6)
    chunk_size_words: Optional[int] = Field(None, ge=50, le=500)
    chunk_overlap_words: Optional[int] = Field(None, ge=0, le=100)
    theme: Optional[str] = None
    logging_level: Optional[str] = None
