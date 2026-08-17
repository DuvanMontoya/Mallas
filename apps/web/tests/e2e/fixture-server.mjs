import { createServer } from "node:http";
import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const fixturePath = fileURLToPath(new URL("./fixtures/student-academic-overview.json", import.meta.url));
const academicOverview = readFileSync(fixturePath, "utf8");
const studentAnalytics = JSON.stringify({
  schema_version: "1.0",
  scope: "STUDENT",
  data_state: "PERSISTED_PUBLISHED_AUDIT",
  as_of: "2026-08-16T20:00:00Z",
  enrollment_id: "00000000-0000-4000-8000-000000000254",
  program_code: "2514",
  program_name: "Estadística",
  plan_code: "2514",
  revision_code: "2514-2026",
  snapshot: { status: "INCOMPLETE", engine_version: "audit-engine/1.0.0" },
  metrics: {
    credits: { required: 141, earned: 8, applied: 7, unapplied: 1, remaining: 134, progress_percent: 4 },
    requirements: { remaining_count: 2, unknown_count: 1, remaining: [{ code: "GRADUATION:FOREIGN_LANGUAGE_B1", purpose: "GRADUATION", status: "UNKNOWN", owner_course_code: null }] },
    critical_courses: [{ course_code: "2000001", state: "BLOCKED", requirement_codes: ["PREREQ:2000001"] }],
    trend: [{ captured_at: "2026-08-16T20:00:00Z", status: "INCOMPLETE", required_credits: 141, earned_credits: 8, applied_credits: 7, unapplied_credits: 1, progress_percent: 4, unknown_count: 1, engine_version: "audit-engine/1.0.0", result_hash: "fixture-analytics-hash", revision_hash: "fixture-revision-hash" }],
    scenarios: [{ name: "Ruta fixture", status: "ACTIVE", generated_at: "2026-08-16T19:00:00Z", planned_course_count: 2, required_credits: 141, applied_credits: 15, remaining_credits: 126, progress_percent: 10, unknown_count: 0, result_hash: "fixture-scenario-hash" }]
  },
  definitions: [{ key: "credits.applied", label: "Créditos aplicados", description: "Créditos derivados del resultado de auditoría.", source: "DegreeAuditResult.payload.overall.applied_credits", epistemic_status: "DERIVED", privacy: "PRIVATE_OR_AGGREGATED" }],
  warnings: []
});
const curriculumMapPath = fileURLToPath(new URL("./fixtures/curriculum-map.json", import.meta.url));
const curriculumMap = readFileSync(curriculumMapPath, "utf8");
const dependencyGraphPath = fileURLToPath(new URL("./fixtures/dependency-graph.json", import.meta.url));
const dependencyGraph = readFileSync(dependencyGraphPath, "utf8");
const dependencyGraphPayload = JSON.parse(dependencyGraph);
const offeringsPath = fileURLToPath(new URL("./fixtures/offerings.json", import.meta.url));
const offerings = readFileSync(offeringsPath, "utf8");
const scenariosPath = fileURLToPath(new URL("./fixtures/scenarios.json", import.meta.url));
const scenariosFixture = JSON.parse(readFileSync(scenariosPath, "utf8"));
const offeringsFixture = JSON.parse(offerings);
const academicTerms = JSON.stringify({
  items: [
    ...offeringsFixture.terms,
    {
      ...offeringsFixture.terms[0],
      id: "00000000-0000-4000-8000-000000000402",
      code: "2027-1S",
      starts_at: "2027-02-01T00:00:00Z",
      ends_at: "2027-06-30T23:59:59Z",
      status: "PLANNED",
      source: { ...offeringsFixture.terms[0].source, freshness: "UNKNOWN", retrieved_at: null, sha256: null }
    }
  ]
});
let scenarioState = scenariosFixture.items;
const optimizationState = new Map();
const notificationFixture = {
  id: "00000000-0000-4000-8000-000000000901",
  event_id: "00000000-0000-4000-8000-000000000902",
  event_type: "curriculum.revision.published",
  channel: "IN_APP",
  status: "SENT",
  title: "Cambio curricular publicado",
  body: "Se publicó una revisión curricular que puede requerir una revisión de tu cohorte académica.",
  locale: "es-CO",
  link_path: "/audit",
  created_at: "2026-08-16T20:00:00Z",
  delivered_at: "2026-08-16T20:00:01Z"
};
let notificationRead = false;
let notificationPreference = {
  event_type: "curriculum.revision.published",
  in_app_enabled: true,
  email_enabled: false,
  locale: "es-CO"
};

