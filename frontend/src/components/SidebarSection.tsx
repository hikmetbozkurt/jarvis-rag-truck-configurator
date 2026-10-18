import type { ReactNode } from 'react';

interface SidebarSectionProps {
  title: string;
  headerAccessory?: ReactNode;
  children: ReactNode;
}

export function SidebarSection({ title, headerAccessory, children }: SidebarSectionProps) {
  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-[11px] font-bold uppercase tracking-widest text-blue-400">{title}</h3>
        {headerAccessory}
      </div>
      {children}
    </section>
  );
}
