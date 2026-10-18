import type { BuildValidation, VehicleBuild } from '../types/assistant';
import { SidebarSection } from './SidebarSection';

const BUILD_FIELDS: { field: keyof VehicleBuild; label: string }[] = [
  { field: 'model', label: 'Model' },
  { field: 'engine', label: 'Engine' },
  { field: 'transmission', label: 'Transmission' },
  { field: 'trim', label: 'Trim' },
  { field: 'application', label: 'Application' },
  { field: 'region', label: 'Region' },
];

const STATUS_STYLES: Record<BuildValidation['status'], string> = {
  valid: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  invalid: 'border-red-500/30 bg-red-500/10 text-red-300',
  incomplete: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
};

interface BuildTrackerCardProps {
  activeBuild: VehicleBuild;
  validation: BuildValidation | null;
}

export function BuildTrackerCard({ activeBuild, validation }: BuildTrackerCardProps) {
  const buildStatus = validation?.status ?? 'incomplete';

  return (
    <SidebarSection
      title="Active build"
      headerAccessory={
        <span className={`rounded border px-2 py-0.5 text-[10px] font-bold uppercase ${STATUS_STYLES[buildStatus]}`}>
          {buildStatus}
        </span>
      }
    >
      <dl className="space-y-2.5">
        {BUILD_FIELDS.map(({ field, label }) => (
          <div key={field} className="flex items-end justify-between border-b border-white/5 pb-2">
            <dt className="text-[11px] font-semibold uppercase text-slate-500">{label}</dt>
            <dd className={`font-mono text-xs ${activeBuild[field] ? 'text-white' : 'text-slate-600'}`}>
              {activeBuild[field] ?? 'Not selected'}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-[11px] text-slate-500">Status is checked by the rule engine, not by the language model.</p>
    </SidebarSection>
  );
}
