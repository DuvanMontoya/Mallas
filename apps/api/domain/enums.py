from __future__ import annotations

from enum import Enum
from typing import TypeVar


class InstitutionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class RevisionStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"


class RequirementGroupKind(str, Enum):
    COMPONENT = "COMPONENT"
    GROUP = "GROUP"
    GRADUATION = "GRADUATION"


class MembershipRole(str, Enum):
    MANDATORY = "MANDATORY"
    ELECTIVE_OPTION = "ELECTIVE_OPTION"
    FREE_ELECTIVE_OPTION = "FREE_ELECTIVE_OPTION"
    EXTERNAL_REFERENCE = "EXTERNAL_REFERENCE"


class CountPolicy(str, Enum):
    COURSE = "COURSE"
    CREDITS = "CREDITS"
    ONCE = "ONCE"


class EpistemicStatus(str, Enum):
    VERIFIED = "VERIFIED"
    DERIVED = "DERIVED"
    INFERRED_PENDING_REVIEW = "INFERRED_PENDING_REVIEW"
    UNKNOWN = "UNKNOWN"
    DISPUTED = "DISPUTED"
    SUPERSEDED = "SUPERSEDED"


class SourceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUPERSEDED = "SUPERSEDED"
    UNKNOWN = "UNKNOWN"


class NormRelationType(str, Enum):
    AMENDS = "AMENDS"
    REPEALS = "REPEALS"
    ADDS = "ADDS"
    CLARIFIES = "CLARIFIES"
    SUPERSEDES = "SUPERSEDES"


class RequirementPurpose(str, Enum):
    ENROLLMENT_PREREQUISITE = "ENROLLMENT_PREREQUISITE"
    COREQUISITE = "COREQUISITE"
    GROUP_COMPLETION = "GROUP_COMPLETION"
    GRADUATION = "GRADUATION"
    PRACTICE_ELIGIBILITY = "PRACTICE_ELIGIBILITY"
    SUBSTITUTION = "SUBSTITUTION"


class TermStatus(str, Enum):
    PLANNED = "PLANNED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    COMPLETED = "COMPLETED"


class OfferingStatus(str, Enum):
    PLANNED = "PLANNED"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class SectionModality(str, Enum):
    IN_PERSON = "IN_PERSON"
    ONLINE = "ONLINE"
    HYBRID = "HYBRID"
    UNKNOWN = "UNKNOWN"


class EnrollmentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    SUSPENDED = "SUSPENDED"
    WITHDRAWN = "WITHDRAWN"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class AttemptStatus(str, Enum):
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


class AttemptOrigin(str, Enum):
    SIA = "SIA"
    MANUAL = "MANUAL"
    IMPORT = "IMPORT"
    RECOGNITION = "RECOGNITION"


class RecognitionType(str, Enum):
    EQUIVALENCE = "EQUIVALENCE"
    HOMOLOGATION = "HOMOLOGATION"
    TRANSFER = "TRANSFER"
    SUBSTITUTION = "SUBSTITUTION"


class ExceptionStatus(str, Enum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class ImportStatus(str, Enum):
    RECEIVED = "RECEIVED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"


class ScenarioStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ScenarioCourseSource(str, Enum):
    USER = "USER"
    OPTIMIZER = "OPTIMIZER"


EnumT = TypeVar("EnumT", bound=Enum)


def enum_choices(enum_type: type[EnumT]) -> list[tuple[str, str]]:
    """Return stable Django-style choices without importing Django."""

    return [(member.value, member.name.replace("_", " ").title()) for member in enum_type]

