"""Pure, versioned rule AST and deterministic evaluator."""

from .ast import (
    AST_SCHEMA_VERSION,
    All,
    AnyOf,
    AuditRule,
    Corequisite,
    CourseInProgress,
    CoursePassed,
    CoursePassedOrInProgress,
    CreditsInComponent,
    CreditsInGroup,
    EquivalentCoursePassed,
    ExternalRequirement,
    GroupCompleted,
    MandatoryCoursesCompleted,
    MinimumGrade,
    Not,
    PercentageOfPlan,
    TotalCredits,
    Unknown,
    ast_hash,
    canonical_rule_json,
    parse_rule,
    parse_rule_document,
    serialize_rule,
    serialize_rule_document,
)
from .errors import RuleEvaluationError, RuleSchemaError
from .evaluator import (
    AuditContext,
    EvaluationResult,
    EvaluationStatus,
    RevisionFacts,
    evaluate_rule,
)
from .graph import direct_course_dependencies, find_requirement_cycles

RuleStatus = EvaluationStatus
RuleResult = EvaluationResult
parse_ast = parse_rule
serialize_ast = serialize_rule
hash_ast = ast_hash

__all__ = [
    "AST_SCHEMA_VERSION",
    "All",
    "AnyOf",
    "AuditContext",
    "AuditRule",
    "Corequisite",
    "CourseInProgress",
    "CoursePassed",
    "CoursePassedOrInProgress",
    "CreditsInComponent",
    "CreditsInGroup",
    "EquivalentCoursePassed",
    "EvaluationResult",
    "EvaluationStatus",
    "ExternalRequirement",
    "GroupCompleted",
    "MandatoryCoursesCompleted",
    "MinimumGrade",
    "Not",
    "PercentageOfPlan",
    "RevisionFacts",
    "RuleEvaluationError",
    "RuleResult",
    "RuleSchemaError",
    "RuleStatus",
    "TotalCredits",
    "Unknown",
    "ast_hash",
    "canonical_rule_json",
    "direct_course_dependencies",
    "evaluate_rule",
    "find_requirement_cycles",
    "hash_ast",
    "parse_ast",
    "parse_rule",
    "parse_rule_document",
    "serialize_rule",
    "serialize_rule_document",
    "serialize_ast",
]
