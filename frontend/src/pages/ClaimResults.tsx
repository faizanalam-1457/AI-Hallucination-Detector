import React, { useState } from 'react';
import {
  ShieldAlert,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  FileText,
  Clock,
  Layers,
  Sparkles,
  ExternalLink,
  BookOpen,
} from 'lucide-react';
import { Analysis, ClaimResult, PageId } from '../types';
import { VerdictBadge } from '../components/VerdictBadge';

interface ClaimResultsProps {
  analysis: Analysis | null;
  onNavigate: (page: PageId) => void;
  onSelectEvidencePassage?: (passage: any) => void;
}

export const ClaimResults: React.FC<ClaimResultsProps> = ({
  analysis,
  onNavigate,
  onSelectEvidencePassage,
}) => {
  const [filterVerdict, setFilterVerdict] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'index' | 'confidence' | 'similarity'>('index');
  const [expandedClaims, setExpandedClaims] = useState<Record<string, boolean>>({});

  if (!analysis) {
    return (
      <div className="p-12 text-center max-w-xl mx-auto space-y-4">
        <div className="w-12 h-12 rounded-xl bg-slate-800 text-slate-400 flex items-center justify-center mx-auto">
          <Layers className="w-6 h-6" />
        </div>
        <h3 className="text-lg font-semibold text-white">No Analysis Selected</h3>
        <p className="text-sm text-slate-400">
          Run an analysis on an AI answer or select a past report from history to inspect claim-level verdicts.
        </p>
        <button
          onClick={() => onNavigate('analyze')}
          className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
        >
          Go to Analyze Answer
        </button>
      </div>
    );
  }

  const toggleExpand = (id: string) => {
    setExpandedClaims((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const filteredClaims = analysis.claims
    .filter((c) => {
      if (filterVerdict === 'SUPPORTED') return c.verdict === 'SUPPORTED';
      if (filterVerdict === 'CONTRADICTED') return c.verdict === 'CONTRADICTED';
      if (filterVerdict === 'INSUFFICIENT') return c.verdict === 'INSUFFICIENT_EVIDENCE';
      if (filterVerdict === 'REVIEW_NEEDED') return c.requires_human_review;
      return true;
    })
    .filter((c) => {
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      return (
        c.claim_text.toLowerCase().includes(q) ||
        c.plain_english_explanation.toLowerCase().includes(q)
      );
    })
    .sort((a, b) => {
      if (sortBy === 'confidence') return b.model_score - a.model_score;
      if (sortBy === 'similarity') return b.retrieval_similarity - a.retrieval_similarity;
      return a.claim_index - b.claim_index;
    });

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      {/* Disclaimer Alert */}
      <div className="p-3.5 rounded-xl bg-indigo-950/40 border border-indigo-500/20 text-xs text-indigo-300 flex items-center gap-2.5">
        <ShieldAlert className="w-4 h-4 shrink-0 text-indigo-400" />
        <span>
          <strong className="font-semibold text-indigo-200">Scientific Epistemic Notice:</strong> Verdicts and
          scores are machine-learned model inferences (cross-encoder entailment probabilities), not guaranteed
          absolute truth. High confidence does not substitute for domain expert review.
        </span>
      </div>

      {/* Analysis Overview Header */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs text-indigo-400 font-semibold">{analysis.id}</span>
              <span className="text-slate-600">•</span>
              <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 uppercase font-mono text-[10px]">
                {analysis.method}
              </span>
              {analysis.metadata?.extraction_method && (
                <>
                  <span className="text-slate-600">•</span>
                  <span className="px-2 py-0.5 rounded bg-indigo-950/70 border border-indigo-500/30 text-indigo-300 font-mono text-[10px] flex items-center gap-1">
                    <Sparkles className="w-3 h-3 text-indigo-400" />
                    {analysis.metadata.extraction_method.toUpperCase()} EXTRACTION
                  </span>
                </>
              )}
              <span className="text-slate-600">•</span>
              <span className="text-xs text-slate-400">
                {new Date(analysis.created_at).toLocaleString()}
              </span>
            </div>
            {analysis.question && (
              <h3 className="text-base font-medium text-slate-200 mt-1">
                <span className="text-slate-400 font-normal">Prompt:</span> {analysis.question}
              </h3>
            )}
          </div>
          <div className="flex items-center gap-3 text-xs">
            <div className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700/60 flex items-center gap-2">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <span className="font-mono text-slate-200 font-medium">
                {analysis.latency_ms.toFixed(0)} ms
              </span>
            </div>
            <button
              onClick={() => onNavigate('evidence_explorer')}
              className="px-3 py-1.5 rounded-lg bg-indigo-600/15 hover:bg-indigo-600/25 text-indigo-300 border border-indigo-500/30 transition-colors flex items-center gap-1.5"
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>Evidence Inspector</span>
            </button>
          </div>
        </div>

        {/* Full Answer Collapsible Box */}
        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs text-slate-300 font-normal leading-relaxed">
          <p className="font-semibold text-slate-400 uppercase text-[10px] tracking-wider mb-1">
            Verified Answer Text
          </p>
          {analysis.full_answer}
        </div>

        {/* Summary Metric Pills */}
        <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-slate-800 text-xs">
          <span className="text-slate-400 font-medium">Results Summary:</span>
          <span className="inline-flex items-center gap-1.5 text-emerald-400 font-medium">
            <CheckCircle2 className="w-3.5 h-3.5" />
            {analysis.supported_count} Supported
          </span>
          <span className="text-slate-700">•</span>
          <span className="inline-flex items-center gap-1.5 text-rose-400 font-medium">
            <XCircle className="w-3.5 h-3.5" />
            {analysis.contradicted_count} Contradicted
          </span>
          <span className="text-slate-700">•</span>
          <span className="inline-flex items-center gap-1.5 text-amber-400 font-medium">
            <HelpCircle className="w-3.5 h-3.5" />
            {analysis.insufficient_count} Insufficient
          </span>
          {analysis.conflicting_count > 0 && (
            <>
              <span className="text-slate-700">•</span>
              <span className="inline-flex items-center gap-1.5 text-purple-400 font-medium">
                <AlertTriangle className="w-3.5 h-3.5" />
                {analysis.conflicting_count} Conflicting
              </span>
            </>
          )}
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Verdict Filter Buttons */}
        <div className="flex flex-wrap items-center gap-1.5 p-1 rounded-xl bg-slate-900/80 border border-slate-800 text-xs">
          {[
            { id: 'ALL', label: `All (${analysis.claims.length})` },
            { id: 'SUPPORTED', label: `Supported (${analysis.supported_count})` },
            { id: 'CONTRADICTED', label: `Contradicted (${analysis.contradicted_count})` },
            { id: 'INSUFFICIENT', label: `Insufficient (${analysis.insufficient_count})` },
            { id: 'REVIEW_NEEDED', label: 'Human Review' },
          ].map((btn) => (
            <button
              key={btn.id}
              onClick={() => setFilterVerdict(btn.id)}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                filterVerdict === btn.id
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {btn.label}
            </button>
          ))}
        </div>

        {/* Search & Sort Controls */}
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter claim text..."
              className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 outline-none focus:border-indigo-500"
            />
          </div>

          <select
            value={sortBy}
            onChange={(e: any) => setSortBy(e.target.value)}
            className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 outline-none"
          >
            <option value="index">Index</option>
            <option value="confidence">Confidence</option>
            <option value="similarity">Similarity</option>
          </select>
        </div>
      </div>

      {/* Claim Cards List */}
      <div className="space-y-4">
        {filteredClaims.length === 0 ? (
          <div className="p-8 text-center rounded-xl bg-slate-900/30 border border-slate-800 text-sm text-slate-400">
            No claims matching the active filter or search query.
          </div>
        ) : (
          filteredClaims.map((claim, idx) => {
            const isExpanded = !!expandedClaims[claim.id || `c-${idx}`];
            const claimKey = claim.id || `c-${idx}`;

            return (
              <div
                key={claimKey}
                className="rounded-2xl bg-slate-900/60 border border-slate-800 overflow-hidden hover:border-slate-700/80 transition-all shadow-sm"
              >
                {/* Claim Card Header */}
                <div className="p-5 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                        Claim #{claim.claim_index + 1}
                      </span>
                      <VerdictBadge verdict={claim.verdict} size="md" />
                      {claim.explanation_provider === 'gemini' && (
                        <span className="text-[10px] font-semibold text-indigo-300 bg-indigo-500/15 border border-indigo-500/30 px-2 py-0.5 rounded-full flex items-center gap-1">
                          <Sparkles className="w-3 h-3 text-indigo-400" />
                          Gemini Grounded
                        </span>
                      )}
                      {claim.requires_human_review && (
                        <span className="text-[11px] font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" />
                          Review Advised
                        </span>
                      )}
                    </div>

                    <p className="text-sm font-medium text-white leading-relaxed">
                      "{claim.claim_text}"
                    </p>

                    <p className="text-xs text-slate-400 leading-normal">
                      <strong className="text-slate-300 font-semibold">Audit Verdict:</strong>{' '}
                      {claim.plain_english_explanation}
                    </p>
                  </div>

                  {/* Scores & Toggle Button */}
                  <div className="flex sm:flex-col items-end gap-2 shrink-0">
                    <div className="text-right">
                      <div className="text-xs text-slate-400">Model Entailment:</div>
                      <div className="text-base font-bold font-mono text-indigo-400">
                        {(claim.model_score * 100).toFixed(1)}%
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono">
                        Sim: {(claim.retrieval_similarity * 100).toFixed(0)}%
                      </div>
                    </div>

                    <button
                      onClick={() => toggleExpand(claimKey)}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700/80 text-xs text-slate-300 font-medium flex items-center gap-1 transition-colors"
                    >
                      <span>{isExpanded ? 'Hide Evidence' : 'Inspect Evidence'}</span>
                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                {/* Expanded Evidence & Passages Tray */}
                {isExpanded && (
                  <div className="px-5 pb-5 pt-2 border-t border-slate-800/80 bg-slate-950/40 space-y-4">
                    <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center justify-between">
                      <span>Retrieved Evidence Passages ({claim.supporting_evidence?.length || 0})</span>
                      <span className="text-[11px] text-slate-500 normal-case">
                        Model: {claim.model_identifier}
                      </span>
                    </div>

                    {claim.supporting_evidence && claim.supporting_evidence.length > 0 ? (
                      <div className="space-y-3">
                        {claim.supporting_evidence.map((p, pIdx) => (
                          <div
                            key={pIdx}
                            className={`p-4 rounded-xl border text-xs space-y-2 transition-all ${
                              p.is_winning
                                ? 'bg-indigo-950/20 border-indigo-500/30 ring-1 ring-indigo-500/20'
                                : 'bg-slate-900/60 border-slate-800/80'
                            }`}
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <FileText className="w-3.5 h-3.5 text-slate-400" />
                                <span className="font-semibold text-slate-200">
                                  {p.doc_title || p.doc_id}
                                </span>
                                {p.page_number && (
                                  <span className="px-1.5 py-0.5 rounded bg-slate-800 text-indigo-400 font-mono text-[10px]">
                                    Page {p.page_number}
                                  </span>
                                )}
                                {p.is_winning && (
                                  <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded">
                                    Primary Winning Hit
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-3 font-mono text-[11px]">
                                <span className="text-emerald-400">
                                  Entail: {(p.entailment_prob * 100).toFixed(1)}%
                                </span>
                                <span className="text-rose-400">
                                  Contra: {(p.contradiction_prob * 100).toFixed(1)}%
                                </span>
                                <span className="text-slate-400">
                                  Neutral: {(p.neutral_prob * 100).toFixed(1)}%
                                </span>
                              </div>
                            </div>

                            <p className="text-slate-300 leading-relaxed font-normal bg-slate-900/80 p-2.5 rounded-lg border border-slate-800/60">
                              "{p.text}"
                            </p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500 italic">
                        No specific passage met threshold for direct quotation.
                      </p>
                    )}

                    {/* Method Limitations Notice */}
                    {claim.limitations && claim.limitations.length > 0 && (
                      <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800 text-[11px] text-slate-400">
                        <strong className="text-slate-300">Method Limitation:</strong>{' '}
                        {claim.limitations.join(' ')}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
