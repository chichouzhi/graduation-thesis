import type { ReactNode } from "react";

type StatCardProps = {
  label: string;
  value: string;
  hint: string;
  icon: ReactNode;
};

export function StatCard({ label, value, hint, icon }: StatCardProps) {
  return (
    <article className="stat-card">
      <header>
        <div>
          <div className="stat-label">{label}</div>
          <div className="stat-value">{value}</div>
          <div className="stat-hint">{hint}</div>
        </div>
        <div className="icon-pill">{icon}</div>
      </header>
    </article>
  );
}
