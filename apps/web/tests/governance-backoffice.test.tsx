import axe from "axe-core";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GovernanceBackoffice } from "../components/governance-backoffice";
import type { GovernanceProposal, SourceInbox } from "../lib/api";

const mocks = vi.hoisted(() => ({
  getGovernanceProposal: vi.fn(),
  submitGovernanceProposal: vi.fn(),
  reviewGovernanceProposal: vi.fn(),
  publishGovernanceProposal: vi.fn(),
  reviewGovernanceCandidate: vi.fn(),
  previewGovernanceCandidates: vi.fn(),
  applyGovernanceCandidates: vi.fn(),
  linkGovernanceRequirementEvidence: vi.fn(),
  getAssignmentPolicies: vi.fn().mockResolvedValue({ data: [], failure: null }),
  submitAssignmentPolicy: vi.fn(),
  publishAssignmentPolicy: vi.fn(),
  problemMessage: vi.fn((problem: { detail?: string } | null, fallback: string) => problem?.detail ?? fallback),
}));

vi.mock("../lib/api", () => mocks);

const inbox = {
  documents: [],
  snapshots: [],
  workflow: ["DISCOVERED", "SNAPSHOT", "EXTRACTED", "DRAFT", "VALIDATED", "IN_REVIEW", "APPROVED", "PUBLISHED"],
  proposals: [{
    id: "00000000-0000-4000-8000-000000000701",
    proposal_key: "test:proposal",
    title: "Revisión de prueba",
    status: "DRAFT",
    base_revision_id: null,
    candidate_revision_id: "00000000-0000-4000-8000-000000000702",
    candidate_revision_code: "2514-2026",
    source_snapshot_id: "00000000-0000-4000-8000-000000000703",
    source_title: "Fuente de prueba",
    content_fingerprint: "a".repeat(64),
    semantic_has_changes: true,
    created_by: "editor@example.test",
    updated_at: "2026-08-16T20:00:00Z",
    version: "2026-08-16T20:00:00Z",
    pending_candidates: 0,
  }],
} as unknown as SourceInbox;

const proposal = {
  ...inbox.proposals[0],
  rationale: "Fuente archivada con diff explícito.",
  base_revision: null,
  candidate_revision: {
    id: inbox.proposals[0].candidate_revision_id,
    plan_code: "2514",
    revision_code: "2514-2026",
    status: "DRAFT",
    effective_from: "2026-01-01",
    effective_to: null,
    total_required_credits: 141,
    source_set_hash: "b".repeat(64),
    content_hash: "c".repeat(64),
    published_at: null,
    version: "2026-08-16T20:00:00Z",
  },
  source_snapshot: {
    id: inbox.proposals[0].source_snapshot_id,
    document_id: "00000000-0000-4000-8000-000000000704",
    document_title: "Fuente de prueba",
    captured_at: "2026-08-16T19:00:00Z",
    sha256: "d".repeat(64),
    mime_type: "application/pdf",
    storage_key: "private/source.pdf",
    source_url: null,
    metadata: {},
    evidence_count: 1,
    version: "2026-08-16T19:00:00Z",
  },
  semantic_diff: {
    added: { courses: [{ code: "STAT000" }] },
    removed: {},
    changed: [],
    has_changes: true,
  },
  validation_report: { ok: true, errors: [], warnings: [], unknowns: [], counts: {}, totals: {}, verified_rules_without_evidence: [] },
  impact_analysis: { audits_affected: 0, students_potentially_affected: 0, changed_semantic_items: 1, new_unknowns: 0, cycles_detected: 0, totals_inconsistent: false, publish_blockers: [] },
  requirements: [{
    id: "00000000-0000-4000-8000-000000000705",
    code: "TEST:PREREQUISITE",
    owner_type: "COURSE",
    owner_id: "00000000-0000-4000-8000-000000000706",
    purpose: "ENROLLMENT_PREREQUISITE",
    ast: { type: "COURSE_PASSED", course_code: "STAT000" },
    ast_schema_version: "1.0.0",
    ast_hash: "e".repeat(64),
    epistemic_status: "VERIFIED",
    explanation_key: "test.rule",
    human_explanation: "Haber aprobado el curso STAT000.",
    metadata: {},
    evidence: [{
      id: "00000000-0000-4000-8000-000000000707",
      reference: "d#page:1",
      snapshot_id: inbox.proposals[0].source_snapshot_id,
      snapshot_sha256: "d".repeat(64),
      locator: "page:1",
      page: 1,
      section: "",
      excerpt: "Evidence",
      annotation: "",
      source_title: "Fuente de prueba",
      source_url: null,
    }],
    version: "2026-08-16T19:00:00Z",
  }],
  candidates: [{
    id: "00000000-0000-4000-8000-000000000708",
    entity: "courses",
    entity_key: "STAT000",
    operation: "ADD",
    before: null,
    after: { code: "STAT000" },
    status: "ACCEPTED",
    epistemic_status: "INFERRED_PENDING_REVIEW",
    evidence: [],
    reviewed_by: "editor@example.test",
    reviewed_at: "2026-08-16T19:30:00Z",
    note: "Reviewed",
    version: "2026-08-16T19:30:00Z",
  }],
  reviews: [],
  publication: null,
  audit_events: [],
} as unknown as GovernanceProposal;

