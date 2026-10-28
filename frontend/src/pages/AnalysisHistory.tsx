import React, { useEffect, useState } from 'react';
import {
  History,
  Trash2,
  Download,
  GitCompare,
  Eye,
  Search,
  AlertTriangle,
  Clock,
  Layers,
  ArrowRight,
  X,
} from 'lucide-react';
import { Analysis, PageId } from '../types';
import { clearAllAnalyses, deleteAnalysis, getAnalyses, getAnalysis } from '../services/api';
import { VerdictBadge } from '../components/VerdictBadge';

interface AnalysisHistoryProps {
  onSelectAnalysis: (analysisId: string) => void;
  onNavigate: (page: PageId) => void;
}

export const AnalysisHistory: React.FC<AnalysisHistoryProps> = ({
  onSelectAnalysis,
  onNavigate,
}) => {
  const [analyses, setAnalyses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Compare Modal State
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [compareModalOpen, setCompareModalOpen] = useState(false);
  const [compareData, setCompareData] = useState<{ anl1: Analysis; anl2: Analysis } | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getAnalyses(100, 0);
      setAnalyses(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load analysis history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm(`Delete analysis "${id}"?`)) return;
    try {
      await deleteAnalysis(id);
      await fetchHistory();
    } catch (err: any) {
      setError(err.message || 'Failed to delete analysis.');
    }
  };

  const handleClearAll = async () => {
    if (!confirm('Are you sure you want to delete ALL analysis history? This cannot be undone.')) return;
    try {
      await clearAllAnalyses();
      await fetchHistory();
    } catch (err: any) {
      setError(err.message || 'Failed to clear history.');
    }
  };

  const handleDownload = async (id: string) => {
    try {
      const full = await getAnalysis(id);
      const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(full, null, 2));
      const a = document.createElement('a');
      a.setAttribute('href', dataStr);
      a.setAttribute('download', `${id}_veriai_report.json`);
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      alert('Failed to download report JSON.');
    }
  };

  const toggleCompareSelection = (id: string) => {
    if (selectedForCompare.includes(id)) {
      setSelectedForCompare(selectedForCompare.filter((i) => i !== id));
    } else {
      if (selectedForCompare.length >= 2) {
        setSelectedForCompare([selectedForCompare[1], id]);
      } else {
        setSelectedForCompare([...selectedForCompare, id]);
      }
    }
  };

  const handleLaunchCompare = async () => {
    if (selectedForCompare.length !== 2) return;
    setCompareLoading(true);
    setCompareModalOpen(true);
    try {
      const [anl1, anl2] = await Promise.all([
        getAnalysis(selectedForCompare[0]),
        getAnalysis(selectedForCompare[1]),
      ]);
      setCompareData({ anl1, anl2 });
    } catch (err: any) {
      setError(err.message || 'Failed to load comparative analyses.');
      setCompareModalOpen(false);
    } finally {
      setCompareLoading(false);
    }
  };

  const filtered = analyses.filter((a) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      a.id.toLowerCase().includes(q) ||
      a.answer_summary.toLowerCase().includes(q) ||
      (a.question && a.question.toLowerCase().includes(q))
    );
  });

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Analysis History & Audit Archive
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Persisted verification runs stored in local SQLite database with claim-level audit traces.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {selectedForCompare.length === 2 && (
            <button
              onClick={handleLaunchCompare}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-md transition-all"
            >
              <GitCompare className="w-3.5 h-3.5" />
              <span>Compare Selected (2)</span>
            </button>
          )}

          {analyses.length > 0 && (
            <button
              onClick={handleClearAll}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 text-xs font-medium border border-slate-700 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear History</span>
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm">
          {error}
        </div>
      )}

      {/* Search Input */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative w-full sm:w-80">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by analysis ID, question, or text..."
            className="w-full pl-8 pr-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 outline-none focus:border-indigo-500"
          />
        </div>

        <span className="text-xs text-slate-500 hidden sm:inline">
          {selectedForCompare.length} selected for comparison (select 2)
        </span>
      </div>

      {/* History Table */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        {loading ? (
          <div className="py-12 text-center text-sm text-slate-400">Loading history archive...</div>
        ) : filtered.length === 0 ? (
          <div className="py-12 text-center space-y-3">
            <p className="text-sm text-slate-400">No historical analyses found.</p>
            <button
              onClick={() => onNavigate('analyze')}
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium"
            >
              Run First Analysis
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[11px]">
                  <th className="py-3 px-3 w-8">Cmp</th>
                  <th className="py-3 px-3">Run ID</th>
                  <th className="py-3 px-3">Answer Summary</th>
                  <th className="py-3 px-3">Method</th>
                  <th className="py-3 px-3">Claims</th>
                  <th className="py-3 px-3">Supported</th>
                  <th className="py-3 px-3">Contradicted</th>
                  <th className="py-3 px-3">Latency</th>
                  <th className="py-3 px-3">Timestamp</th>
                  <th className="py-3 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filtered.map((anl) => {
                  const isChecked = selectedForCompare.includes(anl.id);
                  return (
                    <tr key={anl.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-3">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleCompareSelection(anl.id)}
                          className="accent-indigo-500 cursor-pointer"
                        />
                      </td>
                      <td className="py-3 px-3 font-mono font-medium text-indigo-400">{anl.id}</td>
                      <td className="py-3 px-3 max-w-xs truncate text-slate-300">
                        {anl.question ? (
                          <span className="text-slate-400 font-medium mr-1.5">Q: {anl.question} —</span>
                        ) : null}
                        {anl.answer_summary}
                      </td>
                      <td className="py-3 px-3">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 uppercase font-mono text-[10px]">
                          {anl.method}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-semibold text-white">{anl.num_claims}</td>
                      <td className="py-3 px-3 font-mono text-emerald-400 font-medium">
                        {anl.supported_count}
                      </td>
                      <td className="py-3 px-3 font-mono text-rose-400 font-medium">
                        {anl.contradicted_count}
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-400">
                        {anl.latency_ms ? `${anl.latency_ms.toFixed(0)}ms` : '—'}
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-400 text-[11px]">
                        {new Date(anl.created_at).toLocaleString([], {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td className="py-3 px-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => onSelectAnalysis(anl.id)}
                            title="Inspect Report"
                            className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-400 hover:bg-slate-800 transition-colors"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDownload(anl.id)}
                            title="Download JSON Report"
                            className="p-1.5 rounded-lg text-slate-400 hover:text-emerald-400 hover:bg-slate-800 transition-colors"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDelete(anl.id)}
                            title="Delete"
                            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Compare Modal */}
      {compareModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-4xl rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl overflow-hidden max-h-[85vh] flex flex-col">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <GitCompare className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-white">Side-by-Side Analysis Comparison</h3>
              </div>
              <button
                onClick={() => setCompareModalOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6 text-xs">
              {compareLoading || !compareData ? (
                <div className="py-12 text-center text-slate-400">Loading comparison details...</div>
              ) : (
                <div className="grid grid-cols-2 gap-6 divide-x divide-slate-800">
                  {/* Analysis 1 */}
                  <div className="space-y-4 pr-3">
                    <div className="space-y-1">
                      <span className="font-mono text-indigo-400 font-semibold">{compareData.anl1.id}</span>
                      <p className="text-slate-300 font-medium">Method: {compareData.anl1.method.toUpperCase()}</p>
                      <p className="text-slate-400 text-[11px] font-mono">
                        Latency: {compareData.anl1.latency_ms.toFixed(0)}ms
                      </p>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                      <p className="font-semibold text-slate-400 text-[10px] uppercase mb-1">Answer</p>
                      <p className="text-slate-200">{compareData.anl1.full_answer}</p>
                    </div>

                    <div className="space-y-2">
                      <p className="font-semibold text-slate-300 uppercase text-[10px]">Claims & Verdicts</p>
                      {compareData.anl1.claims.map((c, i) => (
                        <div key={i} className="p-2.5 rounded bg-slate-950 border border-slate-800/80 space-y-1">
                          <div className="flex justify-between items-center">
                            <span className="font-mono text-slate-400">#{i + 1}</span>
                            <VerdictBadge verdict={c.verdict} size="sm" />
                          </div>
                          <p className="text-slate-200">"{c.claim_text}"</p>
                          <div className="text-[10px] text-slate-400 font-mono">
                            Confidence: {(c.model_score * 100).toFixed(1)}%
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Analysis 2 */}
                  <div className="space-y-4 pl-6">
                    <div className="space-y-1">
                      <span className="font-mono text-indigo-400 font-semibold">{compareData.anl2.id}</span>
                      <p className="text-slate-300 font-medium">Method: {compareData.anl2.method.toUpperCase()}</p>
                      <p className="text-slate-400 text-[11px] font-mono">
                        Latency: {compareData.anl2.latency_ms.toFixed(0)}ms
                      </p>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                      <p className="font-semibold text-slate-400 text-[10px] uppercase mb-1">Answer</p>
                      <p className="text-slate-200">{compareData.anl2.full_answer}</p>
                    </div>

                    <div className="space-y-2">
                      <p className="font-semibold text-slate-300 uppercase text-[10px]">Claims & Verdicts</p>
                      {compareData.anl2.claims.map((c, i) => (
                        <div key={i} className="p-2.5 rounded bg-slate-950 border border-slate-800/80 space-y-1">
                          <div className="flex justify-between items-center">
                            <span className="font-mono text-slate-400">#{i + 1}</span>
                            <VerdictBadge verdict={c.verdict} size="sm" />
                          </div>
                          <p className="text-slate-200">"{c.claim_text}"</p>
                          <div className="text-[10px] text-slate-400 font-mono">
                            Confidence: {(c.model_score * 100).toFixed(1)}%
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
