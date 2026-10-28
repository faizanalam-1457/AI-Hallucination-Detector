import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './pages/Dashboard';
import { AnalyzeAnswer } from './pages/AnalyzeAnswer';
import { ClaimResults } from './pages/ClaimResults';
import { EvidenceExplorer } from './pages/EvidenceExplorer';
import { DocumentLibrary } from './pages/DocumentLibrary';
import { ResearchLab } from './pages/ResearchLab';
import { Benchmarks } from './pages/Benchmarks';
import { AnalysisHistory } from './pages/AnalysisHistory';
import { Settings } from './pages/Settings';
import { Analysis, PageId } from './types';
import { getAnalysis, getSettings } from './services/api';

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<PageId>('dashboard');
  const [activeAnalysis, setActiveAnalysis] = useState<Analysis | null>(null);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [activeModel, setActiveModel] = useState<string>('DeBERTa-v3 NLI + MiniLM-L6');
  const [device, setDevice] = useState<string>('cpu');

  useEffect(() => {
    // Initial fetch of system settings for active model & device
    getSettings()
      .then((cfg) => {
        if (cfg.active_models?.nli_cross_encoder) {
          setActiveModel(cfg.active_models.nli_cross_encoder.split('/').pop() || 'DeBERTa-v3');
        }
        if (cfg.device) {
          setDevice(cfg.device);
        }
      })
      .catch(() => {});
  }, []);

  const handleToggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    if (next === 'dark') {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
    } else {
      document.documentElement.classList.add('light');
      document.documentElement.classList.remove('dark');
    }
  };

  const handleSelectAnalysis = async (analysisId: string) => {
    try {
      const full = await getAnalysis(analysisId);
      setActiveAnalysis(full);
      setCurrentPage('claim_results');
    } catch (err: any) {
      alert(`Failed to load analysis: ${err.message}`);
    }
  };

  const handleAnalysisComplete = (analysis: Analysis) => {
    setActiveAnalysis(analysis);
    setCurrentPage('claim_results');
  };

  return (
    <div className={`min-h-screen flex flex-col ${theme === 'dark' ? 'bg-[#0a0e17] text-slate-100' : 'bg-slate-50 text-slate-900'}`}>
      <Header
        theme={theme}
        onToggleTheme={handleToggleTheme}
        activeModel={activeModel}
        device={device}
      />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          currentPage={currentPage}
          onSelectPage={setCurrentPage}
          hasActiveAnalysis={activeAnalysis !== null}
        />

        <main className="flex-1 overflow-y-auto">
          {currentPage === 'dashboard' && (
            <Dashboard
              onNavigate={setCurrentPage}
              onSelectAnalysis={handleSelectAnalysis}
            />
          )}

          {currentPage === 'analyze' && (
            <AnalyzeAnswer
              onAnalysisComplete={handleAnalysisComplete}
              onNavigate={setCurrentPage}
            />
          )}

          {currentPage === 'claim_results' && (
            <ClaimResults
              analysis={activeAnalysis}
              onNavigate={setCurrentPage}
            />
          )}

          {currentPage === 'evidence_explorer' && (
            <EvidenceExplorer
              analysis={activeAnalysis}
              onNavigate={setCurrentPage}
            />
          )}

          {currentPage === 'documents' && <DocumentLibrary />}

          {currentPage === 'research_lab' && <ResearchLab />}

          {currentPage === 'benchmarks' && <Benchmarks onNavigate={setCurrentPage} />}

          {currentPage === 'history' && (
            <AnalysisHistory
              onSelectAnalysis={handleSelectAnalysis}
              onNavigate={setCurrentPage}
            />
          )}

          {currentPage === 'settings' && (
            <Settings theme={theme} onToggleTheme={handleToggleTheme} />
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
