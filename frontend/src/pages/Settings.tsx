import React, { useEffect, useState } from 'react';
import {
  Settings as SettingsIcon,
  Cpu,
  Sliders,
  ShieldAlert,
  Save,
  CheckCircle2,
  AlertTriangle,
  FolderTree,
  Scale,
  RefreshCw,
  Sparkles,
  Key,
  ExternalLink,
} from 'lucide-react';
import { SystemSettings } from '../types';
import { getSettings, updateSettings } from '../services/api';

interface SettingsProps {
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
}

export const Settings: React.FC<SettingsProps> = ({ theme, onToggleTheme }) => {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedSuccess, setSavedSuccess] = useState(false);

  // Form states
  const [topK, setTopK] = useState(3);
  const [threshold, setThreshold] = useState(0.5);
  const [adaptiveHigh, setAdaptiveHigh] = useState(0.88);
  const [adaptiveLow, setAdaptiveLow] = useState(0.35);
  const [chunkSize, setChunkSize] = useState(150);
  const [chunkOverlap, setChunkOverlap] = useState(30);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const data = await getSettings();
      setSettings(data);
      setTopK(data.retrieval_top_k);
      setThreshold(data.decision_threshold);
      setAdaptiveHigh(data.adaptive_high_threshold);
      setAdaptiveLow(data.adaptive_low_threshold);
      setChunkSize(data.chunk_size_words);
      setChunkOverlap(data.chunk_overlap_words);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch settings.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSavedSuccess(false);

    try {
      const updated = await updateSettings({
        retrieval_top_k: topK,
        decision_threshold: threshold,
        adaptive_high_threshold: adaptiveHigh,
        adaptive_low_threshold: adaptiveLow,
        chunk_size_words: chunkSize,
        chunk_overlap_words: chunkOverlap,
      });
      setSettings(updated);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to update settings.');
    } finally {
      setSaving(false);
    }
  };

  if (loading || !settings) {
    return <div className="p-12 text-center text-sm text-slate-400">Loading system settings...</div>;
  }

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            System & Research Configuration
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Compute hardware preferences, model architecture parameters, and probability calibration guidelines.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm">
          {error}
        </div>
      )}

      {savedSuccess && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>Configuration saved successfully.</span>
        </div>
      )}

      {/* Model Architectures & Compute Device Panel */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-white">
          <Cpu className="w-4 h-4 text-cyan-400" />
          <span>Model Architecture & Hardware Runtime</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
            <span className="text-slate-400 font-medium">Active Compute Device</span>
            <div className="text-sm font-bold font-mono text-cyan-400 uppercase">{settings.device}</div>
            <p className="text-[11px] text-slate-500">Auto-detected via PyTorch hardware backend.</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
            <span className="text-slate-400 font-medium">NLI Cross-Encoder</span>
            <div className="text-sm font-bold font-mono text-indigo-400">
              {settings.active_models.nli_cross_encoder}
            </div>
            <p className="text-[11px] text-slate-500">184M parameters, trained on MNLI+SNLI+FEVER.</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
            <span className="text-slate-400 font-medium">Dense Bi-Encoder</span>
            <div className="text-sm font-bold font-mono text-slate-200">
              {settings.active_models.embedding_bi_encoder}
            </div>
            <p className="text-[11px] text-slate-500">384-dimensional dense semantic embeddings.</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
            <span className="text-slate-400 font-medium">Local Text Generator</span>
            <div className="text-sm font-bold font-mono text-slate-200">
              {settings.active_models.generator}
            </div>
            <p className="text-[11px] text-slate-500">Instruction-tuned seq2seq generation model.</p>
          </div>
        </div>
      </div>

      {/* LLM Providers & API Status Panel */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <span>LLM Providers & External API Diagnostics</span>
          </div>
          <span className="text-xs text-slate-400">Zero-Leakage Key Architecture</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          {/* Google Gemini Card */}
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-indigo-400" />
                Google Gemini API
              </span>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold ${
                  settings.providers?.gemini?.configured
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                }`}
              >
                {settings.providers?.gemini?.configured ? 'Active & Configured' : 'Missing API Key'}
              </span>
            </div>

            <div className="space-y-1 text-slate-400">
              <div className="flex justify-between">
                <span>Model:</span>
                <span className="font-mono text-slate-200 font-medium">
                  {settings.providers?.gemini?.model || 'gemini-2.5-flash'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>SDK:</span>
                <span className="font-mono text-slate-300">google-genai</span>
              </div>
              <div className="flex justify-between">
                <span>Masked Key:</span>
                <span className="font-mono text-slate-300">
                  {settings.providers?.gemini?.masked_key || 'None (local fallback)'}
                </span>
              </div>
            </div>

            <p className="text-[11px] text-slate-500 pt-1 border-t border-slate-900">
              Usage is subject to Google AI Studio quota tiers and pricing limits. To configure or update, set{' '}
              <code className="text-indigo-300">GEMINI_API_KEY</code> in your root <code className="text-indigo-300">.env</code> file.
            </p>
          </div>

          {/* Hugging Face Router Card */}
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-cyan-400" />
                Hugging Face Router (DeepSeek)
              </span>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold ${
                  settings.providers?.hf_router?.configured
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'bg-slate-800 text-slate-400'
                }`}
              >
                {settings.providers?.hf_router?.configured ? 'Configured' : 'Optional / Standby'}
              </span>
            </div>

            <div className="space-y-1 text-slate-400">
              <div className="flex justify-between">
                <span>Model:</span>
                <span className="font-mono text-slate-200 font-medium truncate max-w-[200px]">
                  {settings.providers?.hf_router?.model || 'DeepSeek-V4.1-Flash'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Endpoint:</span>
                <span className="font-mono text-slate-300">router.huggingface.co/v1</span>
              </div>
              <div className="flex justify-between">
                <span>Masked Token:</span>
                <span className="font-mono text-slate-300">
                  {settings.providers?.hf_router?.masked_key || 'None'}
                </span>
              </div>
            </div>

            <p className="text-[11px] text-slate-500 pt-1 border-t border-slate-900">
              OpenAI-compatible inference router. Configure with{' '}
              <code className="text-cyan-300">HF_TOKEN</code> in your root <code className="text-cyan-300">.env</code> file.
            </p>
          </div>
        </div>

        <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800 text-[11px] text-slate-400 flex items-center gap-2">
          <Key className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
          <span>
            <strong>Security Guarantee:</strong> API keys are loaded strictly on the backend via environment variables. Keys are never embedded in frontend JavaScript, browser payloads, or Git commits.
          </span>
        </div>
      </div>

      {/* Probability Calibration Advisory */}
      <div className="p-5 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200 space-y-2">
        <div className="flex items-center gap-2 font-semibold text-amber-300">
          <Scale className="w-4 h-4 text-amber-400" />
          <span>Research Calibration Disclosure</span>
        </div>
        <p className="leading-relaxed text-[11px] text-amber-200/90">{settings.calibration_notice}</p>
      </div>

      {/* Threshold Configuration Form */}
      <form onSubmit={handleSave} className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-6">
        <div className="flex items-center gap-2 text-sm font-semibold text-white">
          <Sliders className="w-4 h-4 text-indigo-400" />
          <span>Heuristic & Cutoff Parameters</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {/* Decision Cutoff */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-slate-300 font-medium">Default Decision Threshold:</span>
              <span className="font-mono text-indigo-400 font-bold">{threshold.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min={0.1}
              max={0.9}
              step={0.05}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="w-full accent-indigo-500 cursor-pointer"
            />
            <p className="text-[11px] text-slate-500">
              Probability cutoff above which an NLI sentence verdict is confirmed.
            </p>
          </div>

          {/* Top-K Passages */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-slate-300 font-medium">Retrieval Top-K Passages:</span>
              <span className="font-mono text-indigo-400 font-bold">{topK}</span>
            </div>
            <input
              type="range"
              min={1}
              max={15}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-full accent-indigo-500 cursor-pointer"
            />
            <p className="text-[11px] text-slate-500">
              Maximum chunk passages retrieved per claim from vector store.
            </p>
          </div>

          {/* Adaptive High */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-slate-300 font-medium">Adaptive Ceiling (Stage 1 Pass):</span>
              <span className="font-mono text-emerald-400 font-bold">{adaptiveHigh.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min={0.6}
              max={0.95}
              step={0.02}
              value={adaptiveHigh}
              onChange={(e) => setAdaptiveHigh(Number(e.target.value))}
              className="w-full accent-emerald-500 cursor-pointer"
            />
            <p className="text-[11px] text-slate-500">
              Similarity threshold above which high-confidence claims bypass deep NLI cross-encoder.
            </p>
          </div>

          {/* Adaptive Low */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-slate-300 font-medium">Adaptive Floor (Stage 1 Insufficient):</span>
              <span className="font-mono text-amber-400 font-bold">{adaptiveLow.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min={0.15}
              max={0.5}
              step={0.02}
              value={adaptiveLow}
              onChange={(e) => setAdaptiveLow(Number(e.target.value))}
              className="w-full accent-amber-500 cursor-pointer"
            />
            <p className="text-[11px] text-slate-500">
              Similarity threshold below which unrelated claims are short-circuited as insufficient evidence.
            </p>
          </div>

          {/* Chunk Size */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-slate-300 font-medium">Document Chunk Size:</span>
              <span className="font-mono text-slate-300 font-bold">{chunkSize} words</span>
            </div>
            <input
              type="range"
              min={50}
              max={300}
              step={25}
              value={chunkSize}
              onChange={(e) => setChunkSize(Number(e.target.value))}
              className="w-full accent-slate-400 cursor-pointer"
            />
          </div>

          {/* Chunk Overlap */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-slate-300 font-medium">Chunk Overlap:</span>
              <span className="font-mono text-slate-300 font-bold">{chunkOverlap} words</span>
            </div>
            <input
              type="range"
              min={0}
              max={60}
              step={5}
              value={chunkOverlap}
              onChange={(e) => setChunkOverlap(Number(e.target.value))}
              className="w-full accent-slate-400 cursor-pointer"
            />
          </div>
        </div>

        {/* Save Button */}
        <div className="pt-2 flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-xs shadow-md transition-all hover:scale-[1.02]"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{saving ? 'Updating...' : 'Save Configuration'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
