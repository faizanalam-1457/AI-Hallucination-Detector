import {
  Analysis,
  BenchmarkDataset,
  DashboardStats,
  DocumentItem,
  Experiment,
  ProvidersStatus,
  SystemSettings,
} from '../types';

const API_BASE = '/api';

export async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    let errorMsg = `HTTP Error ${res.status}: ${res.statusText}`;
    try {
      const errorJson = await res.json();
      if (errorJson.detail) errorMsg = errorJson.detail;
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return res.json();
}

// -------------------------------------------------------------
// Dashboard & Analytics
// -------------------------------------------------------------
export async function getDashboardStats(): Promise<DashboardStats> {
  return fetchApi<DashboardStats>('/stats/dashboard');
}

// -------------------------------------------------------------
// Analysis
// -------------------------------------------------------------
export interface AnalyzeParams {
  question?: string;
  answer: string;
  evidence_text?: string;
  document_ids?: string[];
  method: 'adaptive' | 'nli' | 'embedding';
  extraction_method: 'gemini' | 'hf_router' | 'decomposed' | 'sentence';
  use_gemini_explanations?: boolean;
  top_k?: number;
  decision_threshold?: number;
  adaptive_low_threshold?: number;
  adaptive_high_threshold?: number;
}

export async function analyzeAnswer(params: AnalyzeParams): Promise<Analysis> {
  return fetchApi<Analysis>('/analyses', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function getAnalyses(limit = 50, offset = 0): Promise<Analysis[]> {
  return fetchApi<Analysis[]>(`/analyses?limit=${limit}&offset=${offset}`);
}

export async function getAnalysis(id: string): Promise<Analysis> {
  return fetchApi<Analysis>(`/analyses/${id}`);
}

export async function deleteAnalysis(id: string): Promise<{ status: string }> {
  return fetchApi<{ status: string }>(`/analyses/${id}`, {
    method: 'DELETE',
  });
}

export async function clearAllAnalyses(): Promise<{ status: string }> {
  return fetchApi<{ status: string }>('/analyses', {
    method: 'DELETE',
  });
}

// -------------------------------------------------------------
// Documents
// -------------------------------------------------------------
export async function getDocuments(): Promise<DocumentItem[]> {
  return fetchApi<DocumentItem[]>('/documents');
}

export async function uploadDocument(file: File): Promise<DocumentItem> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    let msg = `Upload failed (${res.status})`;
    try {
      const err = await res.json();
      if (err.detail) msg = err.detail;
    } catch {
      // ignore
    }
    throw new Error(msg);
  }

  return res.json();
}

export async function getDocumentPreview(docId: string): Promise<any> {
  return fetchApi<any>(`/documents/${docId}/preview`);
}

export async function deleteDocument(docId: string): Promise<{ status: string }> {
  return fetchApi<{ status: string }>(`/documents/${docId}`, {
    method: 'DELETE',
  });
}

export async function reindexDocument(docId: string): Promise<any> {
  return fetchApi<any>(`/documents/${docId}/reindex`, {
    method: 'POST',
  });
}

// -------------------------------------------------------------
// Experiments & Research Lab
// -------------------------------------------------------------
export interface RunExperimentParams {
  name?: string;
  method: 'adaptive' | 'nli' | 'embedding';
  dataset_name: string;
  sample_limit: number;
  decision_threshold: number;
  extraction_method: 'sentence' | 'decomposed';
}

export async function runExperiment(params: RunExperimentParams): Promise<Experiment> {
  return fetchApi<Experiment>('/experiments/run', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function getExperiments(): Promise<Experiment[]> {
  return fetchApi<Experiment[]>('/experiments');
}

export async function getExperiment(id: string): Promise<Experiment> {
  return fetchApi<Experiment>(`/experiments/${id}`);
}

// -------------------------------------------------------------
// Benchmarks
// -------------------------------------------------------------
export async function getBenchmarkDatasets(): Promise<BenchmarkDataset[]> {
  return fetchApi<BenchmarkDataset[]>('/benchmarks/datasets');
}

export async function getDatasetSamples(datasetId: string, limit = 5): Promise<any[]> {
  return fetchApi<any[]>(`/benchmarks/datasets/${datasetId}/sample?limit=${limit}`);
}

// -------------------------------------------------------------
// Settings
// -------------------------------------------------------------
export async function getSettings(): Promise<SystemSettings> {
  return fetchApi<SystemSettings>('/settings');
}

export async function getProvidersStatus(): Promise<ProvidersStatus> {
  return fetchApi<ProvidersStatus>('/settings/providers');
}

export async function updateSettings(params: Partial<SystemSettings>): Promise<SystemSettings> {
  return fetchApi<SystemSettings>('/settings', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}
