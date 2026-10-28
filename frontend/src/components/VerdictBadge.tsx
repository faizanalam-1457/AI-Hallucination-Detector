import React from 'react';
import { CheckCircle2, XCircle, HelpCircle, AlertOctagon } from 'lucide-react';
import { ClaimVerdict } from '../types';

interface VerdictBadgeProps {
  verdict: ClaimVerdict | string;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
}

export const VerdictBadge: React.FC<VerdictBadgeProps> = ({
  verdict,
  size = 'md',
  showIcon = true,
}) => {
  const norm = verdict.toUpperCase();

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5 font-medium',
    lg: 'text-sm px-3.5 py-1.5 gap-2 font-semibold',
  }[size];

  if (norm === 'SUPPORTED') {
    return (
      <span
        className={`inline-flex items-center rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 tracking-wide ${sizeClasses}`}
      >
        {showIcon && <CheckCircle2 className={size === 'lg' ? 'w-4 h-4' : 'w-3.5 h-3.5'} />}
        SUPPORTED
      </span>
    );
  }

  if (norm === 'CONTRADICTED') {
    return (
      <span
        className={`inline-flex items-center rounded-full bg-rose-500/15 text-rose-400 border border-rose-500/30 tracking-wide ${sizeClasses}`}
      >
        {showIcon && <XCircle className={size === 'lg' ? 'w-4 h-4' : 'w-3.5 h-3.5'} />}
        CONTRADICTED
      </span>
    );
  }

  if (norm === 'CONFLICTING_EVIDENCE') {
    return (
      <span
        className={`inline-flex items-center rounded-full bg-purple-500/15 text-purple-400 border border-purple-500/30 tracking-wide ${sizeClasses}`}
      >
        {showIcon && <AlertOctagon className={size === 'lg' ? 'w-4 h-4' : 'w-3.5 h-3.5'} />}
        CONFLICTING EVIDENCE
      </span>
    );
  }

  // Default: INSUFFICIENT_EVIDENCE / NEUTRAL
  return (
    <span
      className={`inline-flex items-center rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30 tracking-wide ${sizeClasses}`}
    >
      {showIcon && <HelpCircle className={size === 'lg' ? 'w-4 h-4' : 'w-3.5 h-3.5'} />}
      INSUFFICIENT EVIDENCE
    </span>
  );
};
