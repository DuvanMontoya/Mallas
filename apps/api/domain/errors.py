class DomainError(Exception):
    """Base error for deterministic domain services."""


class PublishedRevisionImmutableError(DomainError):
    """Raised when content of a published revision would be changed."""

