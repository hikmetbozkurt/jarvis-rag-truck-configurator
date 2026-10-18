import { useEffect, useState } from 'react';

import { fetchRequestTrace } from '../services/assistantApi';
import type { RequestTrace } from '../types/assistant';
import { SidebarSection } from './SidebarSection';

export function TraceDetailsPanel({ traceId }: { traceId: string | null }) {
  const [trace, setTrace] = useState<RequestTrace | null>(null);
  const [loadingError, setLoadingError] = useState<string | null>(null);

  useEffect(() => {
    setLoadingError(null);
    if (!traceId) {
      setTrace(null);
      return;
    }
    let isCurrentRequest = true;
    fetchRequestTrace(traceId)
      .then((loadedTrace) => isCurrentRequest && setTrace(loadedTrace))
      .catch((error: Error) => isCurrentRequest && setLoadingError(error.message));
    return () => {
      isCurrentRequest = false;
    };
  }, [traceId]);

  if (!traceId) return null;

  return (
    <SidebarSection
      title="Retrieval trace"
      headerAccessory={<span className="font-mono text-[10px] text-slate-500">{traceId.slice(0, 8)}</span>}
    >
      {loadingError && <p className="text-xs text-red-300">{loadingError}</p>}
      {trace && (
        <div className="space-y-4 text-xs">
          {trace.unknownCitationIds.length > 0 && (
            <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-2 text-amber-200">
              Model cited documents that were not retrieved: {trace.unknownCitationIds.join(', ')}
            </p>
          )}
          {trace.replyParsed === false && (
            <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-2 text-amber-200">
              The model reply was not valid JSON, so the raw text was shown.
            </p>
          )}

          <div>
            <p className="mb-1 font-semibold text-slate-400">Candidates per channel</p>
            <ul className="space-y-1 font-mono text-[11px] text-slate-300">
              {Object.entries(trace.candidatesByChannel).map(([channelName, hits]) => (
                <li key={channelName} className="flex justify-between">
                  <span>{channelName}</span>
                  <span className="text-slate-500">{hits.length} hits</span>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <p className="mb-1 font-semibold text-slate-400">Stage timings</p>
            <ul className="space-y-1 font-mono text-[11px] text-slate-300">
              {Object.entries(trace.stageDurationsMs).map(([stageName, durationMs]) => (
                <li key={stageName} className="flex justify-between">
                  <span>{stageName}</span>
                  <span className="text-slate-500">{durationMs.toFixed(0)} ms</span>
                </li>
              ))}
              <li className="flex justify-between border-t border-white/5 pt-1">
                <span>total</span>
                <span className="text-slate-500">{trace.totalDurationMs.toFixed(0)} ms</span>
              </li>
            </ul>
          </div>

          {trace.estimatedPromptTokens !== null && (
            <p className="text-[11px] text-slate-500">Prompt size: about {trace.estimatedPromptTokens} tokens</p>
          )}
        </div>
      )}
    </SidebarSection>
  );
}
