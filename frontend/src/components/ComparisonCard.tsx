import type { VehicleComparison } from '../types/assistant';
import { SidebarSection } from './SidebarSection';

export function ComparisonCard({ comparison }: { comparison: VehicleComparison }) {
  return (
    <SidebarSection title="Comparison">
      <div className="mb-4 grid grid-cols-2 gap-3 text-center">
        {[comparison.firstVehicle, comparison.secondVehicle].map((vehicleName, index) => (
          <div key={vehicleName} className="rounded-xl bg-black/30 p-2">
            <p className="text-[10px] uppercase text-slate-500">Vehicle {index === 0 ? 'A' : 'B'}</p>
            <p className="truncate text-xs font-semibold text-white">{vehicleName}</p>
          </div>
        ))}
      </div>
      <dl className="space-y-2 text-xs">
        <div className="flex justify-between border-b border-white/5 pb-2">
          <dt className="text-slate-400">Efficiency winner</dt>
          <dd className="font-semibold text-emerald-300">{comparison.efficiencyWinner}</dd>
        </div>
        <div className="flex justify-between border-b border-white/5 pb-2">
          <dt className="text-slate-400">Power winner</dt>
          <dd className="font-semibold text-amber-300">{comparison.powerWinner}</dd>
        </div>
      </dl>
      <p className="mt-3 text-xs italic text-slate-300">{comparison.summary}</p>
    </SidebarSection>
  );
}
