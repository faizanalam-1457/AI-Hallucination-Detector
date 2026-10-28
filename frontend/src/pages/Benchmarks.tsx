import React, { useEffect, useState } from 'react';
import {
  BarChart3,
  Database,
  CheckCircle2,
  AlertTriangle,
  Play,
  FileText,
  ShieldCheck,
  ExternalLink,
  Layers,
} from 'lucide-react';
import { BenchmarkDataset, PageId } from '../types';
import { getBenchmarkDatasets, getDatasetSamples } from '../services/api';

interface BenchmarksProps {
  onNavigate: (page: PageId) => void;
}

export const Benchmarks: React.FC<BenchmarksProps> = ({ onNavigate }) => {
  const [datasets, setDatasets] = useState<BenchmarkDataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDataset, setSelectedDataset] = useState<string>('smoke_test');
  const [samples, setSamples] = useState<any[]>([]);
  const [samplesLoading, setSamplesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        setLoading(true);
        const data = await getBenchmarkDatasets();
        setDatasets(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load benchmark datasets.');
      } finally {
        setLoading(false);
      }
    };
    fetchDatasets();
  }, []);

  useEffect(() => {
    if (!selectedDataset) return;
    const fetchSamples = async () => {
      try {
        setSamplesLoading(true);
        const s = await getDatasetSamples(selectedDataset, 6);
        setSamples(s);
      } catch (err: any) {
        // ignore
      } finally {
        setSamplesLoading(false);
      }
    };
    fetchSamples();
  }, [selectedDataset]);

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Hallucination Benchmarks & Dataset Registry
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Standardized evaluation datasets, formal schema mappings, and verified reference test splits.
          </p>
        </div>
        <div>
          <button
            onClick={() => onNavigate('research_lab')}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-lg shadow-indigo-600/20 transition-all hover:scale-[1.02]"
          >
            <Play className="w-3.5 h-3.5" />
            <span>Launch Evaluation Suite</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm">
          {error}
        </div>
      )}

      {/* Dataset Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {datasets.map((ds) => {
          const isSelected = selectedDataset === ds.id;
          return (
            <div
              key={ds.id}
              onClick={() => setSelectedDataset(ds.id)}
              className={`p-5 rounded-2xl border transition-all cursor-pointer space-y-3 ${
                isSelected
                  ? 'bg-slate-900 border-indigo-500 ring-2 ring-indigo-500/20'
                  : 'bg-slate-900/50 border-slate-800 hover:border-slate-700/80'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs uppercase text-indigo-400 font-semibold">
                  {ds.id}
                </span>
                {ds.offline_available && (
                  <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                    Offline Available
                  </span>
                )}
              </div>

              <h3 className="text-base font-bold text-white">{ds.name}</h3>
              <p className="text-xs text-slate-400 leading-relaxed">{ds.description}</p>

              <div className="pt-2 border-t border-slate-800 text-[11px] space-y-1 text-slate-400 font-mono">
                <div>Version: <span className="text-slate-300">{ds.version}</span></div>
                <div>License: <span className="text-slate-300">{ds.license}</span></div>
                <div>Size: <span className="text-indigo-400 font-semibold">{ds.size.toLocaleString()} examples</span></div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Label Taxonomy & Mapping Layer Advisory */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-white">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Label Mapping & Ground Truth Harmonization</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-slate-300 leading-relaxed">
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1.5">
            <span className="font-semibold text-indigo-300">Smoke Test Mapping</span>
            <p className="text-slate-400">
              Binary label: <code className="text-indigo-400">is_hallucinated: bool</code>. 8 verbatim true facts, 8 entity/number mutations.
            </p>
          </div>
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1.5">
            <span className="font-semibold text-indigo-300">HaluEval QA Mapping</span>
            <p className="text-slate-400">
              Row pairs: <code className="text-emerald-400">right_answer</code> &rarr; False,{' '}
              <code className="text-rose-400">hallucinated_answer</code> &rarr; True. Perfectly balanced.
            </p>
          </div>
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1.5">
            <span className="font-semibold text-indigo-300">RAGTruth Mapping</span>
            <p className="text-slate-400">
              Span-level labels: if response contains any annotated hallucination span &rarr; True, else False.
            </p>
          </div>
        </div>
      </div>

      {/* Sample Examples Preview */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">
            Sample Rows Preview — <span className="text-indigo-400 font-mono">{selectedDataset}</span>
          </h3>
          <span className="text-xs text-slate-400">Inspecting input structure & ground truth</span>
        </div>

        {samplesLoading ? (
          <div className="py-8 text-center text-xs text-slate-400">Loading dataset sample rows...</div>
        ) : samples.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-400">No samples available.</div>
        ) : (
          <div className="space-y-3">
            {samples.map((s, i) => (
              <div
                key={i}
                className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-300">Q: {s.question}</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                      s.is_hallucinated
                        ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                        : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                    }`}
                  >
                    {s.ground_truth_label}
                  </span>
                </div>
                {s.context_preview && (
                  <p className="text-slate-400 text-[11px] font-serif bg-slate-900/80 p-2 rounded border border-slate-800">
                    <strong className="font-sans text-slate-500 uppercase text-[9px] block">
                      Context Passage:
                    </strong>
                    "{s.context_preview}..."
                  </p>
                )}
                <p className="text-slate-200">
                  <strong className="text-slate-400">Candidate Answer:</strong> "{s.answer}"
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
