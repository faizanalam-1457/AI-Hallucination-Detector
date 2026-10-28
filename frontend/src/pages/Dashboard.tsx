import React, { useEffect, useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Sparkles,
  ArrowRight,
  TrendingUp,
  FileText,
  Clock,
  Layers,
} from 'lucide-react';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, AreaChart, Area, XAxis, YAxis } from 'recharts';
import { DashboardStats, PageId } from '../types';
import { getDashboardStats } from '../services/api';
import { VerdictBadge } from '../components/VerdictBadge';

interface DashboardProps {
  onNavigate: (page: PageId) => void;
  onSelectAnalysis: (analysisId: string) => void;
}

const VERDICT_COLORS = {
  Supported: '#10b981',
  Contradicted: '#f43f5e',
  Insufficient: '#f59e0b',
  Conflicting: '#a855f7',
};

export const Dashboard: React.FC<DashboardProps> = ({ onNavigate, onSelectAnalysis }) => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getDashboardStats();
      setStats(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard statistics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-slate-400">Loading research dashboard metrics...</p>
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="p-8">
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm">
          {error || 'Unable to retrieve statistics.'}
        </div>
      </div>
    );
  }

  const isEmpty = stats.total_analyses === 0;

  const pieData = [
    { name: 'Supported', value: stats.supported_claims, color: VERDICT_COLORS.Supported },
    { name: 'Contradicted', value: stats.contradicted_claims, color: VERDICT_COLORS.Contradicted },
    { name: 'Insufficient', value: stats.insufficient_claims, color: VERDICT_COLORS.Insufficient },
    { name: 'Conflicting', value: stats.conflicting_claims, color: VERDICT_COLORS.Conflicting },
  ].filter((d) => d.value > 0);

  const supportRate =
    stats.total_claims > 0 ? ((stats.supported_claims / stats.total_claims) * 100).toFixed(1) : '0.0';
  const contradictionRate =
    stats.total_claims > 0 ? ((stats.contradicted_claims / stats.total_claims) * 100).toFixed(1) : '0.0';

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Verification Intelligence Dashboard
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Empirical telemetry on factual grounding, claim decomposition, and NLI verification accuracy.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigate('analyze')}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm shadow-lg shadow-indigo-600/20 transition-all hover:scale-[1.02]"
          >
            <Sparkles className="w-4 h-4" />
            <span>Verify New Answer</span>
          </button>
        </div>
      </div>

      {isEmpty ? (
        /* Empty State */
        <div className="p-12 text-center rounded-2xl border border-slate-800 bg-slate-900/40 space-y-6">
          <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <div className="max-w-md mx-auto space-y-2">
            <h3 className="text-lg font-semibold text-white">No Analyses Recorded Yet</h3>
            <p className="text-sm text-slate-400">
              Start by verifying an AI-generated answer or run the research benchmark suite to generate baseline statistics.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
            <button
              onClick={() => onNavigate('analyze')}
              className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-all"
            >
              Analyze Your First Answer
            </button>
            <button
              onClick={() => onNavigate('research_lab')}
              className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium border border-slate-700 transition-all"
            >
              Run Benchmark Experiment
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Key Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-slate-700/80 transition-all">
              <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
                <span>Total Analyses</span>
                <Clock className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-white tracking-tight">{stats.total_analyses}</span>
                <span className="text-xs text-slate-400">runs</span>
              </div>
              <p className="text-xs text-slate-400 mt-2">Stored locally in SQLite</p>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-slate-700/80 transition-all">
              <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
                <span>Atomic Claims</span>
                <Layers className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-white tracking-tight">{stats.total_claims}</span>
                <span className="text-xs text-slate-400">claims</span>
              </div>
              <p className="text-xs text-slate-400 mt-2">Decomposed and verified</p>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900/60 border border-emerald-500/20 hover:border-emerald-500/40 transition-all">
              <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
                <span>Supported Claims</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-emerald-400 tracking-tight">{stats.supported_claims}</span>
                <span className="text-xs text-emerald-500/80 font-medium">({supportRate}%)</span>
              </div>
              <p className="text-xs text-slate-400 mt-2">Grounded in verified context</p>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900/60 border border-rose-500/20 hover:border-rose-500/40 transition-all">
              <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
                <span>Contradicted Claims</span>
                <XCircle className="w-4 h-4 text-rose-400" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-rose-400 tracking-tight">{stats.contradicted_claims}</span>
                <span className="text-xs text-rose-500/80 font-medium">({contradictionRate}%)</span>
              </div>
              <p className="text-xs text-slate-400 mt-2">Factual hallucinations flagged</p>
            </div>
          </div>

          {/* Analytics Visualizations */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Verdict Distribution Donut */}
            <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white">Verdict Distribution</h3>
                <span className="text-xs text-slate-400">{stats.total_claims} Total Claims</span>
              </div>

              {pieData.length > 0 ? (
                <div className="h-56 relative flex items-center justify-center">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        innerRadius={55}
                        outerRadius={80}
                        paddingAngle={4}
                        dataKey="value"
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#0f172a',
                          borderColor: '#334155',
                          borderRadius: '8px',
                          color: '#fff',
                          fontSize: '12px',
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-56 flex items-center justify-center text-xs text-slate-400">
                  No claims data available.
                </div>
              )}

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800 text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                  <span className="text-slate-400">Supported: {stats.supported_claims}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                  <span className="text-slate-400">Contradicted: {stats.contradicted_claims}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                  <span className="text-slate-400">Insufficient: {stats.insufficient_claims}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
                  <span className="text-slate-400">Conflicting: {stats.conflicting_claims}</span>
                </div>
              </div>
            </div>

            {/* Verification Activity Over Time */}
            <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 lg:col-span-2 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">Verification Activity Over Time</h3>
                  <p className="text-xs text-slate-400">Daily verification execution volume</p>
                </div>
                <TrendingUp className="w-4 h-4 text-indigo-400" />
              </div>

              {stats.activity_over_time.length > 0 ? (
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={stats.activity_over_time}>
                      <defs>
                        <linearGradient id="colorAnalyses" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickLine={false} />
                      <YAxis stroke="#64748b" fontSize={11} tickLine={false} allowDecimals={false} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#0f172a',
                          borderColor: '#334155',
                          borderRadius: '8px',
                          color: '#fff',
                          fontSize: '12px',
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="analyses"
                        stroke="#6366f1"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#colorAnalyses)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-56 flex items-center justify-center text-xs text-slate-400">
                  Execute analyses to populate the activity timeline.
                </div>
              )}

              {/* Method distribution breakdown */}
              <div className="flex flex-wrap items-center gap-4 pt-2 border-t border-slate-800 text-xs text-slate-400">
                <span className="font-medium text-slate-300">Methods used:</span>
                {Object.entries(stats.method_distribution).map(([method, count]) => (
                  <span key={method} className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                    {method.toUpperCase()}: <span className="text-indigo-400 font-semibold">{count}</span>
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Recent Analyses Table */}
          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-white">Recent Analyses</h3>
                <p className="text-xs text-slate-400">Latest claim-level verification audits</p>
              </div>
              <button
                onClick={() => onNavigate('history')}
                className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1"
              >
                <span>View Full History</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[11px]">
                    <th className="py-3 px-4">Analysis ID</th>
                    <th className="py-3 px-4">Answer Summary</th>
                    <th className="py-3 px-4">Method</th>
                    <th className="py-3 px-4">Claims</th>
                    <th className="py-3 px-4">Verdicts Breakdown</th>
                    <th className="py-3 px-4">Timestamp</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {stats.recent_analyses.map((anl) => (
                    <tr key={anl.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-indigo-400">{anl.id}</td>
                      <td className="py-3 px-4 max-w-xs truncate text-slate-300 font-normal">
                        {anl.question ? (
                          <span className="text-slate-400 font-medium mr-1.5">Q: {anl.question} —</span>
                        ) : null}
                        {anl.answer_summary}
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 uppercase font-mono text-[10px]">
                          {anl.method}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-semibold text-white">{anl.num_claims}</td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span className="text-emerald-400 font-medium">{anl.supported_count} sup</span>
                          <span className="text-slate-600">/</span>
                          <span className="text-rose-400 font-medium">{anl.contradicted_count} con</span>
                          <span className="text-slate-600">/</span>
                          <span className="text-amber-400 font-medium">{anl.insufficient_count} ins</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                        {new Date(anl.created_at).toLocaleString([], {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => onSelectAnalysis(anl.id)}
                          className="px-2.5 py-1 rounded-lg bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 border border-indigo-500/20 transition-colors font-medium text-[11px]"
                        >
                          View Claims
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
