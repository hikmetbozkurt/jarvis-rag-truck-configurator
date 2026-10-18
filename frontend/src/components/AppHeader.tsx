import { RotateCcw, Truck } from 'lucide-react';

import type { ServiceReadiness } from '../services/assistantApi';

interface AppHeaderProps {
  readiness: ServiceReadiness | null;
  isVoiceModeActive: boolean;
  onStartNewSession: () => void;
}

function describeReadiness(readiness: ServiceReadiness | null) {
  if (!readiness) return { label: 'Backend offline', dotClass: 'bg-red-500' };
  if (readiness.status === 'ready') {
    return {
      label: `${readiness.languageModelName} · ${readiness.indexedDocumentCount} docs indexed`,
      dotClass: 'bg-emerald-500',
    };
  }
  return {
    label: readiness.languageModelReachable ? 'Knowledge base empty' : `${readiness.languageModelName} not reachable`,
    dotClass: 'bg-amber-500',
  };
}

export function AppHeader({ readiness, isVoiceModeActive, onStartNewSession }: AppHeaderProps) {
  const readinessSummary = describeReadiness(readiness);

  return (
    <header className="flex items-center justify-between border-b border-white/5 bg-slate-950/80 px-6 py-4 backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-slate-800">
          <Truck className="h-5 w-5 text-blue-400" />
        </div>
        <div>
          <h1 className="flex items-center gap-2 text-lg font-bold text-white">
            Jarvis
            {isVoiceModeActive && (
              <span className="rounded border border-red-500/30 bg-red-500/20 px-1.5 py-0.5 text-[9px] uppercase tracking-widest text-red-300">
                Live voice
              </span>
            )}
          </h1>
          <p className="text-[11px] uppercase tracking-wider text-slate-500">Truck configuration assistant</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300 sm:flex">
          <span className={`h-2 w-2 rounded-full ${readinessSummary.dotClass}`} />
          {readinessSummary.label}
        </div>
        <button
          type="button"
          onClick={onStartNewSession}
          className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-white/10"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          New session
        </button>
      </div>
    </header>
  );
}
