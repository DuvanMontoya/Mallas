import { cookies } from "next/headers";

import { GovernanceBackoffice } from "@/components/governance-backoffice";
import { getGovernanceInbox, getGovernanceProposal, getSessionSnapshot } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function SourcesPage() {
  const cookieHeader = (await cookies()).toString();
  const headers = cookieHeader ? { Cookie: cookieHeader } : undefined;
  const [session, inbox] = await Promise.all([
    getSessionSnapshot(headers),
    getGovernanceInbox({ headers }),
  ]);
  const firstProposalId = inbox.data?.proposals[0]?.id;
  const initialProposalResult = firstProposalId ? await getGovernanceProposal(firstProposalId, { headers }) : { data: null, failure: null, etag: null };
  return <GovernanceBackoffice initialInbox={inbox.data} initialFailure={inbox.failure} initialProposal={initialProposalResult.data} initialProposalEtag={initialProposalResult.etag} initialProposalFailure={initialProposalResult.failure} roles={session.user?.roles ?? []} />;
}
