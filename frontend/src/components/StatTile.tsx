import type { ReactNode } from 'react';

export interface StatTileProps {
  label: string;
  value: string;
  icon?: ReactNode;
}

export default function StatTile({ label, value, icon }: StatTileProps) {
  return (
    <div className="rounded-lg border border-flood-border bg-flood-panel-2 p-4">
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-xs uppercase text-flood-muted">{label}</span>
      </div>
      <p className="mt-1 text-2xl font-bold text-flood-text">{value}</p>
    </div>
  );
}
