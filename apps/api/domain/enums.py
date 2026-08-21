from __future__ import annotations

from enum import Enum, StrEnum


class InstitutionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class UserRole(StrEnum):
    STUDENT = "STUDENT"
    ADVISOR = "ADVISOR"
    EDITOR = "EDITOR"
    REVIEWER = "REVIEWER"
    ANALYST = "ANALYST"
    ADMIN = "ADMIN"


class RevisionStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"


class RequirementGroupKind(StrEnum):
    COMPONENT = "COMPONENT"
    GROUP = "GROUP"
    GRADUATION = "GRADUATION"


class MembershipRole(StrEnum):
    MANDATORY = "MANDATORY"
    ELECTIVE_OPTION = "ELECTIVE_OPTION"
    FREE_ELECTIVE_OPTION = "FREE_ELECTIVE_OPTION"
    EXTERNAL_REFERENCE = "EXTERNAL_REFERENCE"


class CountPolicy(StrEnum):
    COURSE = "COURSE"
    CREDITS = "CREDITS"
    ONCE = "ONCE"


class EpistemicStatus(StrEnum):
    VERIFIED = "VERIFIED"
    DERIVED = "DERIVED"
    INFERRED_PENDING_REVIEW = "INFERRED_PENDING_REVIEW"
    UNKNOWN = "UNKNOWN"
    DISPUTED = "DISPUTED"
    SUPERSEDED = "SUPERSEDED"


class SourceStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUPERSEDED = "SUPERSEDED"
    UNKNOWN = "UNKNOWN"


class NormRelationType(StrEnum):
    AMENDS = "AMENDS"
    REPEALS = "REPEALS"
    ADDS = "ADDS"
    CLARIFIES = "CLARIFIES"
    SUPERSEDES = "SUPERSEDES"


class RequirementPurpose(StrEnum):
    ENROLLMENT_PREREQUISITE = "ENROLLMENT_PREREQUISITE"
    COREQUISITE = "COREQUISITE"
    GROUP_COMPLETION = "GROUP_COMPLETION"
    GRADUATION = "GRADUATION"
    PRACTICE_ELIGIBILITY = "PRACTICE_ELIGIBILITY"
    SUBSTITUTION = "SUBSTITUTION"


class TermStatus(StrEnum):
    PLANNED = "PLANNED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    COMPLETED = "COMPLETED"


class OfferingStatus(StrEnum):
    PLANNED = "PLANNED"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class SectionModality(StrEnum):
    IN_PERSON = "IN_PERSON"
    ONLINE = "ONLINE"
    HYBRID = "HYBRID"
    UNKNOWN = "UNKNOWN"


class OfferingFreshness(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class CapacityStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    REPORTED_NOT_REAL_TIME = "REPORTED_NOT_REAL_TIME"
    REAL_TIME = "REAL_TIME"


class EnrollmentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    SUSPENDED = "SUSPENDED"
    WITHDRAWN = "WITHDRAWN"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    TRANSITIONED = "TRANSITIONED"


class CurriculumAssignmentContext(StrEnum):
    ADMISSION = "ADMISSION"
    REENTRY = "REENTRY"
    TRANSFER = "TRANSFER"
    DUAL_DEGREE = "DUAL_DEGREE"
    PLAN_TRANSITION = "PLAN_TRANSITION"


class CurriculumAssignmentPolicyStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"


class CurriculumAssignmentDecisionStatus(StrEnum):
    RESOLVED = "RESOLVED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    UNKNOWN = "UNKNOWN"


class CurriculumAssignmentMethod(StrEnum):
    AUTOMATIC = "AUTOMATIC"
    POLICY_EVALUATION = "POLICY_EVALUATION"
    ADMIN_OVERRIDE = "ADMIN_OVERRIDE"


class AdmissionFactVerificationMethod(StrEnum):
    SOURCE_SNAPSHOT = "SOURCE_SNAPSHOT"
    INSTITUTIONAL_RECORD_REFERENCE = "INSTITUTIONAL_RECORD_REFERENCE"
    VERIFIED_ADMISSION_FACT = "VERIFIED_ADMISSION_FACT"


class AttemptStatus(StrEnum):
    PLANNED = "PLANNED"
    ENROLLED = "ENROLLED"
    PASSED = "PASSED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    WITHDRAWN = "WITHDRAWN"
    VALIDATED = "VALIDATED"
    HOMOLOGATED = "HOMOLOGATED"
    TRANSFERRED = "TRANSFERRED"
    ANNULLED = "ANNULLED"


class AttemptOrigin(StrEnum):
    SIA = "SIA"
    MANUAL = "MANUAL"
    IMPORT = "IMPORT"
    RECOGNITION = "RECOGNITION"


class RecognitionType(StrEnum):
    EQUIVALENCE = "EQUIVALENCE"
    HOMOLOGATION = "HOMOLOGATION"
    TRANSFER = "TRANSFER"
    SUBSTITUTION = "SUBSTITUTION"


class ExceptionStatus(StrEnum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class ImportStatus(StrEnum):
    RECEIVED = "RECEIVED"
    VALIDATING = "VALIDATING"
    PREVIEW = "PREVIEW"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"


class ImportArtifactStatus(StrEnum):
    STORED = "STORED"
    REJECTED = "REJECTED"
    PURGE_PENDING = "PURGE_PENDING"
    PURGED = "PURGED"


class CandidateStatus(StrEnum):
    PENDING = "PENDING"
    VALID = "VALID"
    CONFLICT = "CONFLICT"
    ERROR = "ERROR"
    RESOLVED = "RESOLVED"
    SKIPPED = "SKIPPED"


class ReconciliationDecision(StrEnum):
    PENDING = "PENDING"
    ACCEPT = "ACCEPT"
    EXTERNAL = "EXTERNAL"
    SKIP = "SKIP"


class ProposalStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"
    WITHDRAWN = "WITHDRAWN"


class ReviewDecision(StrEnum):
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    REJECT = "REJECT"


class ExtractionCandidateStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class PublicationImpactStatus(StrEnum):
    IDENTIFIED = "IDENTIFIED"
    RECOMPUTE_QUEUED = "RECOMPUTE_QUEUED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    RECOMPUTED = "RECOMPUTED"


class CurriculumLayoutType(StrEnum):
    SOURCE_FAITHFUL_LAYOUT = "SOURCE_FAITHFUL_LAYOUT"
    DEPENDENCY_DERIVED_LAYOUT = "DEPENDENCY_DERIVED_LAYOUT"


class CurriculumLayoutStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"


class CurriculumLayoutNodeType(StrEnum):
    COURSE = "COURSE"
    CHOICE_POOL = "CHOICE_POOL"
    FREE_ELECTIVE_POOL = "FREE_ELECTIVE_POOL"
    EXTERNAL_REQUIREMENT = "EXTERNAL_REQUIREMENT"
    MILESTONE = "MILESTONE"
    ANNOTATION = "ANNOTATION"


class NotificationDeliveryStatus(StrEnum):
    QUEUED = "QUEUED"
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    SUPPRESSED = "SUPPRESSED"


class NotificationChannel(StrEnum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"


class NotificationEventType(StrEnum):
    CURRICULUM_REVISION_PUBLISHED = "curriculum.revision.published"


class ScenarioStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ScenarioCourseSource(StrEnum):
    USER = "USER"
    OPTIMIZER = "OPTIMIZER"


def enum_choices[EnumT: Enum](enum_type: type[EnumT]) -> list[tuple[str, str]]:
    """Return stable Django-style choices without importing Django."""

    return [(member.value, member.name.replace("_", " ").title()) for member in enum_type]
