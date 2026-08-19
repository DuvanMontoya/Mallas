import {
  createApiClient,
  type ApiComponents,
  type ApiPaths,
} from "@curriculum-navigator/api-client";

export type UserView = ApiComponents["schemas"]["UserView"];
export type PersonProfileView = ApiComponents["schemas"]["PersonProfileView"];
export type PersonProfileUpdatePayload = ApiComponents["schemas"]["PersonProfileUpdatePayload"];
export type PersonProfileExportView = ApiComponents["schemas"]["PersonProfileExportView"];
export type StudentOnboardingView = ApiComponents["schemas"]["StudentOnboardingView"];
export type StudentOnboardingPayload = ApiComponents["schemas"]["StudentOnboardingPayload"];
export type ProblemDetails = ApiComponents["schemas"]["ProblemDetails"];
export type AcademicOverview = ApiComponents["schemas"]["AcademicOverviewView"];
export type CurriculumMap = ApiComponents["schemas"]["CurriculumMapView"];
export type DependencyGraph = ApiComponents["schemas"]["DependencyGraphView"];
export type AcademicTerm = ApiComponents["schemas"]["AcademicTermView"];
export type OfferingsReadModel = ApiComponents["schemas"]["OfferingsView"];
export type ScheduleEvaluation = ApiComponents["schemas"]["ScheduleEvaluationView"];
export type NotificationView = ApiComponents["schemas"]["NotificationView"];
export type NotificationCollection = ApiComponents["schemas"]["NotificationCollectionView"];
export type NotificationPreferenceView = ApiComponents["schemas"]["NotificationPreferenceView"];
export type NotificationPreferenceCollection = ApiComponents["schemas"]["NotificationPreferenceCollectionView"];
export type NotificationPreferencePayload = ApiComponents["schemas"]["NotificationPreferencePayload"];
export type AnalyticsDefinition = ApiComponents["schemas"]["AnalyticsDefinitionView"];
export type StudentAnalytics = ApiComponents["schemas"]["StudentAnalyticsView"];
export type InstitutionalAnalytics = ApiComponents["schemas"]["InstitutionalAnalyticsView"];
export type { ApiComponents };

export type SessionState = "authenticated" | "anonymous" | "unavailable";

export interface SessionSnapshot {
  state: SessionState;
  user: UserView | null;
  correlationId: string | null;
}

export interface ApiFailure {
  problem: ProblemDetails | null;
  correlationId: string | null;
  unavailable: boolean;
}

const api = createApiClient();

function correlationId(response: Response | undefined): string | null {
  return response?.headers.get("X-Request-ID") ?? null;
}

function isProblemDetails(value: unknown): value is ProblemDetails {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<ProblemDetails>;
  return typeof candidate.code === "string" && typeof candidate.detail === "string";
}

export function problemFromUnknown(value: unknown): ProblemDetails | null {
  return isProblemDetails(value) ? value : null;
}

export function problemMessage(problem: ProblemDetails | null, fallback: string): string {
  return problem?.detail || fallback;
}

export async function getSessionSnapshot(headers?: HeadersInit): Promise<SessionSnapshot> {
  try {
    const result = await api.GET("/api/v1/auth/me", { headers });
    const requestCorrelationId = correlationId(result.response);
    if (result.response.status === 401) {
      return { state: "anonymous", user: null, correlationId: requestCorrelationId };
    }
    if (result.data) {
      return { state: "authenticated", user: result.data, correlationId: requestCorrelationId };
    }
    return { state: "unavailable", user: null, correlationId: requestCorrelationId };
  } catch {
    return { state: "unavailable", user: null, correlationId: null };
  }
}

