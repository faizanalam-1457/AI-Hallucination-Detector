export type ClaimVerdict = 'SUPPORTED' | 'CONTRADICTED' | 'INSUFFICIENT_EVIDENCE' | 'CONFLICTING_EVIDENCE';

export interface EvidencePassage {
  chunk_id: string;
  doc_id: string;
  doc_title?: string;
  page_number?: number;
  text: string;
  retrieval_similarity: number;
  entailment_prob: number;
  contradiction_prob: number;
  neutral_prob: number;
  verdict: string;
  is_winning: boolean;
}

export interface ClaimResult {
  id?: string;
  claim_index: number;
  claim_text: string;
  source_sentence: string;
  verdict: ClaimVerdict;
  model_score: number;
  retrieval_similarity: number;
  verification_method: string;
  model_identifier: string;
  requires_human_review: boolean;
  plain_english_explanation: string;
  explanation_provider?: string;
  limitations?: string[];
  primary_passage?: EvidencePassage;
  supporting_evidence: EvidencePassage[];
}

export interface Analysis {
  id: string;
  question?: string;
  answer_summary: string;
  full_answer: string;
  method: string;
  model_name: string;
  num_claims: number;
  supported_count: number;
  contradicted_count: number;
  insufficient_count: number;
  conflicting_count: number;
  latency_ms: number;
  created_at: string;
  claims: ClaimResult[];
  metadata?: Record<string, any>;
}

export interface DocumentItem {
  id: string;
  filename: string;
  file_type: string;
  file_size_bytes: number;
  page_count: number;
  chunk_count: number;
  is_indexed: boolean;
  is_scanned_warning: boolean;
  warning_message?: string;
  created_at: string;
}

export interface ConfusionMatrix {
  tp: number;
  fp: number;
  tn: number;
  fn: number;
}

export interface Experiment {
  id: string;
  name: string;
  method: string;
  model_name: string;
  dataset_name: string;
  sample_size: number;
  decision_threshold: number;
  macro_f1: number;
  accuracy: number;
  precision: number;
  recall: number;
  supported_f1: number;
  hallucinated_f1: number;
  latency_per_claim_ms: number;
  total_latency_ms: number;
  confusion_matrix: ConfusionMatrix;
  metrics: Record<string, any>;
  config: Record<string, any>;
  created_at: string;
}

export interface BenchmarkDataset {
  id: string;
  name: string;
  size: number;
  version: string;
  license: string;
  task: string;
  description: string;
  label_distribution: Record<string, any>;
  offline_available: boolean;
}

export interface DashboardStats {
  total_analyses: number;
  total_claims: number;
  supported_claims: number;
  contradicted_claims: number;
  insufficient_claims: number;
  conflicting_claims: number;
  total_documents: number;
  total_experiments: number;
  method_distribution: Record<string, number>;
  activity_over_time: Array<{ date: string; analyses: number }>;
  recent_analyses: Array<{
    id: string;
    question?: string;
    answer_summary: string;
    method: string;
    num_claims: number;
    supported_count: number;
    contradicted_count: number;
    insufficient_count: number;
    created_at: string;
  }>;
}

export interface SystemSettings {
  active_models: Record<string, string>;
  device: string;
  retrieval_top_k: number;
  decision_threshold: number;
  adaptive_high_threshold: number;
  adaptive_low_threshold: number;
  chunk_size_words: number;
  chunk_overlap_words: number;
  max_upload_size_mb: number;
  data_retention_days: number;
  theme: string;
  logging_level: string;
  calibration_notice: string;
  providers?: ProvidersStatus;
}

export interface ProviderInfo {
  configured: boolean;
  model: string;
  masked_key?: string | null;
  provider: string;
  base_url?: string;
  limits_notice?: string;
}

export interface ProvidersStatus {
  gemini: ProviderInfo;
  hf_router: ProviderInfo;
}

export type PageId =
  | 'dashboard'
  | 'analyze'
  | 'claim_results'
  | 'evidence_explorer'
  | 'documents'
  | 'research_lab'
  | 'benchmarks'
  | 'history'
  | 'settings';