function resetNotificationCenter() {
  notificationRead = false;
  notificationPreference = {
    event_type: "curriculum.revision.published",
    in_app_enabled: true,
    email_enabled: false,
    locale: "es-CO"
  };
}

function notificationCollection() {
  return {
    items: [{ ...notificationFixture, read_at: notificationRead ? "2026-08-16T20:01:00Z" : null }],
    unread_count: notificationRead ? 0 : 1,
    next_cursor: null
  };
}
const authenticatedUser = JSON.stringify({
  id: 2514,
  email: "student.fixture@example.test",
  email_verified: true,
  roles: ["STUDENT", "EDITOR", "REVIEWER"],
  student_profile_id: "00000000-0000-4000-8000-000000000254",
});

const governanceProposal = {
  id: "00000000-0000-4000-8000-000000000701",
  proposal_key: "fixture:governance",
  title: "Revisión editorial de prueba",
  status: "DRAFT",
  base_revision_id: null,
  candidate_revision_id: "00000000-0000-4000-8000-000000000702",
  candidate_revision_code: "2514-2026",
  source_snapshot_id: "00000000-0000-4000-8000-000000000703",
  source_title: "Acuerdo archivado de prueba",
  content_fingerprint: "a".repeat(64),
  semantic_has_changes: true,
  created_by: "editor.fixture@example.test",
  updated_at: "2026-08-16T20:00:00Z",
  version: "2026-08-16T20:00:00Z",
  pending_candidates: 0,
  rationale: "Fuente archivada con diff explícito.",
  base_revision: null,
  candidate_revision: {
    id: "00000000-0000-4000-8000-000000000702",
    plan_code: "2514",
    revision_code: "2514-2026",
    status: "DRAFT",
    effective_from: "2026-01-01",
    effective_to: null,
    total_required_credits: 141,
    source_set_hash: "b".repeat(64),
    content_hash: "c".repeat(64),
    published_at: null,
    version: "2026-08-16T20:00:00Z"
  },
  source_snapshot: {
    id: "00000000-0000-4000-8000-000000000703",
    document_id: "00000000-0000-4000-8000-000000000704",
    document_title: "Acuerdo archivado de prueba",
    captured_at: "2026-08-16T19:00:00Z",
    sha256: "d".repeat(64),
    mime_type: "application/pdf",
    storage_key: "private/fixture-source.pdf",
    source_url: null,
    metadata: {},
    evidence_count: 1,
    version: "2026-08-16T19:00:00Z"
  },
  semantic_diff: { added: { courses: [{ code: "STAT000" }] }, removed: {}, changed: [], has_changes: true },
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
    evidence: [{ id: "00000000-0000-4000-8000-000000000707", reference: "d#page:1", snapshot_id: "00000000-0000-4000-8000-000000000703", snapshot_sha256: "d".repeat(64), locator: "page:1", page: 1, section: "", excerpt: "Evidence", annotation: "", source_title: "Acuerdo archivado de prueba", source_url: null }],
    version: "2026-08-16T19:00:00Z"
  }],
  candidates: [{ id: "00000000-0000-4000-8000-000000000708", entity: "courses", entity_key: "STAT000", operation: "ADD", before: null, after: { code: "STAT000" }, status: "ACCEPTED", epistemic_status: "INFERRED_PENDING_REVIEW", evidence: [], reviewed_by: "editor.fixture@example.test", reviewed_at: "2026-08-16T19:30:00Z", note: "Reviewed", version: "2026-08-16T19:30:00Z" }],
  reviews: [],
  publication: null,
  audit_events: []
};
const governanceInbox = {
  documents: [{ id: "00000000-0000-4000-8000-000000000704", issuer: "Universidad Nacional", document_type: "ACUERDO", number: "496", year: 2023, title: "Acuerdo archivado de prueba", publication_date: "2023-05-09", canonical_url: null, status: "ACTIVE", metadata: {}, snapshot_count: 1, version: "2026-08-16T19:00:00Z" }],
  snapshots: [{ id: "00000000-0000-4000-8000-000000000703", document_id: "00000000-0000-4000-8000-000000000704", document_title: "Acuerdo archivado de prueba", captured_at: "2026-08-16T19:00:00Z", sha256: "d".repeat(64), mime_type: "application/pdf", storage_key: "private/fixture-source.pdf", source_url: null, metadata: {}, evidence_count: 1, version: "2026-08-16T19:00:00Z" }],
  proposals: [governanceProposal],
  workflow: ["DISCOVERED", "SNAPSHOT", "EXTRACTED", "DRAFT", "VALIDATED", "IN_REVIEW", "APPROVED", "PUBLISHED"]
};

