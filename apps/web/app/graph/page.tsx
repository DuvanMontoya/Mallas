import { cookies } from "next/headers";

import { DependencyGraphShell } from "@/components/dependency-graph-shell";
import { getDependencyGraph } from "@/lib/api";

export const dynamic = "force-dynamic";

type GraphPageProps = {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
};

export default async function GraphPage({ searchParams }: GraphPageProps) {
  const params = await searchParams;
  const selected = Array.isArray(params.selected) ? params.selected[0] : params.selected;
  let headers: HeadersInit | undefined;
  try {
    const cookieHeader = (await cookies()).toString();
    headers = cookieHeader ? { Cookie: cookieHeader } : undefined;
  } catch {
    headers = undefined;
  }
  const result = await getDependencyGraph({ headers, selected });
  return <DependencyGraphShell graph={result.data} failureMessage={result.failure?.problem?.detail ?? undefined} />;
}
