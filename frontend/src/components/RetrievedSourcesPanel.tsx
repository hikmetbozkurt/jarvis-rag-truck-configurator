import type { SourceReference } from '../types/assistant';
import { SidebarSection } from './SidebarSection';

export function RetrievedSourcesPanel({ sources }: { sources: SourceReference[] }) {
  return (
    <SidebarSection title="Grounding sources">
      {sources.length === 0 ? (
        <p className="text-xs text-slate-500">Sources used for the latest answer will appear here.</p>
      ) : (
        <ul className="space-y-2">
          {sources.map((source) => (
            <li key={source.documentId} className="rounded-xl border border-white/5 bg-black/20 p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-[11px] text-blue-300">{source.documentId}</span>
                {source.wasCited && (
                  <span className="rounded bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-300">
                    cited
                  </span>
                )}
              </div>
              <p className="mt-1 truncate text-xs text-slate-300">{source.title}</p>
              <p className="mt-1 text-[10px] text-slate-500">
                {source.sourceType.replace(/_/g, ' ')} · relevance {source.relevanceScore.toFixed(3)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </SidebarSection>
  );
}
