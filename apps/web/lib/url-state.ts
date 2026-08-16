export interface WorkspaceUrlState {
  query: string;
  view: string;
  selected: string | null;
}

export function readWorkspaceUrlState(params: URLSearchParams): WorkspaceUrlState {
  return {
    query: params.get("q") ?? "",
    view: params.get("view") ?? "all",
    selected: params.get("selected"),
  };
}

export function updateWorkspaceUrl(
  current: URLSearchParams,
  patch: Partial<WorkspaceUrlState>,
): URLSearchParams {
  const next = new URLSearchParams(current);
  if (patch.query !== undefined) {
    patch.query ? next.set("q", patch.query) : next.delete("q");
  }
  if (patch.view !== undefined) {
    patch.view && patch.view !== "all" ? next.set("view", patch.view) : next.delete("view");
  }
  if (patch.selected !== undefined) {
    patch.selected ? next.set("selected", patch.selected) : next.delete("selected");
  }
  return next;
}

export function safeInternalPath(candidate: string | null | undefined, fallback = "/"): string {
  if (!candidate || !candidate.startsWith("/") || candidate.startsWith("//")) return fallback;
  return candidate;
}
