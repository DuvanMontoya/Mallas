import { cookies } from "next/headers";

import { GovernanceBackoffice } from "@/components/governance-backoffice";
import { SourceProvenanceOverview } from "@/components/source-provenance-overview";
import Link from "next/link";
import { getCurriculumMap, getGovernanceInbox, getGovernanceProposal, getSessionSnapshot } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function SourcesPage() {
  const cookieHeader = (await cookies()).toString();
  const headers = cookieHeader ? { Cookie: cookieHeader } : undefined;
  const session = await getSessionSnapshot(headers);
  const editorial = session.user?.roles.some((role) => ["EDITOR", "REVIEWER", "ADMIN"].includes(role)) ?? false;
  if (!editorial) {
    const map = await getCurriculumMap({ headers });
    if (map.data) return <SourceProvenanceOverview map={map.data} showEditorialAccess={session.state === "anonymous"} />;
    return <div className="page-shell access-page"><section className="panel access-panel"><p className="eyebrow accent">Procedencia pública</p><h1>La evidencia no está disponible temporalmente</h1><p>No se abrió ninguna superficie administrativa. Vuelve a la malla o reintenta cuando la revisión publicada esté disponible.</p><div className="hero-actions"><a className="button button-primary" href="/sources">Reintentar</a><Link className="button button-secondary" href="/curriculum">Volver a la malla</Link></div></section></div>;
  }
  const inbox = await getGovernanceInbox({ headers });
  const firstProposalId = inbox.data?.proposals[0]?.id;
  const initialProposalResult = firstProposalId ? await getGovernanceProposal(firstProposalId, { headers }) : { data: null, failure: null, etag: null };
  return <GovernanceBackoffice initialInbox={inbox.data} initialFailure={inbox.failure} initialProposal={initialProposalResult.data} initialProposalEtag={initialProposalResult.etag} initialProposalFailure={initialProposalResult.failure} roles={session.user?.roles ?? []} />;
}
