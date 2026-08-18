import type { ReactNode } from "react";

export function Alert({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "warning" | "error" | "success" }) {
  return (
    <div className={`alert alert-${tone}`} role={tone === "error" ? "alert" : "status"}>
      <span className="alert-mark" aria-hidden="true">{tone === "error" || tone === "warning" ? "!" : "i"}</span>
      <div>{children}</div>
    </div>
  );
}
