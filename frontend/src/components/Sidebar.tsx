import React from 'react';
import {
  LayoutDashboard,
  Sparkles,
  CheckSquare,
  Compass,
  FolderGit2,
  FlaskConical,
  BarChart3,
  History,
  Settings,
} from 'lucide-react';
import { PageId } from '../types';

interface SidebarProps {
  currentPage: PageId;
  onSelectPage: (page: PageId) => void;
  hasActiveAnalysis: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onSelectPage,
  hasActiveAnalysis,
}) => {
  const navItems = [
    { id: 'dashboard' as PageId, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'analyze' as PageId, label: 'Analyze Answer', icon: Sparkles, badge: 'New' },
    {
      id: 'claim_results' as PageId,
      label: 'Claim-Level Results',
      icon: CheckSquare,
      disabled: !hasActiveAnalysis,
    },
    {
      id: 'evidence_explorer' as PageId,
      label: 'Evidence Explorer',
      icon: Compass,
      disabled: !hasActiveAnalysis,
    },
    { id: 'documents' as PageId, label: 'Document Library', icon: FolderGit2 },
    { id: 'research_lab' as PageId, label: 'Research Lab', icon: FlaskConical, badge: 'Cascade' },
    { id: 'benchmarks' as PageId, label: 'Benchmarks & Datasets', icon: BarChart3 },
    { id: 'history' as PageId, label: 'Analysis History', icon: History },
    { id: 'settings' as PageId, label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-900/60 p-4 flex flex-col justify-between shrink-0">
      <div className="space-y-1">
        <div className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Core Workspaces
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentPage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => !item.disabled && onSelectPage(item.id)}
              disabled={item.disabled}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : item.disabled
                  ? 'text-slate-600 cursor-not-allowed hover:bg-transparent'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/70'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span
                  className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                    isActive
                      ? 'bg-indigo-700 text-indigo-100'
                      : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Research Citation Footnote */}
      <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-800 text-xs text-slate-400 space-y-1">
        <p className="font-semibold text-slate-300">Methodology</p>
        <p className="text-[11px] leading-relaxed text-slate-400">
          Cross-Encoder NLI + Adaptive Semantic Routing on DeBERTa-v3 & MiniLM-L6.
        </p>
      </div>
    </aside>
  );
};
