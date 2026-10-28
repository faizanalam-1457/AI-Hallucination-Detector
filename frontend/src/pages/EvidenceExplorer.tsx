import React, { useState } from 'react';
import {
  Compass,
  FileText,
  Search,
  Filter,
  ExternalLink,
  BookOpen,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ArrowRight,
} from 'lucide-react';
import { Analysis, PageId } from '../types';
import { VerdictBadge } from '../components/VerdictBadge';

interface EvidenceExplorerProps {
  analysis: Analysis | null;
  onNavigate: (page: PageId) => void;
}

export const EvidenceExplorer: React.FC<EvidenceExplorerProps> = ({ analysis, onNavigate }) => {
  const [search, setSearch] = useState('');
  const [selectedDoc, setSelectedDoc] = useState<string>('ALL');

  if (!analysis) {
    return (
      <div className="p-12 text-center max-w-xl mx-auto space-y-4">
        <div className="w-12 h-12 rounded-xl bg-slate-800 text-slate-400 flex items-center justify-center mx-auto">
          <Compass className="w-6 h-6" />
        </div>
        <h3 className="text-lg font-semibold text-white">No Evidence Context Loaded</h3>
        <p className="text-sm text-slate-400">
          Run an analysis on an AI answer or inspect an existing report to explore the retrieved evidence passages and citations.
        </p>
        <button
          onClick={() => onNavigate('analyze')}
          className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
        >
          Verify an Answer
        </button>
      </div>
    );
  }

  // Extract all evidence passages across all claims
  const allEvidence: Array<{
    claimIndex: number;
    claimText: string;
    verdict: string;
    passage: any;
  }> = [];

  analysis.claims.forEach((c) => {
    c.supporting_evidence.forEach((p) => {
      allEvidence.push({
        claimIndex: c.claim_index,
        claimText: c.claim_text,
        verdict: c.verdict,
        passage: p,
      });
    });
  });

  const availableDocs = Array.from(new Set(allEvidence.map((e) => e.passage.doc_title || e.passage.doc_id)));

  const filtered = allEvidence
    .filter((e) => {
      if (selectedDoc !== 'ALL') {
        const docName = e.passage.doc_title || e.passage.doc_id;
        if (docName !== selectedDoc) return false;
      }
      if (!search.trim()) return true;
      const q = search.toLowerCase();
      return (
        e.passage.text.toLowerCase().includes(q) ||
        e.claimText.toLowerCase().includes(q) ||
        (e.passage.doc_title && e.passage.doc_title.toLowerCase().includes(q))
      );
    });

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Evidence Explorer & Source Attribution
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Auditing grounding passages, document page references, and similarity coefficients behind verified claims.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onNavigate('claim_results')}
            className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-colors flex items-center gap-1.5"
          >
            <span>Back to Claims</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Filter and Search Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <label className="text-xs text-slate-400 font-medium">Document Filter:</label>
          <select
            value={selectedDoc}
            onChange={(e) => setSelectedDoc(e.target.value)}
            className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200 outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Documents ({availableDocs.length})</option>
            {availableDocs.map((doc) => (
              <option key={doc} value={doc}>
                {doc}
              </option>
            ))}
          </select>
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search passage content or claim..."
            className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Evidence Cards */}
      <div className="space-y-4">
        {filtered.length === 0 ? (
          <div className="p-8 text-center rounded-xl bg-slate-900/40 border border-slate-800 text-xs text-slate-400">
            No evidence passages matching criteria.
          </div>
        ) : (
          filtered.map((item, i) => {
            const p = item.passage;
            return (
              <div
                key={i}
                className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-slate-700/80 transition-all space-y-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-indigo-400" />
                    <span className="font-semibold text-white text-sm">
                      {p.doc_title || p.doc_id}
                    </span>
                    {p.page_number && (
                      <span className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-mono text-[11px]">
                        Page {p.page_number}
                      </span>
                    )}
                    {p.is_winning && (
                      <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium text-[10px]">
                        Decisive Winning Passage
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-3 font-mono text-xs">
                    <span className="text-slate-400">
                      Similarity: <strong className="text-indigo-400">{(p.retrieval_similarity * 100).toFixed(0)}%</strong>
                    </span>
                    <span className="text-emerald-400">
                      Entail: {(p.entailment_prob * 100).toFixed(1)}%
                    </span>
                    <span className="text-rose-400">
                      Contra: {(p.contradiction_prob * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                {/* Associated Claim Box */}
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center justify-between gap-4 text-xs">
                  <div className="space-y-0.5">
                    <span className="text-[10px] uppercase font-semibold text-slate-400">
                      Assigned To Claim #{item.claimIndex + 1}
                    </span>
                    <p className="font-medium text-slate-200">"{item.claimText}"</p>
                  </div>
                  <VerdictBadge verdict={item.verdict} size="sm" />
                </div>

                {/* Quoted Passage */}
                <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 font-serif leading-relaxed">
                  "{p.text}"
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
