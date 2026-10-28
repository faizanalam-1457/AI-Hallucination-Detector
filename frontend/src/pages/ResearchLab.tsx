import React, { useEffect, useState } from 'react';
import {
  FlaskConical,
  Play,
  Download,
  BarChart2,
  Sliders,
  CheckCircle2,
  XCircle,
  Clock,
  Layers,
  HelpCircle,
  FileSpreadsheet,
  FileCode,
  Zap,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';
import { Experiment } from '../types';
import { getExperiments, runExperiment, RunExperimentParams } from '../services/api';

export const ResearchLab: React.FC = () => {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form Config
  const [expName, setExpName] = useState('');
  const [method, setMethod] = useState<'adaptive' | 'nli' | 'embedding'>('adaptive');
  const [datasetName, setDatasetName] = useState('smoke_test');
  const [sampleLimit, setSampleLimit] = useState(16);
  const [decisionThreshold, setDecisionThreshold] = useState(0.5);
  const [extractionMethod, setExtractionMethod] = useState<'sentence' | 'decomposed'>('sentence');

  const [activeExperiment, setActiveExperiment] = useState<Experiment | null>(null);

  const loadPastExperiments = async () => {
    try {
      setLoading(true);
      setError(null);
      const exps = await getExperiments();
      setExperiments(exps);
      if (exps.length > 0 && !activeExperiment) {
        setActiveExperiment(exps[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load past experiments.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPastExperiments();
  }, []);

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setRunning(true);
    setError(null);

    try {
      const params: RunExperimentParams = {
        name: expName.trim() || undefined,
        method,
        dataset_name: datasetName,
        sample_limit: sampleLimit,
        decision_threshold: decisionThreshold,
        extraction_method: extractionMethod,
      };

      const result = await runExperiment(params);
      setActiveExperiment(result);
      await loadPastExperiments();
    } catch (err: any) {
      setError(err.message || 'Experiment run failed.');
    } finally {
      setRunning(false);
    }
  };

  const handleExport = (expId: string, format: 'json' | 'csv') => {
    window.open(`/api/experiments/${expId}/export?format=${format}`, '_blank');
  };

  // Prepare comparison data across recent experiments
  const comparisonData = experiments.slice(0, 5).map((exp) => ({
    name: `${exp.method.toUpperCase()} (${exp.dataset_name})`,
    MacroF1: parseFloat((exp.macro_f1 * 100).toFixed(1)),
    Recall: parseFloat((exp.recall * 100).toFixed(1)),
    Precision: parseFloat((exp.precision * 100).toFixed(1)),
    LatencyMs: parseFloat(exp.latency_per_claim_ms.toFixed(1)),
  }));

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Research Evaluation Lab
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Controlled empirical comparison of Embedding Similarity vs. NLI Cross-Encoder vs. Adaptive Cascade.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-xs text-indigo-400 font-medium">
            Empirical Benchmark Suite
          </span>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm">
          {error}
        </div>
      )}

      {/* Experiment Run Configuration */}
      <form onSubmit={handleRun} className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <Sliders className="w-4 h-4 text-indigo-400" />
            <span>Configure New Experiment</span>
          </div>
          <span className="text-xs text-slate-500">Parameters are versioned with results</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Method */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-300">Detection Method</label>
            <select
              value={method}
              onChange={(e: any) => setMethod(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 text-xs outline-none focus:border-indigo-500"
            >
              <option value="adaptive">Adaptive Cascade (Proposed)</option>
              <option value="nli">NLI Cross-Encoder (DeBERTa-v3)</option>
              <option value="embedding">Embedding Similarity (Baseline)</option>
            </select>
          </div>

          {/* Dataset */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-300">Benchmark Dataset</label>
            <select
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 text-xs outline-none focus:border-indigo-500"
            >
              <option value="smoke_test">Smoke Test (16 balanced offline pairs)</option>
              <option value="ragtruth">RAGTruth (Sampled split)</option>
              <option value="halueval">HaluEval QA (Hugging Face mirror)</option>
            </select>
          </div>

          {/* Sample Size */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs text-slate-300">
              <span>Sample Limit:</span>
              <span className="font-mono text-indigo-400 font-semibold">{sampleLimit}</span>
            </div>
            <input
              type="range"
              min={4}
              max={100}
              step={2}
              value={sampleLimit}
              onChange={(e) => setSampleLimit(Number(e.target.value))}
              className="w-full accent-indigo-500 cursor-pointer"
            />
          </div>

          {/* Threshold */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs text-slate-300">
              <span>Decision Threshold:</span>
              <span className="font-mono text-indigo-400 font-semibold">{decisionThreshold.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min={0.1}
              max={0.9}
              step={0.05}
              value={decisionThreshold}
              onChange={(e) => setDecisionThreshold(Number(e.target.value))}
              className="w-full accent-indigo-500 cursor-pointer"
            />
          </div>

          {/* Run Button */}
          <div className="flex items-end">
            <button
              type="submit"
              disabled={running}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-xs shadow-lg shadow-indigo-600/30 transition-all hover:scale-[1.02]"
            >
              <Play className="w-3.5 h-3.5" />
              <span>{running ? 'Running Experiment...' : 'Execute Run'}</span>
            </button>
          </div>
        </div>
      </form>

      {/* Active Experiment Results Dashboard */}
      {activeExperiment && (
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-indigo-400 font-semibold">
                  {activeExperiment.id}
                </span>
                <span className="text-slate-600">•</span>
                <span className="text-xs text-slate-400">
                  {new Date(activeExperiment.created_at).toLocaleString()}
                </span>
              </div>
              <h3 className="text-lg font-bold text-white mt-1">{activeExperiment.name}</h3>
            </div>

            {/* Export Buttons */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleExport(activeExperiment.id, 'csv')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
                <span>Export CSV</span>
              </button>
              <button
                onClick={() => handleExport(activeExperiment.id, 'json')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
              >
                <FileCode className="w-3.5 h-3.5 text-indigo-400" />
                <span>Export JSON</span>
              </button>
            </div>
          </div>

          {/* Score Cards Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <span className="text-[11px] text-slate-400 font-medium">Macro F1</span>
              <div className="text-2xl font-bold font-mono text-indigo-400 mt-1">
                {(activeExperiment.macro_f1 * 100).toFixed(1)}%
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <span className="text-[11px] text-slate-400 font-medium">Accuracy</span>
              <div className="text-2xl font-bold font-mono text-white mt-1">
                {(activeExperiment.accuracy * 100).toFixed(1)}%
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <span className="text-[11px] text-slate-400 font-medium">Precision (Halluc.)</span>
              <div className="text-2xl font-bold font-mono text-cyan-400 mt-1">
                {(activeExperiment.precision * 100).toFixed(1)}%
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <span className="text-[11px] text-slate-400 font-medium">Recall (Halluc.)</span>
              <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
                {(activeExperiment.recall * 100).toFixed(1)}%
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <span className="text-[11px] text-slate-400 font-medium">Latency / Claim</span>
              <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
                {activeExperiment.latency_per_claim_ms.toFixed(0)} ms
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <span className="text-[11px] text-slate-400 font-medium">Sample Size</span>
              <div className="text-2xl font-bold font-mono text-slate-200 mt-1">
                {activeExperiment.sample_size} N
              </div>
            </div>
          </div>

          {/* Confusion Matrix & Detailed Metrics */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-2">
            {/* Confusion Matrix 2x2 Heatmap */}
            <div className="p-5 rounded-xl bg-slate-950/50 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase text-slate-300">
                  Confusion Matrix (Binary Classification)
                </span>
                <span className="text-[11px] text-slate-500 font-mono">Positive = Hallucinated</span>
              </div>

              <div className="grid grid-cols-2 gap-3 text-center">
                {/* True Positives */}
                <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                  <div className="text-xs text-emerald-300 font-medium">True Positives (TP)</div>
                  <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
                    {activeExperiment.confusion_matrix.tp}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">Caught Hallucinations</div>
                </div>

                {/* False Positives */}
                <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20">
                  <div className="text-xs text-rose-300 font-medium">False Positives (FP)</div>
                  <div className="text-2xl font-bold font-mono text-rose-400 mt-1">
                    {activeExperiment.confusion_matrix.fp}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">False Alarms (Grounded flagged)</div>
                </div>

                {/* False Negatives */}
                <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/20">
                  <div className="text-xs text-amber-300 font-medium">False Negatives (FN)</div>
                  <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
                    {activeExperiment.confusion_matrix.fn}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">Missed Hallucinations</div>
                </div>

                {/* True Negatives */}
                <div className="p-4 rounded-lg bg-slate-800/80 border border-slate-700/80">
                  <div className="text-xs text-slate-300 font-medium">True Negatives (TN)</div>
                  <div className="text-2xl font-bold font-mono text-slate-200 mt-1">
                    {activeExperiment.confusion_matrix.tn}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">Correctly Grounded Answers</div>
                </div>
              </div>
            </div>

            {/* Per-class Metrics & Calibration */}
            <div className="p-5 rounded-xl bg-slate-950/50 border border-slate-800 space-y-3">
              <span className="text-xs font-semibold uppercase text-slate-300">
                Per-Class & Calibration Diagnostic
              </span>

              <div className="space-y-2 text-xs">
                <div className="flex justify-between p-2 rounded bg-slate-900 border border-slate-800">
                  <span className="text-slate-400">Supported Class F1:</span>
                  <span className="font-mono text-emerald-400 font-semibold">
                    {(activeExperiment.supported_f1 * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between p-2 rounded bg-slate-900 border border-slate-800">
                  <span className="text-slate-400">Hallucinated Class F1:</span>
                  <span className="font-mono text-rose-400 font-semibold">
                    {(activeExperiment.hallucinated_f1 * 100).toFixed(1)}%
                  </span>
                </div>
                {activeExperiment.metrics.ece !== undefined && (
                  <div className="flex justify-between p-2 rounded bg-slate-900 border border-slate-800">
                    <span className="text-slate-400">Expected Calibration Error (ECE):</span>
                    <span className="font-mono text-indigo-400 font-semibold">
                      {activeExperiment.metrics.ece.toFixed(4)}
                    </span>
                  </div>
                )}
                {activeExperiment.metrics.brier_score !== undefined && (
                  <div className="flex justify-between p-2 rounded bg-slate-900 border border-slate-800">
                    <span className="text-slate-400">Brier Score Loss:</span>
                    <span className="font-mono text-slate-300 font-semibold">
                      {activeExperiment.metrics.brier_score.toFixed(4)}
                    </span>
                  </div>
                )}
                <div className="flex justify-between p-2 rounded bg-slate-900 border border-slate-800">
                  <span className="text-slate-400">Evaluated Model:</span>
                  <span className="font-mono text-slate-300">{activeExperiment.model_name}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Cross-Method Comparison Chart */}
      {comparisonData.length > 0 && (
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white">Method Comparison Benchmark</h3>
              <p className="text-xs text-slate-400">Macro F1, Precision, and Recall across saved runs</p>
            </div>
            <BarChart2 className="w-4 h-4 text-indigo-400" />
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparisonData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} domain={[0, 100]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '12px',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                <Bar dataKey="MacroF1" fill="#6366f1" name="Macro F1 (%)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Recall" fill="#10b981" name="Recall (%)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Precision" fill="#38bdf8" name="Precision (%)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Historical Runs Table */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <h3 className="text-sm font-semibold text-white">Historical Experiment Records</h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[11px]">
                <th className="py-3 px-4">Run ID</th>
                <th className="py-3 px-4">Method</th>
                <th className="py-3 px-4">Dataset</th>
                <th className="py-3 px-4">Macro F1</th>
                <th className="py-3 px-4">Recall</th>
                <th className="py-3 px-4">Precision</th>
                <th className="py-3 px-4">Latency/Claim</th>
                <th className="py-3 px-4 text-right">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {experiments.map((exp) => (
                <tr key={exp.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3 px-4 font-mono font-medium text-indigo-400">{exp.id}</td>
                  <td className="py-3 px-4 uppercase font-mono font-semibold text-slate-300">
                    {exp.method}
                  </td>
                  <td className="py-3 px-4 text-slate-300">{exp.dataset_name}</td>
                  <td className="py-3 px-4 font-mono text-emerald-400 font-semibold">
                    {(exp.macro_f1 * 100).toFixed(1)}%
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-200">
                    {(exp.recall * 100).toFixed(1)}%
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-200">
                    {(exp.precision * 100).toFixed(1)}%
                  </td>
                  <td className="py-3 px-4 font-mono text-amber-400">
                    {exp.latency_per_claim_ms.toFixed(0)} ms
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => setActiveExperiment(exp)}
                      className="px-2.5 py-1 rounded-lg bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 border border-indigo-500/20 text-[11px] font-medium transition-colors"
                    >
                      View Run
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
