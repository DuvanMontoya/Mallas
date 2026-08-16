import type { ReactNode } from "react";

export interface EmptyStateProps {
  title: string;
  description: string;
  action?: ReactNode;
  tone?: "neutral" | "unknown";
}

export function EmptyState({ title, description, action, tone = "neutral" }: EmptyStateProps) {
  return (
    <div className={`empty-state empty-state-${tone}`} role="status">
      <span className="empty-state-icon" aria-hidden="true">—</span>
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
        {action ? <div className="empty-state-action">{action}</div> : null}
      </div>
    </div>
  );
}
