import { AlertTriangle, Lightbulb } from 'lucide-react';

import type { BuildValidation } from '../types/assistant';

export function ValidationNotices({ validation }: { validation: BuildValidation | null }) {
  if (!validation || (validation.violations.length === 0 && validation.recommendations.length === 0)) {
    return null;
  }

  return (
    <div className="space-y-2">
      {validation.violations.map((violation) => (
        <div
          key={violation.ruleId}
          className="flex gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-200"
        >
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>
            {violation.message} <span className="font-mono text-red-400/70">({violation.ruleId})</span>
          </span>
        </div>
      ))}
      {validation.recommendations.map((recommendation) => (
        <div
          key={recommendation.ruleId}
          className="flex gap-2 rounded-xl border border-blue-500/30 bg-blue-500/10 p-3 text-xs text-blue-200"
        >
          <Lightbulb className="h-4 w-4 shrink-0" />
          <span>{recommendation.message}</span>
        </div>
      ))}
    </div>
  );
}
