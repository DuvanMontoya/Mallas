class DomainError(Exception):
    """Base error for deterministic domain services."""


class PublishedRevisionImmutableError(DomainError):
    """Raised when content of a published revision would be changed."""


class PublishedAssignmentPolicyImmutableError(DomainError):
    """Raised when a published curriculum-assignment policy would be changed."""


class AuditEventImmutableError(DomainError):
    """Raised when an append-only audit event would be changed or deleted."""


class CurriculumAssignmentDecisionImmutableError(DomainError):
    """Raised when an append-only assignment decision would be changed."""
