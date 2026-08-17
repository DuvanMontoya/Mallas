"""Pure planning validation primitives."""

from .validator import (
    CourseValidation,
    PlannedCourseFact,
    RequirementFact,
    ScenarioValidation,
    ValidationWarning,
    validate_scenario,
)

__all__ = [
    "CourseValidation",
    "PlannedCourseFact",
    "RequirementFact",
    "ScenarioValidation",
    "ValidationWarning",
    "validate_scenario",
]
