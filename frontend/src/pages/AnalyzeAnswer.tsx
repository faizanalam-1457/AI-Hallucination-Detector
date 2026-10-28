import React, { useState } from 'react';
import {
  Sparkles,
  RotateCcw,
  BookOpen,
  Sliders,
  CheckCircle2,
  FileText,
  AlertCircle,
  HelpCircle,
  Zap,
  ArrowRight,
} from 'lucide-react';
import { Analysis, PageId } from '../types';
import { analyzeAnswer, AnalyzeParams, getProvidersStatus } from '../services/api';

interface AnalyzeAnswerProps {
  onAnalysisComplete: (analysis: Analysis) => void;
  onNavigate: (page: PageId) => void;
}

const EXAMPLES = [
  {
    name: 'Lincoln Presidency (Entity & Date Contrast)',
    question: 'Was Abraham Lincoln the sixteenth President of the United States?',
    answer:
      'Abraham Lincoln was the seventeenth President of the United States. He signed the Emancipation Proclamation in 1863 and was assassinated in 1865.',
    evidence:
      'Abraham Lincoln was the sixteenth President of the United States, serving from March 4, 1861 until his assassination in April 1865. In 1863, Lincoln issued the Emancipation Proclamation.',
  },
  {
    name: 'Compound Statement (Penicillin & Steam Engine)',
    question: 'Who discovered penicillin and what else did he invent?',
    answer:
      'Sir Alexander Fleming was a Scottish physician who discovered penicillin in 1928, and he later invented the commercial steam engine in 1935.',
    evidence:
      'Sir Alexander Fleming FRS FRSE FRCS was a Scottish physician and microbiologist, best known for discovering the world’s first broadly effective antibiotic substance, penicillin, in 1928.',
  },
  {
    name: 'Biomedical Claim (DNA Double Helix)',
    question: 'Describe the molecular structure of DNA.',
    answer:
      'DNA is composed of two polynucleotide chains coiling around each other in a double helix. It was first synthesized as a triple carbohydrate ring.',
    evidence:
      'Deoxyribonucleic acid (DNA) is a polymer composed of two polynucleotide chains that coil around each other to form a double helix. The nitrogenous bases are adenine, cytosine, guanine, and thymine.',
  },
];

