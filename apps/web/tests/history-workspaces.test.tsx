import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { HistoryImportWorkspace } from "../components/history-import-workspace";
import { HistoryWorkspace } from "../components/history-workspace";
import type { HistoryAttemptPage, HistoryImportPreview } from "../lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), replace: vi.fn() }),
}));

const attemptsPage: HistoryAttemptPage = {
  items: [{
    id: "attempt-1",
    enrollment_id: "enrollment-1",
    course_version_id: "course-1",
    course_code: "1000001",
    course_name: "Matemáticas básicas",
    term_id: "term-1",
    term_code: "2023-1S",
    attempt_number: 1,
    status: "PASSED",
    grade: "4.00",
    credits_earned: 4,
    origin: "MANUAL",
    import_batch_id: null,
    notes: "",
    audit_run_id: null,
    version: "v1",
  }],
  total: 1,
  limit: 1,
  offset: 0,
  next_offset: null,
  previous_offset: null,
};

const importPreview = {
  id: "batch-1",
  enrollment_id: "enrollment-1",
  status: "PREVIEW",
  source_kind: "CSV",
  original_filename: "historia.csv",
  content_sha256: "a".repeat(64),
  content_fingerprint: "b".repeat(64),
  parser_version: "csv-v1",
  schema_version: "1",
  validation_errors: [],
  metadata: {},
  created: true,
  candidate_count: 1,
  unresolved_count: 1,
  error_count: 0,
  version: "batch-v1",
  candidates: [{
    id: "candidate-1",
    row_number: 1,
    source_locator: "fila 2",
    status: "CONFLICT",
    candidate_fingerprint: "c".repeat(64),
    raw_payload: { course_code: "1000001" },
    normalized_payload: { course_code: "1000001" },
    parse_errors: [],
    warnings: [],
    confidence: 80,
    requires_confirmation: true,
    conflict_details: [{ field: "grade", message: "Conflicto" }],
    decision: "PENDING",
    selected_course_version_id: null,
    external_code: "",
    note: "",
    version: "candidate-v1",
  }],
} as HistoryImportPreview;

describe("history workspaces", () => {
  it("supports retakes and reserves ANNULLED for the dedicated action", () => {
    render(<HistoryWorkspace enrollmentId="enrollment-1" studentName="Estudiante" attemptsPage={attemptsPage} />);

    expect(screen.getByRole("spinbutton", { name: "Número de intento" })).toHaveValue(1);
    expect(screen.queryByRole("option", { name: "Anulado" })).not.toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: /1000001.*Matemáticas básicas/i })).toBeInTheDocument();
  });

  it("lets an internal conflict be mapped and requires an explicit note", () => {
    render(<HistoryImportWorkspace enrollmentId="enrollment-1" initialPreview={importPreview} courseOptions={[{ id: "course-1", code: "1000001", name: "Matemáticas básicas" }]} />);

    expect(screen.getByRole("progressbar", { name: "Progreso de reconciliación" })).toHaveAttribute("aria-valuenow", "0");
    const candidate = screen.getByRole("button", { name: /1000001/i });
    fireEvent.click(candidate);
    expect(candidate).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("combobox", { name: "Asignatura del plan" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Nota de decisión" })).toBeRequired();
  });
});
