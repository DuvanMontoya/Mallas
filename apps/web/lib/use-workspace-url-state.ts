"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

import { readWorkspaceUrlState, updateWorkspaceUrl, type WorkspaceUrlState } from "./url-state";

export function useWorkspaceUrlState() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const state = useMemo(() => readWorkspaceUrlState(new URLSearchParams(searchParams.toString())), [searchParams]);
  const setState = useCallback((patch: Partial<WorkspaceUrlState>) => {
    const next = updateWorkspaceUrl(new URLSearchParams(searchParams.toString()), patch);
    const query = next.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }, [pathname, router, searchParams]);

  return { state, setState };
}