export const AnalyzeAnswer: React.FC<AnalyzeAnswerProps> = ({ onAnalysisComplete, onNavigate }) => {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [evidenceText, setEvidenceText] = useState('');
  const [method, setMethod] = useState<'adaptive' | 'nli' | 'embedding'>('adaptive');
  const [extractionMethod, setExtractionMethod] = useState<'gemini' | 'hf_router' | 'decomposed' | 'sentence'>('gemini');
  const [useGeminiExplanations, setUseGeminiExplanations] = useState<boolean>(true);
  const [geminiConfigured, setGeminiConfigured] = useState<boolean | null>(null);
  const [topK, setTopK] = useState(3);
  const [threshold, setThreshold] = useState(0.5);

  React.useEffect(() => {
    getProvidersStatus()
      .then((s) => setGeminiConfigured(s?.gemini?.configured ?? false))
      .catch(() => setGeminiConfigured(false));
  }, []);

  const [loading, setLoading] = useState(false);
  const [currentStage, setCurrentStage] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const handleLoadExample = (idx: number) => {
    const ex = EXAMPLES[idx];
    setQuestion(ex.question);
    setAnswer(ex.answer);
    setEvidenceText(ex.evidence);
    setError(null);
  };

  const handleClear = () => {
    setQuestion('');
    setAnswer('');
    setEvidenceText('');
    setError(null);
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!answer.trim()) {
      setError('Please provide an AI-generated answer to verify.');
      return;
    }

    setLoading(true);
    setError(null);

    // Simulate progress stages for user feedback
    setCurrentStage('1/5: Sanitizing input & preparing claim extraction...');
    const t1 = setTimeout(() => setCurrentStage('2/5: Decomposing answer into atomic claims...'), 300);
    const t2 = setTimeout(() => setCurrentStage('3/5: Querying vector index for evidence passages...'), 700);
    const t3 = setTimeout(() => setCurrentStage('4/5: Running cross-encoder NLI entailment evaluation...'), 1200);

    try {
      const params: AnalyzeParams = {
        question: question.trim() || undefined,
        answer: answer.trim(),
        evidence_text: evidenceText.trim() || undefined,
        method,
        extraction_method: extractionMethod,
        use_gemini_explanations: useGeminiExplanations,
        top_k: topK,
        decision_threshold: threshold,
      };

      const result = await analyzeAnswer(params);
      setCurrentStage('5/5: Aggregating multi-source verdicts and audit report...');
      setTimeout(() => {
        setLoading(false);
        onAnalysisComplete(result);
      }, 300);
    } catch (err: any) {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      setError(err.message || 'Verification failed. Please review inputs.');
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          Claim Verification Workspace
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          Decompose generated text into independently verifiable propositions, retrieve supporting evidence, and audit factual consistency.
        </p>
      </div>

      {/* Examples Palette */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span className="font-semibold text-slate-300 flex items-center gap-1.5">
            <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
            Quick Test Scenarios
          </span>
          <span>Click to populate sample verification triples</span>
        </div>
        <div className="flex flex-wrap gap-2 pt-1">
          {EXAMPLES.map((ex, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleLoadExample(i)}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700/80 text-slate-200 text-xs font-medium border border-slate-700/60 transition-all hover:border-indigo-500/50"
            >
              {ex.name}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Analysis Form */}
      <form onSubmit={handleAnalyze} className="space-y-6">
        <div className="grid grid-cols-1 gap-6">
          {/* Question (Optional) */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center justify-between">
              <span>Original Question / Prompt (Optional)</span>
              <span className="text-[11px] text-slate-500 normal-case">Contextual anchor</span>
            </label>
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. Was Abraham Lincoln the sixteenth President of the United States?"
              className="w-full px-4 py-2.5 rounded-xl bg-slate-900/90 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 placeholder-slate-500 text-sm outline-none transition-all"
            />
          </div>

          {/* Generated Answer (Required) */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                AI-Generated Answer <span className="text-rose-400">*</span>
              </label>
              <span className="text-[11px] text-slate-400">Target for factual claim extraction</span>
            </div>
            <textarea
              rows={4}
              required
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Paste the AI response to verify for hallucinations or unsubstantiated claims..."
              className="w-full p-4 rounded-xl bg-slate-900/90 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 placeholder-slate-500 text-sm outline-none transition-all resize-y"
            />
          </div>

          {/* Evidence Text / Context (Optional) */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <span>Direct Evidence Context (Optional)</span>
                <span className="text-[10px] font-normal px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                  Overrides or complements library
                </span>
              </label>
              <button
                type="button"
                onClick={() => onNavigate('documents')}
                className="text-xs text-indigo-400 hover:text-indigo-300"
              >
                Upload PDF / TXT in Library &rarr;
              </button>
            </div>
            <textarea
              rows={3}
              value={evidenceText}
              onChange={(e) => setEvidenceText(e.target.value)}
              placeholder="Paste reference passages or leave empty to automatically search indexed document library and knowledge base..."
              className="w-full p-4 rounded-xl bg-slate-900/90 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 placeholder-slate-500 text-sm outline-none transition-all resize-y"
            />
          </div>
        </div>

        {/* Configuration Parameters Panel */}
        <div className="p-5 rounded-2xl bg-slate-900/40 border border-slate-800 space-y-5">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-300">
            <Sliders className="w-4 h-4 text-indigo-400" />
            <span>Verification Engine Configuration</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Method */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300">Verification Method</label>
              <select
                value={method}
                onChange={(e: any) => setMethod(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 text-xs outline-none focus:border-indigo-500"
              >
                <option value="adaptive">Adaptive Cascade (Fast & Deep)</option>
                <option value="nli">DeBERTa-v3 Cross-Encoder (NLI)</option>
                <option value="embedding">Embedding Similarity (Baseline)</option>
              </select>
            </div>

            {/* Claim Decomposition */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-slate-300">Claim Extraction</label>
                {geminiConfigured !== null && (
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${
                      geminiConfigured
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    }`}
                  >
                    {geminiConfigured ? 'Gemini API ✓' : 'Local Fallback'}
                  </span>
                )}
              </div>
              <select
                value={extractionMethod}
                onChange={(e: any) => setExtractionMethod(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 text-xs outline-none focus:border-indigo-500"
              >
                <option value="gemini">Google Gemini API (Structured LLM)</option>
                <option value="hf_router">DeepSeek (Hugging Face Router)</option>
                <option value="decomposed">Atomic Clause Decomposer (Local)</option>
                <option value="sentence">Sentence Splitting Baseline (Local)</option>
              </select>
            </div>

            {/* Top-K Passages */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-300 font-medium">Top-K Evidence:</span>
                <span className="font-mono text-indigo-400 font-semibold">{topK}</span>
              </div>
              <input
                type="range"
                min={1}
                max={10}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="w-full accent-indigo-500 cursor-pointer"
              />
            </div>

            {/* Threshold */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-300 font-medium">Decision Cutoff:</span>
                <span className="font-mono text-indigo-400 font-semibold">{threshold.toFixed(2)}</span>
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
            </div>
          </div>

          {/* Gemini Grounded Explanations Toggle */}
          <div className="pt-3 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
            <label className="flex items-center gap-2.5 cursor-pointer text-slate-300 hover:text-white transition-colors">
              <input
                type="checkbox"
                checked={useGeminiExplanations}
                onChange={(e) => setUseGeminiExplanations(e.target.checked)}
                className="w-4 h-4 rounded accent-indigo-500 bg-slate-900 border-slate-700"
              />
              <span className="font-medium flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                Synthesize Grounded Explanations via Google Gemini
              </span>
            </label>
            <span className="text-[11px] text-slate-500">
              Conditioned strictly on retrieved evidence excerpts; never contradicts NLI verdicts
            </span>
          </div>
        </div>

        {/* Live Processing Stage Indicator */}
        {loading && (
          <div className="p-4 rounded-xl bg-indigo-950/40 border border-indigo-500/30 text-indigo-200 text-xs space-y-2">
            <div className="flex items-center gap-2 font-medium">
              <div className="w-3.5 h-3.5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
              <span>{currentStage}</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
              <div className="bg-gradient-to-r from-indigo-500 to-cyan-400 h-1.5 rounded-full animate-pulse w-3/4" />
            </div>
          </div>
        )}

        {/* Actions Bar */}
        <div className="flex items-center justify-between pt-2">
          <button
            type="button"
            onClick={handleClear}
            disabled={loading}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 text-sm font-medium transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Clear Inputs</span>
          </button>

          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-sm shadow-lg shadow-indigo-600/30 transition-all hover:scale-[1.02]"
          >
            <Sparkles className="w-4 h-4" />
            <span>{loading ? 'Evaluating Claims...' : 'Analyze Answer'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