function resetGovernanceProposal() {
  governanceProposal.status = "DRAFT";
  governanceProposal.version = "2026-08-16T20:00:00Z";
  governanceProposal.updated_at = governanceProposal.version;
  governanceProposal.candidate_revision.status = "DRAFT";
  governanceProposal.candidate_revision.version = governanceProposal.version;
  governanceProposal.candidate_revision.published_at = null;
  governanceProposal.reviews = [];
  governanceProposal.publication = null;
  governanceProposal.audit_events = [];
}

function readJson(request) {
  return new Promise((resolve) => {
    let body = "";
    request.on("data", (chunk) => { body += chunk; });
    request.on("end", () => {
      try { resolve(body ? JSON.parse(body) : {}); } catch { resolve({}); }
    });
  });
}

function responseJson(response, payload, status = 200, headers = {}) {
  response.writeHead(status, { "Content-Type": "application/json; charset=utf-8", ...headers });
  response.end(JSON.stringify(payload));
}

function scenarioById(id) {
  return scenarioState.find((scenario) => scenario.id === id);
}

function scenarioTerm(codeOrId) {
  return offeringsFixture.terms.find((term) => term.id === codeOrId || term.code === codeOrId)
    ?? JSON.parse(academicTerms).items.find((term) => term.id === codeOrId || term.code === codeOrId);
}

function emptyValidation() {
  return { state: "VALID", courses: [], warnings: [] };
}