export async function getStudentOnboarding(headers?: HeadersInit): Promise<{
  data: StudentOnboardingView | null;
  failure: ApiFailure | null;
}> {
  try {
    const result = await api.GET("/api/v1/onboarding", { headers });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function updateStudentOnboarding(
  body: StudentOnboardingPayload,
  version: string,
): Promise<{ data: StudentOnboardingView | null; failure: ApiFailure | null }> {
  try {
    const result = await api.PATCH("/api/v1/onboarding", {
      body,
      headers: await mutationHeaders({ ifMatch: `"${version}"` }),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getPersonProfile(headers?: HeadersInit): Promise<{
  data: PersonProfileView | null;
  failure: ApiFailure | null;
}> {
  try {
    const result = await api.GET("/api/v1/auth/profile", { headers });
    if (result.data) return { data: result.data, failure: null };
    return {
      data: null,
      failure: {
        problem: problemFromUnknown(result.error),
        correlationId: correlationId(result.response),
        unavailable: false,
      },
    };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function updatePersonProfile(
  body: PersonProfileUpdatePayload,
  version: string,
): Promise<{ data: PersonProfileView | null; failure: ApiFailure | null }> {
  try {
    const csrfToken = await getCsrfToken();
    const result = await api.PATCH("/api/v1/auth/profile", {
      body,
      headers: { "X-CSRFToken": csrfToken, "If-Match": `"${version}"` },
    });
    if (result.data) return { data: result.data, failure: null };
    return {
      data: null,
      failure: {
        problem: problemFromUnknown(result.error),
        correlationId: correlationId(result.response),
        unavailable: false,
      },
    };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function exportPersonProfile(): Promise<{
  data: PersonProfileExportView | null;
  failure: ApiFailure | null;
}> {
  try {
    const result = await api.GET("/api/v1/auth/profile/export");
    if (result.data) return { data: result.data, failure: null };
    return {
      data: null,
      failure: {
        problem: problemFromUnknown(result.error),
        correlationId: correlationId(result.response),
        unavailable: false,
      },
    };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getCsrfToken(): Promise<string> {
  const result = await api.GET("/api/v1/auth/csrf");
  if (!result.data) {
    throw new Error(problemMessage(problemFromUnknown(result.error), "CSRF token unavailable."));
  }
  return result.data.csrf_token;
}

export async function signIn(
  email: string,
  password: string,
): Promise<{ user: UserView } | { failure: ApiFailure }> {
  try {
    const csrfToken = await getCsrfToken();
    const result = await api.POST("/api/v1/auth/login", {
      body: { email, password },
      headers: { "X-CSRFToken": csrfToken },
    });
    if (result.data) return { user: result.data.user };
    return {
      failure: {
        problem: problemFromUnknown(result.error),
        correlationId: correlationId(result.response),
        unavailable: false,
      },
    };
  } catch {
    return { failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function signOut(): Promise<ApiFailure | null> {
  try {
    const csrfToken = await getCsrfToken();
    const result = await api.POST("/api/v1/auth/logout", {
      headers: { "X-CSRFToken": csrfToken },
    });
    if (!result.error) return null;
    return {
      problem: problemFromUnknown(result.error),
      correlationId: correlationId(result.response),
      unavailable: false,
    };
  } catch {
    return { problem: null, correlationId: null, unavailable: true };
  }
}

export async function changeInitialPassword(
  currentPassword: string,
  newPassword: string,
): Promise<ApiFailure | null> {
  try {
    const csrfToken = await getCsrfToken();
    const result = await api.POST("/api/v1/auth/password/change", {
      body: { current_password: currentPassword, new_password: newPassword },
      headers: { "X-CSRFToken": csrfToken },
    });
    if (result.data) return null;
    return {
      problem: problemFromUnknown(result.error),
      correlationId: correlationId(result.response),
      unavailable: false,
    };
  } catch {
    return { problem: null, correlationId: null, unavailable: true };
  }
}

export async function getNotifications(options?: {
  unreadOnly?: boolean;
  limit?: number;
  before?: string;
  headers?: HeadersInit;
}): Promise<{ data: NotificationCollection | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/notifications", {
      headers: options?.headers,
      params: {
        query: {
          unread_only: options?.unreadOnly,
          limit: options?.limit,
          before: options?.before,
        },
      },
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function markNotificationRead(
  deliveryId: string,
  options?: ScenarioMutationOptions,
): Promise<{ data: NotificationView | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/notifications/{delivery_id}/read", {
      params: { path: { delivery_id: deliveryId } },
      headers: await mutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function markAllNotificationsRead(
  options?: ScenarioMutationOptions,
): Promise<{ data: ApiComponents["schemas"]["NotificationReadAllView"] | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/notifications/read-all", {
      headers: await mutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getNotificationPreferences(options?: {
  headers?: HeadersInit;
}): Promise<{ data: NotificationPreferenceCollection | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/notifications/preferences", { headers: options?.headers });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function updateNotificationPreference(
  eventType: string,
  body: NotificationPreferencePayload,
  options?: ScenarioMutationOptions,
): Promise<{ data: NotificationPreferenceView | null; failure: ApiFailure | null }> {
  try {
    const result = await api.PUT("/api/v1/notifications/preferences/{event_type}", {
      params: { path: { event_type: eventType } },
      body,
      headers: await mutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getAcademicOverview(options?: {
  enrollmentId?: string;
  headers?: HeadersInit;
}): Promise<{ data: AcademicOverview | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/academic-overview", {
      headers: options?.headers,
      params: {
        query: options?.enrollmentId ? { enrollment_id: options.enrollmentId } : undefined,
      },
    });
    if (result.data) return { data: result.data, failure: null };
    return {
      data: null,
      failure: {
        problem: problemFromUnknown(result.error),
        correlationId: correlationId(result.response),
        unavailable: false,
      },
    };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getAnalyticsDefinitions(options?: {
  headers?: HeadersInit;
}): Promise<{ data: ApiComponents["schemas"]["AnalyticsDefinitionsView"] | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/analytics/definitions", { headers: options?.headers });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getStudentAnalytics(options?: {
  enrollmentId?: string;
  headers?: HeadersInit;
}): Promise<{ data: StudentAnalytics | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/analytics/student", {
      headers: options?.headers,
      params: { query: options?.enrollmentId ? { enrollment_id: options.enrollmentId } : undefined },
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getInstitutionalAnalytics(options: {
  institutionId: string;
  programId?: string;
  termCode?: string;
  minCellSize?: number;
  headers?: HeadersInit;
}): Promise<{ data: InstitutionalAnalytics | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/analytics/institutional", {
      headers: options.headers,
      params: {
        query: {
          institution_id: options.institutionId,
          program_id: options.programId,
          term_code: options.termCode,
          min_cell_size: options.minCellSize,
        },
      },
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getCurriculumMap(options?: {
  planCode?: string;
  revisionId?: string;
  enrollmentId?: string;
  termCode?: string;
  headers?: HeadersInit;
}): Promise<{ data: CurriculumMap | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/curriculum-map", {
      headers: options?.headers,
      params: {
        query: {
          plan_code: options?.planCode,
          revision_id: options?.revisionId,
          enrollment_id: options?.enrollmentId,
          term_code: options?.termCode,
        },
      },
    });
    if (result.data) return { data: result.data, failure: null };
    return {
      data: null,
      failure: {
        problem: problemFromUnknown(result.error),
        correlationId: correlationId(result.response),
        unavailable: false,
      },
    };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getDependencyGraph(options?: {
  planCode?: string;
  revisionId?: string;
  enrollmentId?: string;
  termCode?: string;
  selected?: string;
  headers?: HeadersInit;
}): Promise<{ data: DependencyGraph | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/dependency-graph", {
      headers: options?.headers,
      params: {
        query: {
          plan_code: options?.planCode,
          revision_id: options?.revisionId,
          enrollment_id: options?.enrollmentId,
          term_code: options?.termCode,
          selected: options?.selected,
        },
      },
    });
    if (result.data) return { data: result.data, failure: null };
    return {
      data: null,
      failure: {
        problem: problemFromUnknown(result.error),
        correlationId: correlationId(result.response),
        unavailable: false,
      },
    };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getAcademicTerms(options?: {
  institutionId?: string;
  campusCode?: string;
  enrollmentId?: string;
  headers?: HeadersInit;
}): Promise<{ data: ApiComponents["schemas"]["AcademicTermCollectionView"] | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/academic-terms", {
      headers: options?.headers,
      params: {
        query: {
          institution_id: options?.institutionId,
          campus_code: options?.campusCode,
          enrollment_id: options?.enrollmentId,
        },
      },
    });
    if (result.data) return { data: result.data, failure: null };
    return {
      data: null,
      failure: {
        problem: problemFromUnknown(result.error),
        correlationId: correlationId(result.response),
        unavailable: false,
      },
    };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getOfferings(options?: {
  termCode?: string;
  courseCode?: string;
  status?: string;
  enrollmentId?: string;
  headers?: HeadersInit;
}): Promise<{ data: OfferingsReadModel | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/offerings", {
      headers: options?.headers,
      params: {
        query: {
          term_code: options?.termCode,
          course_code: options?.courseCode,
          status: options?.status,
          enrollment_id: options?.enrollmentId,
        },
      },
    });
    if (result.data) return { data: result.data, failure: null };
    return {
      data: null,
      failure: {
        problem: problemFromUnknown(result.error),
        correlationId: correlationId(result.response),
        unavailable: false,
      },
    };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getOfferingSchedule(options: {
  termCode: string;
  sectionIds: string[];
  headers?: HeadersInit;
}): Promise<{ data: ScheduleEvaluation | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/offerings/schedule", {
      headers: options.headers,
      params: {
        query: {
          term_code: options.termCode,
          section_ids: options.sectionIds.join(","),
        },
      },
    });
    if (result.data) return { data: result.data, failure: null };
    return {
      data: null,
      failure: {
        problem: problemFromUnknown(result.error),
        correlationId: correlationId(result.response),
        unavailable: false,
      },
    };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export type PlanningScenario = ApiComponents["schemas"]["ScenarioView"];
export type ScenarioCompare = ApiComponents["schemas"]["ScenarioCompareView"];
export type PlannedCourse = ApiComponents["schemas"]["PlannedCourseView"];
export type ScenarioCreatePayload = ApiComponents["schemas"]["ScenarioCreatePayload"];
export type ScenarioPatchPayload = ApiComponents["schemas"]["ScenarioPatchPayload"];
export type PlannedCourseCreatePayload = ApiComponents["schemas"]["PlannedCourseCreatePayload"];
export type PlannedCoursePatchPayload = ApiComponents["schemas"]["PlannedCoursePatchPayload"];
export type OptimizationRun = ApiComponents["schemas"]["OptimizationRunView"];
export type OptimizationRequestPayload = ApiComponents["schemas"]["OptimizationRequestPayload"];
export type SourceInbox = ApiComponents["schemas"]["SourceInboxView"];
export type GovernanceProposal = ApiComponents["schemas"]["ProposalDetailView"];
export type GovernanceReviewPayload = ApiComponents["schemas"]["ReviewPayload"];
export type GovernanceCandidateReviewPayload = ApiComponents["schemas"]["CandidateReviewPayload"];
export type GovernanceCandidate = ApiComponents["schemas"]["GovernanceCandidateView"];
export type GovernanceBulkCandidatePayload = ApiComponents["schemas"]["BulkCandidatePayload"];
export type GovernanceBulkPreview = ApiComponents["schemas"]["BulkPreviewView"];
export type GovernanceRequirement = ApiComponents["schemas"]["GovernanceRequirementView"];
export type GovernancePublicationImpact = ApiComponents["schemas"]["PublicationImpactView"];
export type HistoryAttempt = ApiComponents["schemas"]["AttemptView"];
export type HistoryAttemptPage = ApiComponents["schemas"]["AttemptPage"];
export type HistoryAttemptCreatePayload = ApiComponents["schemas"]["ManualAttemptPayload"];
export type HistoryAttemptPatchPayload = ApiComponents["schemas"]["AttemptPatchPayload"];
export type HistoryImportPreview = ApiComponents["schemas"]["ImportPreviewView"];
export type HistoryImportCandidate = ApiComponents["schemas"]["CandidateView"];
export type HistoryImportResolutionPayload = ApiComponents["schemas"]["ResolvePayload"];
export type HistoryImportApplyResult = ApiComponents["schemas"]["ApplyView"];

type ScenarioMutationOptions = {
  csrfToken?: string;
  ifMatch?: string;
};

async function mutationHeaders(options: ScenarioMutationOptions = {}): Promise<HeadersInit> {
  const csrfToken = options.csrfToken ?? (await getCsrfToken());
  return {
    "X-CSRFToken": csrfToken,
    ...(options.ifMatch ? { "If-Match": options.ifMatch } : {}),
  };
}

function failureFromResult(result: { error?: unknown; response?: Response }): ApiFailure {
  return {
    problem: problemFromUnknown(result.error),
    correlationId: correlationId(result.response),
    unavailable: false,
  };
}

export async function getHistoryAttempts(options: {
  enrollmentId: string;
  limit?: number;
  offset?: number;
  cursor?: string;
  status?: string;
  sort?: "term" | "course" | "status";
  headers?: HeadersInit;
}): Promise<{ data: HistoryAttemptPage | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/history/attempts", {
      headers: options.headers,
      params: {
        query: {
          enrollment_id: options.enrollmentId,
          limit: options.limit,
          offset: options.offset,
          cursor: options.cursor,
          status: options.status,
          sort: options.sort,
        },
      },
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export type HistoryContext = ApiComponents["schemas"]["HistoryContextView"];

export async function getHistoryContext(options?: {
  headers?: HeadersInit;
}): Promise<{ data: HistoryContext | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/history/context", { headers: options?.headers });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function createHistoryAttempt(
  body: HistoryAttemptCreatePayload,
  options?: ScenarioMutationOptions,
): Promise<{ data: HistoryAttempt | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/history/attempts", {
      body,
      headers: await mutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function updateHistoryAttempt(
  attemptId: string,
  body: HistoryAttemptPatchPayload,
  options: ScenarioMutationOptions,
): Promise<{ data: HistoryAttempt | null; failure: ApiFailure | null }> {
  try {
    const result = await api.PATCH("/api/v1/history/attempts/{attempt_id}", {
      params: { path: { attempt_id: attemptId } },
      body,
      headers: await mutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function annulHistoryAttempt(
  attemptId: string,
  options: ScenarioMutationOptions,
): Promise<{ data: HistoryAttempt | null; failure: ApiFailure | null }> {
  try {
    const result = await api.DELETE("/api/v1/history/attempts/{attempt_id}", {
      params: { path: { attempt_id: attemptId } },
      headers: await mutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getHistoryImport(
  batchId: string,
  options?: { headers?: HeadersInit },
): Promise<{ data: HistoryImportPreview | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/history/imports/{batch_id}", {
      params: { path: { batch_id: batchId } },
      headers: options?.headers,
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function uploadHistoryImport(
  enrollmentId: string,
  file: File,
  idempotencyKey: string,
): Promise<{ data: HistoryImportPreview | null; failure: ApiFailure | null }> {
  try {
    const body = new FormData();
    body.append("enrollment_id", enrollmentId);
    body.append("file", file);
    const response = await fetch("/api/v1/history/imports", {
      method: "POST",
      credentials: "include",
      headers: {
        ...(await mutationHeaders()),
        "Idempotency-Key": idempotencyKey,
      },
      body,
    });
    const payload: unknown = await response.json().catch(() => null);
    if (response.ok) return { data: payload as HistoryImportPreview, failure: null };
    return {
      data: null,
      failure: {
        problem: problemFromUnknown(payload),
        correlationId: correlationId(response),
        unavailable: false,
      },
    };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function resolveHistoryImportCandidate(
  batchId: string,
  candidateId: string,
  body: HistoryImportResolutionPayload,
  options: ScenarioMutationOptions,
): Promise<{ data: HistoryImportCandidate | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST(
      "/api/v1/history/imports/{batch_id}/candidates/{candidate_id}/resolve",
      {
        params: { path: { batch_id: batchId, candidate_id: candidateId } },
        body,
        headers: await mutationHeaders(options),
      },
    );
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function confirmHistoryImport(
  batchId: string,
  options?: ScenarioMutationOptions,
): Promise<{ data: HistoryImportApplyResult | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/history/imports/{batch_id}/confirm", {
      params: { path: { batch_id: batchId } },
      headers: await mutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getScenarios(options?: {
  enrollmentId?: string;
  includeArchived?: boolean;
  headers?: HeadersInit;
}): Promise<{ data: { items: PlanningScenario[] } | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/scenarios", {
      headers: options?.headers,
      params: {
        query: {
          enrollment_id: options?.enrollmentId,
          include_archived: options?.includeArchived,
        },
      },
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getScenarioCompare(options: {
  leftId: string;
  rightId: string;
  headers?: HeadersInit;
}): Promise<{ data: ScenarioCompare | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/scenarios/compare", {
      headers: options.headers,
      params: { query: { left_id: options.leftId, right_id: options.rightId } },
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function createScenario(
  body: ScenarioCreatePayload,
  options?: ScenarioMutationOptions,
): Promise<{ data: PlanningScenario | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/scenarios", {
      body,
      headers: await mutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function updateScenario(
  scenarioId: string,
  body: ScenarioPatchPayload,
  options: ScenarioMutationOptions,
): Promise<{ data: PlanningScenario | null; failure: ApiFailure | null }> {
  try {
    const result = await api.PATCH("/api/v1/scenarios/{scenario_id}", {
      params: { path: { scenario_id: scenarioId } },
      body,
      headers: await mutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function addPlannedCourse(
  scenarioId: string,
  body: PlannedCourseCreatePayload,
  options?: ScenarioMutationOptions,
): Promise<{ data: PlanningScenario | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/scenarios/{scenario_id}/courses", {
      params: { path: { scenario_id: scenarioId } },
      body,
      headers: await mutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function updatePlannedCourse(
  scenarioId: string,
  plannedCourseId: string,
  body: PlannedCoursePatchPayload,
  options: ScenarioMutationOptions,
): Promise<{ data: PlanningScenario | null; failure: ApiFailure | null }> {
  try {
    const result = await api.PATCH("/api/v1/scenarios/{scenario_id}/courses/{planned_course_id}", {
      params: { path: { scenario_id: scenarioId, planned_course_id: plannedCourseId } },
      body,
      headers: await mutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function deletePlannedCourse(
  scenarioId: string,
  plannedCourseId: string,
  options: ScenarioMutationOptions,
): Promise<{ data: PlanningScenario | null; failure: ApiFailure | null }> {
  try {
    const result = await api.DELETE("/api/v1/scenarios/{scenario_id}/courses/{planned_course_id}", {
      params: { path: { scenario_id: scenarioId, planned_course_id: plannedCourseId } },
      headers: await mutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function duplicateScenario(
  scenarioId: string,
  name: string,
  options?: ScenarioMutationOptions,
): Promise<{ data: PlanningScenario | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/scenarios/{scenario_id}/duplicate", {
      params: { path: { scenario_id: scenarioId } },
      body: { name },
      headers: await mutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function archiveScenario(
  scenarioId: string,
  options: ScenarioMutationOptions,
): Promise<{ data: PlanningScenario | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/scenarios/{scenario_id}/archive", {
      params: { path: { scenario_id: scenarioId } },
      headers: await mutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function startOptimization(
  scenarioId: string,
  body: OptimizationRequestPayload,
  options?: ScenarioMutationOptions,
): Promise<{ data: OptimizationRun | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/scenarios/{scenario_id}/optimization-runs", {
      params: { path: { scenario_id: scenarioId } },
      body,
      headers: await mutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getOptimizationRun(
  runId: string,
  options?: { headers?: HeadersInit },
): Promise<{ data: OptimizationRun | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/optimization-runs/{run_id}", {
      params: { path: { run_id: runId } },
      headers: options?.headers,
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function cancelOptimizationRun(
  runId: string,
  options?: ScenarioMutationOptions,
): Promise<{ data: OptimizationRun | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/optimization-runs/{run_id}/cancel", {
      params: { path: { run_id: runId } },
      headers: await mutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getGovernanceInbox(options?: {
  headers?: HeadersInit;
}): Promise<{ data: SourceInbox | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/governance/inbox", { headers: options?.headers });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getGovernanceProposal(
  proposalId: string,
  options?: { headers?: HeadersInit },
): Promise<{ data: GovernanceProposal | null; failure: ApiFailure | null; etag: string | null }> {
  try {
    const result = await api.GET("/api/v1/governance/proposals/{proposal_id}", {
      params: { path: { proposal_id: proposalId } },
      headers: options?.headers,
    });
    if (result.data) return { data: result.data, failure: null, etag: result.response.headers.get("ETag") };
    return { data: null, failure: failureFromResult(result), etag: null };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true }, etag: null };
  }
}

async function governanceMutationHeaders(options: ScenarioMutationOptions = {}): Promise<HeadersInit> {
  return mutationHeaders(options);
}

export async function submitGovernanceProposal(
  proposalId: string,
  body: { comment?: string },
  options: ScenarioMutationOptions,
): Promise<{ data: GovernanceProposal | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/governance/proposals/{proposal_id}/submit", {
      params: { path: { proposal_id: proposalId } },
      body: { comment: body.comment ?? "" },
      headers: await governanceMutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function reviewGovernanceProposal(
  proposalId: string,
  body: GovernanceReviewPayload,
  options: ScenarioMutationOptions,
): Promise<{ data: GovernanceProposal | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/governance/proposals/{proposal_id}/review", {
      params: { path: { proposal_id: proposalId } },
      body,
      headers: await governanceMutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function publishGovernanceProposal(
  proposalId: string,
  confirmation: string,
  options: ScenarioMutationOptions,
): Promise<{ data: GovernanceProposal | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/governance/proposals/{proposal_id}/publish", {
      params: { path: { proposal_id: proposalId } },
      body: { confirmation },
      headers: await governanceMutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getGovernancePublicationImpact(
  publicationId: string,
  options?: { headers?: HeadersInit },
): Promise<{ data: GovernancePublicationImpact | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/governance/publications/{publication_id}/impact", {
      params: { path: { publication_id: publicationId } },
      headers: options?.headers,
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function reviewGovernanceCandidate(
  proposalId: string,
  candidateId: string,
  body: GovernanceCandidateReviewPayload,
  options: ScenarioMutationOptions,
): Promise<{ data: GovernanceCandidate | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/governance/proposals/{proposal_id}/candidates/{candidate_id}/review", {
      params: { path: { proposal_id: proposalId, candidate_id: candidateId } },
      body,
      headers: await governanceMutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function previewGovernanceCandidates(
  proposalId: string,
  body: GovernanceBulkCandidatePayload,
): Promise<{ data: GovernanceBulkPreview | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/governance/proposals/{proposal_id}/candidates/bulk-preview", {
      params: { path: { proposal_id: proposalId } },
      body,
      headers: await governanceMutationHeaders(),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function applyGovernanceCandidates(
  proposalId: string,
  body: GovernanceBulkCandidatePayload,
  options: ScenarioMutationOptions,
): Promise<{ data: GovernanceProposal | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/governance/proposals/{proposal_id}/candidates/bulk-review", {
      params: { path: { proposal_id: proposalId } },
      body,
      headers: await governanceMutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function linkGovernanceRequirementEvidence(
  requirementId: string,
  evidenceIds: string[],
  options: ScenarioMutationOptions,
): Promise<{ data: GovernanceRequirement | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/governance/requirements/{requirement_id}/evidence", {
      params: { path: { requirement_id: requirementId } },
      body: { evidence_ids: evidenceIds },
      headers: await governanceMutationHeaders(options),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export type StudentAdminCatalog = ApiComponents["schemas"]["StudentAdminCatalogView"];
export type AdminEnrollment = ApiComponents["schemas"]["AdminEnrollmentView"];
export type AdminEnrollmentSummary = ApiComponents["schemas"]["AdminEnrollmentSummaryView"];
export type AdminEnrollmentPage = ApiComponents["schemas"]["AdminEnrollmentCollectionView"];
export type AdminEnrollmentCreatePayload = ApiComponents["schemas"]["AdminEnrollmentCreatePayload"];
export type AdminAssignmentPreviewPayload = ApiComponents["schemas"]["AdminAssignmentPreviewPayload"];
export type AdminAssignmentPreview = ApiComponents["schemas"]["AdminAssignmentPreviewView"];
export type AdminEnrollmentRevisionPayload = ApiComponents["schemas"]["AdminEnrollmentRevisionPayload"];
export type AdminIdentityUpdatePayload = ApiComponents["schemas"]["AdminIdentityUpdatePayload"];
export type AdminTransitionPayload = ApiComponents["schemas"]["AdminTransitionPayload"];
export type AdminTransitionCreatePayload = ApiComponents["schemas"]["AdminTransitionCreatePayload"];
export type AdminEnrollmentOverridePayload = ApiComponents["schemas"]["AdminEnrollmentOverridePayload"];

export async function getStudentAdminCatalog(options?: {
  headers?: HeadersInit;
}): Promise<{ data: StudentAdminCatalog | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/admin/students/catalog", {
      headers: options?.headers,
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function previewAdminCurriculumAssignment(
  body: AdminAssignmentPreviewPayload,
): Promise<{ data: AdminAssignmentPreview | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/admin/students/assignment-preview", {
      body,
      headers: await mutationHeaders(),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getAdminEnrollments(options?: {
  search?: string;
  limit?: number;
  offset?: number;
  headers?: HeadersInit;
}): Promise<{ data: ApiComponents["schemas"]["AdminEnrollmentCollectionView"] | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/admin/students/enrollments", {
      headers: options?.headers,
      params: {
        query: {
          search: options?.search,
          limit: options?.limit,
          offset: options?.offset,
        },
      },
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function getAdminEnrollmentIdentity(
  enrollmentId: string,
): Promise<{ data: AdminEnrollment | null; failure: ApiFailure | null }> {
  try {
    const result = await api.GET("/api/v1/admin/students/enrollments/{enrollment_id}/identity", {
      params: { path: { enrollment_id: enrollmentId } },
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function createAdminEnrollment(
  body: AdminEnrollmentCreatePayload,
): Promise<{ data: AdminEnrollmentSummary | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST("/api/v1/admin/students/enrollments", {
      body,
      headers: await mutationHeaders(),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function confirmAdminEnrollmentRevision(
  enrollmentId: string,
  body: AdminEnrollmentRevisionPayload,
  version: string,
): Promise<{ data: AdminEnrollmentSummary | null; failure: ApiFailure | null }> {
  try {
    const result = await api.PATCH("/api/v1/admin/students/enrollments/{enrollment_id}/revision", {
      params: { path: { enrollment_id: enrollmentId } },
      body,
      headers: await mutationHeaders({ ifMatch: `"${version}"` }),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function previewAdminEnrollmentTransition(
  sourceEnrollmentId: string,
  body: AdminTransitionPayload,
): Promise<{ data: AdminAssignmentPreview | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST(
      "/api/v1/admin/students/enrollments/{source_enrollment_id}/transition-preview",
      {
        params: { path: { source_enrollment_id: sourceEnrollmentId } },
        body,
        headers: await mutationHeaders(),
      },
    );
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function createAdminEnrollmentTransition(
  sourceEnrollmentId: string,
  body: AdminTransitionCreatePayload,
): Promise<{ data: AdminEnrollmentSummary | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST(
      "/api/v1/admin/students/enrollments/{source_enrollment_id}/transitions",
      {
        params: { path: { source_enrollment_id: sourceEnrollmentId } },
        body,
        headers: await mutationHeaders(),
      },
    );
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function overrideAdminEnrollmentAssignment(
  enrollmentId: string,
  body: AdminEnrollmentOverridePayload,
  version: string,
): Promise<{ data: AdminEnrollmentSummary | null; failure: ApiFailure | null }> {
  try {
    const result = await api.POST(
      "/api/v1/admin/students/enrollments/{enrollment_id}/assignment-override",
      {
        params: { path: { enrollment_id: enrollmentId } },
        body,
        headers: await mutationHeaders({ ifMatch: `"${version}"` }),
      },
    );
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function updateAdminEnrollmentIdentity(
  enrollmentId: string,
  body: AdminIdentityUpdatePayload,
  version: string,
): Promise<{ data: AdminEnrollment | null; failure: ApiFailure | null }> {
  try {
    const result = await api.PATCH("/api/v1/admin/students/enrollments/{enrollment_id}/identity", {
      params: { path: { enrollment_id: enrollmentId } },
      body,
      headers: await mutationHeaders({ ifMatch: `"${version}"` }),
    });
    if (result.data) return { data: result.data, failure: null };
    return { data: null, failure: failureFromResult(result) };
  } catch {
    return { data: null, failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export type ApiPath = keyof ApiPaths;