describe("governance backoffice", () => {
  it("shows the rule inspector, source chain, and editor action", async () => {
    mocks.submitGovernanceProposal.mockResolvedValue({ data: { ...proposal, status: "IN_REVIEW" }, failure: null });
    render(<GovernanceBackoffice initialInbox={inbox} initialFailure={null} initialProposal={proposal} initialProposalEtag={'"2026-08-16T20:00:00Z"'} initialProposalFailure={null} roles={["EDITOR"]} currentUserId={10} />);
    expect(screen.getByRole("heading", { name: /revisiones curriculares/i })).toBeInTheDocument();
    fireEvent.click(screen.getByText(/inspeccionar reglas y evidencia/i));
    expect(screen.getByRole("heading", { name: /qué significa la regla y de dónde sale/i })).toBeInTheDocument();
    expect(screen.getByText(/haber aprobado el curso stat000/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /enviar a revisión/i }));
    await waitFor(() => expect(mocks.submitGovernanceProposal).toHaveBeenCalledWith(
      proposal.id,
      {},
      { ifMatch: '"2026-08-16T20:00:00Z"' },
    ));
    await waitFor(() => expect(screen.getByTestId("governance-live-region")).toHaveTextContent(/estado IN_REVIEW/i));
  });

  it("exposes reviewer-only approval and has no serious accessibility violations", async () => {
    const reviewProposal = { ...proposal, status: "IN_REVIEW" } as GovernanceProposal;
    mocks.reviewGovernanceProposal.mockResolvedValue({ data: { ...reviewProposal, status: "APPROVED" }, failure: null });
    const { container } = render(<GovernanceBackoffice initialInbox={{ ...inbox, proposals: [{ ...inbox.proposals[0], status: "IN_REVIEW" }] } as SourceInbox} initialFailure={null} initialProposal={reviewProposal} initialProposalEtag={'"2026-08-16T20:00:00Z"'} initialProposalFailure={null} roles={["REVIEWER"]} currentUserId={11} />);
    expect(screen.getByRole("button", { name: /aprobar revisión/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /aprobar revisión/i }));
    await waitFor(() => expect(mocks.reviewGovernanceProposal).toHaveBeenCalledWith(
      reviewProposal.id,
      { decision: "APPROVE", comment: "" },
      { ifMatch: '"2026-08-16T20:00:00Z"' },
    ));
    await waitFor(() => expect(screen.getByTestId("governance-live-region")).toHaveTextContent(/estado APPROVED/i));
    expect((await axe.run(container)).violations).toEqual([]);
  });

  it("submits a draft assignment policy and exposes the sealed review package", async () => {
    const draft = {
      id: "00000000-0000-4000-8000-000000000801",
      policy_code: "STAT-ADMISSION",
      version: 1,
      program_name: "Estadística",
      plan_code: "2514",
      revision_code: "2514-2026",
      context: "ADMISSION",
      epistemic_status: "VERIFIED",
      status: "DRAFT",
      prepared_by_id: 10,
      approved_by_id: null,
      admission_from: "2026-01-01",
      admission_to: null,
      cohort_code: "",
      previous_plan_code: null,
      normative_published_on: "2025-06-01",
      effective_from: "2026-01-01",
      effective_to: null,
      allow_retired_revision: false,
      review_content_hash: null,
      source_set_hash: null,
      evidence: [],
    };
    const submitted = {
      ...draft,
      status: "IN_REVIEW",
      review_content_hash: "a".repeat(64),
      source_set_hash: "b".repeat(64),
      evidence: [{ purpose: "ASSIGNMENT_SCOPE", source_title: "Acuerdo 17", locator: "Art. 2", excerpt: "Aplica a ingresos 2026-1.", excerpt_hash: "c".repeat(64), snapshot_sha256: "d".repeat(64) }],
    };
    mocks.getAssignmentPolicies.mockResolvedValue({ data: [draft], failure: null });
    mocks.submitAssignmentPolicy.mockResolvedValue({ data: submitted, failure: null });
    render(<GovernanceBackoffice initialInbox={inbox} initialFailure={null} initialProposal={proposal} initialProposalEtag={'"2026-08-16T20:00:00Z"'} initialProposalFailure={null} roles={["EDITOR"]} currentUserId={10} />);
    fireEvent.click(screen.getByText("Políticas de asignación curricular"));
    const policyRow = (await screen.findByText("STAT-ADMISSION")).closest("tr");
    expect(policyRow).not.toBeNull();
    fireEvent.click(within(policyRow!).getByRole("button", { name: "Enviar STAT-ADMISSION a revisión" }));
    expect(await screen.findByText("Ver material sometido")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Ver material sometido"));
    expect(screen.getByText("Aplica a ingresos 2026-1.")).toBeInTheDocument();
    expect(mocks.submitAssignmentPolicy).toHaveBeenCalledWith(draft.id);
  });
});