const server = createServer(async (request, response) => {
  response.setHeader("Content-Type", "application/json; charset=utf-8");
  if (request.url === "/health") {
    response.writeHead(200);
    response.end(JSON.stringify({ status: "ok" }));
    return;
  }
  if (request.url?.startsWith("/api/v1/auth/me")) {
    resetNotificationCenter();
    response.writeHead(200);
    response.end(authenticatedUser);
    return;
  }
  if (request.url?.startsWith("/api/v1/auth/csrf")) {
    responseJson(response, { csrf_token: "fixture-csrf-token" });
    return;
  }
  if (request.url?.startsWith("/api/v1/analytics/student")) {
    responseJson(response, JSON.parse(studentAnalytics));
    return;
  }
  if (request.url?.startsWith("/api/v1/notifications")) {
    const url = new URL(request.url, "http://127.0.0.1:8010");
    if (url.pathname === "/api/v1/notifications" && request.method === "GET") {
      responseJson(response, notificationCollection());
      return;
    }
    if (url.pathname === "/api/v1/notifications/read-all" && request.method === "POST") {
      notificationRead = true;
      responseJson(response, { marked_read: 1 });
      return;
    }
    if (url.pathname.endsWith("/read") && request.method === "POST") {
      notificationRead = true;
      responseJson(response, { ...notificationFixture, read_at: "2026-08-16T20:01:00Z" });
      return;
    }
    if (url.pathname === "/api/v1/notifications/preferences" && request.method === "GET") {
      responseJson(response, { items: [notificationPreference] });
      return;
    }
    if (url.pathname.startsWith("/api/v1/notifications/preferences/") && request.method === "PUT") {
      const body = await readJson(request);
      notificationPreference = { ...notificationPreference, ...body };
      responseJson(response, notificationPreference);
      return;
    }
  }
  if (request.url?.startsWith("/api/v1/governance/inbox")) {
    resetGovernanceProposal();
    responseJson(response, governanceInbox, 200, { ETag: '"governance-fixture-hash"' });
    return;
  }
  if (request.url?.startsWith("/api/v1/governance/proposals/")) {
    const url = new URL(request.url, "http://127.0.0.1:8010");
    if (url.pathname.endsWith("/submit") && request.method === "POST") {
      governanceProposal.status = "IN_REVIEW";
      governanceProposal.version = "2026-08-16T20:01:00Z";
      governanceProposal.updated_at = governanceProposal.version;
      responseJson(response, governanceProposal, 200, { ETag: `"${governanceProposal.version}"` });
      return;
    }
    if (url.pathname.endsWith("/review") && request.method === "POST") {
      const body = await readJson(request);
      governanceProposal.status = body.decision === "APPROVE" ? "APPROVED" : body.decision === "REJECT" ? "REJECTED" : "DRAFT";
      governanceProposal.version = "2026-08-16T20:02:00Z";
      governanceProposal.updated_at = governanceProposal.version;
      responseJson(response, governanceProposal, 200, { ETag: `"${governanceProposal.version}"` });
      return;
    }
    if (url.pathname.endsWith("/publish") && request.method === "POST") {
      governanceProposal.status = "PUBLISHED";
      governanceProposal.version = "2026-08-16T20:03:00Z";
      governanceProposal.updated_at = governanceProposal.version;
      governanceProposal.publication = { id: randomUUID(), revision_id: governanceProposal.candidate_revision_id, published_by: "reviewer.fixture@example.test", published_at: governanceProposal.version, content_hash: governanceProposal.candidate_revision.content_hash, source_set_hash: governanceProposal.candidate_revision.source_set_hash, validation_report: governanceProposal.validation_report, confirmation: "Fixture confirmation." };
      responseJson(response, governanceProposal, 200, { ETag: `"${governanceProposal.version}"` });
      return;
    }
    if (request.method === "GET") {
      resetGovernanceProposal();
      responseJson(response, governanceProposal, 200, { ETag: `"${governanceProposal.version}"` });
      return;
    }
  }
  if (request.url?.startsWith("/api/v1/academic-terms")) {
    responseJson(response, JSON.parse(academicTerms), 200, { ETag: '"terms-fixture-hash"' });
    return;
  }
  if (request.url?.startsWith("/api/v1/scenarios/compare")) {
    const url = new URL(request.url, "http://127.0.0.1:8010");
    const left = scenarioById(url.searchParams.get("left_id"));
    const right = scenarioById(url.searchParams.get("right_id"));
    if (!left || !right) { responseJson(response, { code: "NOT_FOUND", detail: "Scenario not found" }, 404); return; }
    const leftMap = new Map(left.planned_courses.map((course) => [course.course_code, course]));
    const rightMap = new Map(right.planned_courses.map((course) => [course.course_code, course]));
    const added = [...rightMap.keys()].filter((code) => !leftMap.has(code));
    const removed = [...leftMap.keys()].filter((code) => !rightMap.has(code));
    const moved = [...rightMap.keys()].filter((code) => leftMap.has(code) && leftMap.get(code).term_id !== rightMap.get(code).term_id);
    responseJson(response, {
      left: { id: left.id, name: left.name, version: left.version },
      right: { id: right.id, name: right.name, version: right.version },
      added: added.map((course_code) => ({ course_code, term_code: rightMap.get(course_code).term_code })),
      removed: removed.map((course_code) => ({ course_code, term_code: leftMap.get(course_code).term_code })),
      moved: moved.map((course_code) => ({ course_code, from_term: leftMap.get(course_code).term_code, to_term: rightMap.get(course_code).term_code })),
      unchanged: [...leftMap.keys()].filter((code) => rightMap.has(code) && !moved.includes(code))
    });
    return;
  }
  if (request.url?.startsWith("/api/v1/optimization-runs/")) {
    const url = new URL(request.url, "http://127.0.0.1:8010");
    const pathParts = url.pathname.split("/").filter(Boolean);
    const runId = pathParts[3];
    const run = optimizationState.get(runId);
    if (!run) { responseJson(response, { code: "NOT_FOUND", detail: "Optimization run not found" }, 404); return; }
    if (url.pathname.endsWith("/cancel") && request.method === "POST") {
      run.status = "UNKNOWN";
      run.cancel_requested_at = new Date().toISOString();
      run.completed_at = run.cancel_requested_at;
      run.explanation = { ...run.explanation, assumptions: [...run.explanation.assumptions, "CANCELLED_BY_USER"] };
      responseJson(response, run, 200);
      return;
    }
    if (request.method === "GET") {
      responseJson(response, run, 200);
      return;
    }
  }
  if (request.url?.startsWith("/api/v1/scenarios/") && request.url.includes("/optimization-runs")) {
    const url = new URL(request.url, "http://127.0.0.1:8010");
    const pathParts = url.pathname.split("/").filter(Boolean);
    const scenarioId = pathParts[3];
    const scenario = scenarioById(scenarioId);
    if (!scenario) { responseJson(response, { code: "NOT_FOUND", detail: "Scenario not found" }, 404); return; }
    if (request.method === "GET") {
      responseJson(response, { items: [...optimizationState.values()].filter((run) => run.scenario_id === scenarioId) }, 200);
      return;
    }
    if (request.method === "POST") {
      const body = await readJson(request);
      const now = new Date().toISOString();
      const run = {
        id: randomUUID(),
        scenario_id: scenarioId,
        input_hash: "fixture-optimization-input-hash",
        output_hash: "fixture-optimization-output-hash",
        solver_version: "cp-sat-planner/1.0.0",
        status: "OPTIMAL",
        objective_values: [
          { name: "last_term", value: 1 },
          { name: "unknown_offerings", value: 1 },
          { name: "credit_balance", value: 0 },
          { name: "preference_penalty", value: 0 }
        ],
        solution: {
          selected_courses: [
            { course_code: "1000003", term_code: "2027-1S", credits: 4, selected_section_id: null },
            { course_code: "2000001", term_code: "2026-2S", credits: 4, selected_section_id: null }
          ]
        },
        explanation: {
          explanations: [
            { course_code: "1000003", term_code: "2027-1S", reason: "La solución respeta las restricciones conocidas." },
            { course_code: "2000001", term_code: "2026-2S", reason: "El período reduce el último término de la ruta." }
          ],
          conflicts: [],
          assumptions: [body.unknown_offering_policy === "REQUIRE_OFFERED" ? "UNKNOWN_OFFERINGS_REJECTED" : "UNKNOWN_OFFERINGS_ALLOWED"]
        },
        time_limit_seconds: body.time_limit_seconds ?? 30,
        created_at: now,
        started_at: now,
        cancel_requested_at: null,
        completed_at: now
      };
      optimizationState.set(run.id, run);
      responseJson(response, run, 202);
      return;
    }
  }
  if (request.url?.startsWith("/api/v1/scenarios")) {
    const url = new URL(request.url, "http://127.0.0.1:8010");
    const path = url.pathname;
    if (path === "/api/v1/scenarios" && request.method === "GET") {
      const includeArchived = url.searchParams.get("include_archived") === "true";
      responseJson(response, { items: scenarioState.filter((scenario) => includeArchived || scenario.status === "ACTIVE") }, 200, { ETag: '"scenarios-fixture-hash"' });
      return;
    }
    const body = await readJson(request);
    if (path === "/api/v1/scenarios" && request.method === "POST") {
      const scenario = structuredClone(scenarioState[0]);
      scenario.id = randomUUID();
      scenario.name = body.name ?? "Nuevo escenario";
      scenario.version = 1;
      scenario.planned_courses = [];
      scenario.validation = emptyValidation();
      scenario.share_token = null;
      scenario.sharing_enabled = false;
      scenario.target_term_id = body.target_term_id ?? "00000000-0000-4000-8000-000000000401";
      scenario.target_term_code = scenarioTerm(scenario.target_term_id)?.code ?? "2026-2S";
      scenarioState.push(scenario);
      responseJson(response, scenario, 201, { ETag: '"1"' });
      return;
    }
    const scenarioId = path.split("/")[4];
    const scenario = scenarioById(scenarioId);
    if (!scenario) { responseJson(response, { code: "NOT_FOUND", detail: "Scenario not found" }, 404); return; }
    if (path.endsWith("/duplicate") && request.method === "POST") {
      const duplicate = structuredClone(scenario);
      duplicate.id = randomUUID();
      duplicate.name = body.name ?? `${scenario.name} — copia`;
      duplicate.version = 1;
      duplicate.share_token = null;
      duplicate.sharing_enabled = false;
      duplicate.planned_courses = duplicate.planned_courses.map((course) => ({ ...course, id: randomUUID(), is_locked: false }));
      scenarioState.push(duplicate);
      responseJson(response, duplicate, 201, { ETag: '"1"' });
      return;
    }
    if (path.endsWith("/archive") && request.method === "POST") {
      scenario.status = "ARCHIVED";
      scenario.version += 1;
      responseJson(response, scenario, 200, { ETag: `"${scenario.version}"` });
      return;
    }
    if (path === `/api/v1/scenarios/${scenarioId}` && request.method === "PATCH") {
      if (body.name) scenario.name = body.name;
      if (body.status) scenario.status = body.status;
      if (typeof body.sharing_enabled === "boolean") {
        scenario.sharing_enabled = body.sharing_enabled;
        scenario.share_token = body.sharing_enabled ? (scenario.share_token ?? randomUUID()) : scenario.share_token;
        if (!body.sharing_enabled) scenario.share_token = null;
      }
      scenario.version += 1;
      responseJson(response, scenario, 200, { ETag: `"${scenario.version}"` });
      return;
    }
    if (path === `/api/v1/scenarios/${scenarioId}` && request.method === "GET") {
      responseJson(response, scenario, 200, { ETag: `"${scenario.version}"` });
      return;
    }
    const courseIndex = path.indexOf("/courses/");
    if (courseIndex >= 0) {
      const courseId = path.slice(courseIndex + "/courses/".length);
      const course = scenario.planned_courses.find((item) => item.id === courseId);
      if (!course) { responseJson(response, { code: "NOT_FOUND", detail: "Planned course not found" }, 404); return; }
      if (request.method === "PATCH") {
        if (body.term_id) { course.term_id = body.term_id; course.term_code = scenarioTerm(body.term_id)?.code ?? body.term_id; }
        if (typeof body.is_locked === "boolean") course.is_locked = body.is_locked;
        scenario.version += 1;
        responseJson(response, scenario, 200, { ETag: `"${scenario.version}"` });
        return;
      }
      if (request.method === "DELETE") {
        scenario.planned_courses = scenario.planned_courses.filter((item) => item.id !== courseId);
        scenario.version += 1;
        responseJson(response, scenario, 200, { ETag: `"${scenario.version}"` });
        return;
      }
    }
    if (path.endsWith("/courses") && request.method === "POST") {
      const map = JSON.parse(curriculumMap);
      const option = map.courses.find((item) => item.id === body.course_version_id) ?? map.courses[0];
      const term = scenarioTerm(body.term_id) ?? JSON.parse(academicTerms).items[0];
      scenario.planned_courses.push({
        id: randomUUID(),
        course_version_id: option.id,
        course_code: option.code,
        course_name: option.name,
        credits: option.credits,
        term_id: term.id,
        term_code: term.code,
        section_id: null,
        section_group_code: null,
        priority: body.priority ?? 0,
        source: "USER",
        notes: body.notes ?? "",
        is_locked: false
      });
      scenario.version += 1;
      responseJson(response, scenario, 200, { ETag: `"${scenario.version}"` });
      return;
    }
  }
  if (request.url?.startsWith("/api/v1/academic-overview")) {
    response.writeHead(200, { ETag: '"result-hash-2514"' });
    response.end(academicOverview);
    return;
  }
  if (request.url?.startsWith("/api/v1/curriculum-map")) {
    response.writeHead(200, { ETag: '"map-fixture-hash-2514"' });
    response.end(curriculumMap);
    return;
  }
  if (request.url?.startsWith("/api/v1/dependency-graph")) {
    const url = new URL(request.url, "http://127.0.0.1:8010");
    const selected = url.searchParams.get("selected");
    const selectedNode = dependencyGraphPayload.nodes.find((node) => node.course_code === selected);
    const payload = selected && dependencyGraphPayload.focus && selected !== dependencyGraphPayload.focus.course_code
      ? { ...dependencyGraphPayload, focus: { ...dependencyGraphPayload.focus, course_code: selected, course_name: selectedNode?.label ?? selected } }
      : dependencyGraphPayload;
    response.writeHead(200, { ETag: '"graph-fixture-hash-2514"' });
    response.end(JSON.stringify(payload));
    return;
  }
  if (request.url?.startsWith("/api/v1/offerings/schedule")) {
    const url = new URL(request.url, "http://127.0.0.1:8010");
    const sectionIds = (url.searchParams.get("section_ids") ?? "").split(",").filter(Boolean);
    response.writeHead(200);
    response.end(JSON.stringify({
      term_code: url.searchParams.get("term_code") ?? "2026-2S",
      section_ids: sectionIds,
      state: sectionIds.length > 1 ? "CONFLICT" : "SCHEDULABLE",
      unknown_reasons: [],
      conflicts: sectionIds.length > 1 ? [{
        left_section_id: sectionIds[0],
        right_section_id: sectionIds[1],
        left_meeting_id: "00000000-0000-4000-8000-000000000431",
        right_meeting_id: "00000000-0000-4000-8000-000000000432",
        occurrence_date: "2026-08-03",
        starts_at_utc: "2026-08-03T14:00:00Z",
        ends_at_utc: "2026-08-03T15:00:00Z",
        reason: "OVERLAP"
      }] : []
    }));
    return;
  }
  if (request.url?.startsWith("/api/v1/offerings")) {
    response.writeHead(200, { ETag: '"offerings-fixture-hash-2514"' });
    response.end(offerings);
    return;
  }
  response.writeHead(404);
  response.end(JSON.stringify({ code: "NOT_FOUND", detail: "Fixture route not found" }));
});

server.listen(8010, "127.0.0.1");
