import type { HTMLAttributes } from "react";

export type StatusTone = "passed" | "in-progress" | "eligible" | "blocked" | "unknown" | "neutral";

const defaultLabels: Record<StatusTone, string> = {
  passed: "Aprobado",
  "in-progress": "En curso",
  eligible: "Elegible",
  blocked: "Bloqueado",
  unknown: "Por verificar",
  neutral: "Informativo",
};

export interface StatusBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone: StatusTone;
  label?: string;
}

export function StatusBadge({ tone, label = defaultLabels[tone], className = "", ...props }: StatusBadgeProps) {
  return (
    <span className={`status-badge status-${tone}${className ? ` ${className}` : ""}`} data-status={tone} {...props}>
      <span className="status-badge-mark" aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}
