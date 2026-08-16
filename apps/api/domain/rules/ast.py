from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from .errors import RuleSchemaError

AST_SCHEMA_VERSION = "1.0.0"
_COMPARISON_OPERATORS = frozenset({">=", ">", "=", "<=", "<"})


class RuleNode:
    """Marker base class for all discriminated rule nodes."""


def _require_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _require_integer(value: object, *, field: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{field} must be an integer >= {minimum}")
    return value


def _require_operator(value: object) -> str:
    if value not in _COMPARISON_OPERATORS:
        raise ValueError(f"operator must be one of {sorted(_COMPARISON_OPERATORS)}")
    return str(value)


@dataclass(frozen=True, slots=True)
class All(RuleNode):
    children: tuple[AuditRule, ...]

    def __post_init__(self) -> None:
        children = tuple(self.children)
        if not children:
            raise ValueError("ALL requires at least one child")
        if not all(isinstance(child, RuleNode) for child in children):
            raise ValueError("ALL children must be rule nodes")
        object.__setattr__(self, "children", children)


@dataclass(frozen=True, slots=True)
class AnyOf(RuleNode):
    children: tuple[AuditRule, ...]

    def __post_init__(self) -> None:
        children = tuple(self.children)
        if not children:
            raise ValueError("ANY requires at least one child")
        if not all(isinstance(child, RuleNode) for child in children):
            raise ValueError("ANY children must be rule nodes")
        object.__setattr__(self, "children", children)


@dataclass(frozen=True, slots=True)
class Not(RuleNode):
    child: AuditRule

    def __post_init__(self) -> None:
        if not isinstance(self.child, RuleNode):
            raise ValueError("NOT child must be a rule node")


@dataclass(frozen=True, slots=True)
class CoursePassed(RuleNode):
    course_code: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "course_code", _require_text(self.course_code, field="course_code")
        )


@dataclass(frozen=True, slots=True)
class CourseInProgress(RuleNode):
    course_code: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "course_code", _require_text(self.course_code, field="course_code")
        )


@dataclass(frozen=True, slots=True)
class CoursePassedOrInProgress(RuleNode):
    course_code: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "course_code", _require_text(self.course_code, field="course_code")
        )


@dataclass(frozen=True, slots=True)
class CreditsInGroup(RuleNode):
    group: str
    operator: str
    value: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "group", _require_text(self.group, field="group"))
        object.__setattr__(self, "operator", _require_operator(self.operator))
        object.__setattr__(self, "value", _require_integer(self.value, field="value"))


@dataclass(frozen=True, slots=True)
class CreditsInComponent(RuleNode):
    component: str
    operator: str
    value: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "component", _require_text(self.component, field="component"))
        object.__setattr__(self, "operator", _require_operator(self.operator))
        object.__setattr__(self, "value", _require_integer(self.value, field="value"))


@dataclass(frozen=True, slots=True)
class TotalCredits(RuleNode):
    operator: str
    value: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "operator", _require_operator(self.operator))
        object.__setattr__(self, "value", _require_integer(self.value, field="value"))


@dataclass(frozen=True, slots=True)
class PercentageOfPlan(RuleNode):
    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "numerator", _require_integer(self.numerator, field="numerator"))
        object.__setattr__(
            self,
            "denominator",
            _require_integer(self.denominator, field="denominator", minimum=1),
        )


@dataclass(frozen=True, slots=True)
class GroupCompleted(RuleNode):
    group: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "group", _require_text(self.group, field="group"))


@dataclass(frozen=True, slots=True)
class MandatoryCoursesCompleted(RuleNode):
    course_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        codes = tuple(_require_text(code, field="course_codes[]") for code in self.course_codes)
        if not codes:
            raise ValueError("MANDATORY_COURSES_COMPLETED requires at least one course")
        if len(set(codes)) != len(codes):
            raise ValueError("course_codes must be unique")
        object.__setattr__(self, "course_codes", codes)


@dataclass(frozen=True, slots=True)
class MinimumGrade(RuleNode):
    course_code: str
    minimum_grade: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "course_code", _require_text(self.course_code, field="course_code")
        )
        grade = self.minimum_grade
        if isinstance(grade, bool):
            raise ValueError("minimum_grade must be an exact decimal")
        try:
            decimal_grade = grade if isinstance(grade, Decimal) else Decimal(str(grade))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("minimum_grade must be an exact decimal") from exc
        if not decimal_grade.is_finite():
            raise ValueError("minimum_grade must be finite")
        object.__setattr__(self, "minimum_grade", decimal_grade)


@dataclass(frozen=True, slots=True)
class ExternalRequirement(RuleNode):
    key: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", _require_text(self.key, field="key"))


@dataclass(frozen=True, slots=True)
class EquivalentCoursePassed(RuleNode):
    equivalence_key: str
    course_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "equivalence_key", _require_text(self.equivalence_key, field="equivalence_key")
        )
        codes = tuple(_require_text(code, field="course_codes[]") for code in self.course_codes)
        if not codes:
            raise ValueError("EQUIVALENT_COURSE_PASSED requires at least one course")
        object.__setattr__(self, "course_codes", codes)


@dataclass(frozen=True, slots=True)
class Corequisite(RuleNode):
    course_code: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "course_code", _require_text(self.course_code, field="course_code")
        )


@dataclass(frozen=True, slots=True)
class Unknown(RuleNode):
    reason: str
    raw_source_text: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason", _require_text(self.reason, field="reason"))
        if self.raw_source_text is not None:
            object.__setattr__(
                self,
                "raw_source_text",
                _require_text(self.raw_source_text, field="raw_source_text"),
            )


type AuditRule = (
    All
    | AnyOf
    | Not
    | CoursePassed
    | CourseInProgress
    | CoursePassedOrInProgress
    | CreditsInGroup
    | CreditsInComponent
    | TotalCredits
    | PercentageOfPlan
    | GroupCompleted
    | MandatoryCoursesCompleted
    | MinimumGrade
    | ExternalRequirement
    | EquivalentCoursePassed
    | Corequisite
    | Unknown
)


def _mapping(value: object, *, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuleSchemaError("must be an object", path=path)
    return value


def _check_keys(value: Mapping[str, Any], allowed: set[str], *, path: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise RuleSchemaError(f"unknown fields: {', '.join(unknown)}", path=path)


def _field(value: Mapping[str, Any], field: str, *, path: str) -> object:
    if field not in value:
        raise RuleSchemaError(f"missing required field {field!r}", path=path)
    return value[field]


def _children(value: object, *, path: str) -> tuple[AuditRule, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise RuleSchemaError("children must be an array", path=path)
    if not value:
        raise RuleSchemaError("children cannot be empty", path=path)
    return tuple(parse_rule(child, path=f"{path}[{index}]") for index, child in enumerate(value))


def _course_codes(value: object, *, path: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise RuleSchemaError("course_codes must be an array", path=path)
    return tuple(_parse_text(code, path=f"{path}[{index}]") for index, code in enumerate(value))


def _parse_text(value: object, *, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuleSchemaError("must be a non-empty string", path=path)
    return value.strip()


def _parse_int(value: object, *, path: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise RuleSchemaError(f"must be an integer >= {minimum}", path=path)
    return value


def _parse_decimal(value: object, *, path: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise RuleSchemaError("must be a decimal string or integer", path=path)
    try:
        decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    except InvalidOperation as exc:
        raise RuleSchemaError("must be a valid decimal", path=path) from exc
    if not decimal_value.is_finite():
        raise RuleSchemaError("must be finite", path=path)
    return decimal_value


def _parse_operator(value: object, *, path: str) -> str:
    if value not in _COMPARISON_OPERATORS:
        raise RuleSchemaError("invalid comparison operator", path=path)
    return str(value)


def parse_rule(value: object, *, path: str = "$") -> AuditRule:
    data = _mapping(value, path=path)
    node_type = data.get("type")
    if not isinstance(node_type, str):
        raise RuleSchemaError("type is required", path=path)
    try:
        if node_type == "ALL":
            _check_keys(data, {"type", "children"}, path=path)
            return All(_children(_field(data, "children", path=path), path=f"{path}.children"))
        if node_type == "ANY":
            _check_keys(data, {"type", "children"}, path=path)
            return AnyOf(_children(_field(data, "children", path=path), path=f"{path}.children"))
        if node_type == "NOT":
            _check_keys(data, {"type", "child"}, path=path)
            return Not(parse_rule(_field(data, "child", path=path), path=f"{path}.child"))
        if node_type in {
            "COURSE_PASSED",
            "COURSE_IN_PROGRESS",
            "COURSE_PASSED_OR_IN_PROGRESS",
            "COREQUISITE",
        }:
            _check_keys(data, {"type", "course_code"}, path=path)
            code = _parse_text(_field(data, "course_code", path=path), path=f"{path}.course_code")
            if node_type == "COURSE_PASSED":
                return CoursePassed(code)
            if node_type == "COURSE_IN_PROGRESS":
                return CourseInProgress(code)
            if node_type == "COURSE_PASSED_OR_IN_PROGRESS":
                return CoursePassedOrInProgress(code)
            return Corequisite(code)
        if node_type in {"CREDITS_IN_GROUP", "CREDITS_IN_COMPONENT"}:
            key = "group" if node_type == "CREDITS_IN_GROUP" else "component"
            _check_keys(data, {"type", key, "operator", "value"}, path=path)
            name = _parse_text(_field(data, key, path=path), path=f"{path}.{key}")
            operator = _parse_operator(_field(data, "operator", path=path), path=f"{path}.operator")
            amount = _parse_int(_field(data, "value", path=path), path=f"{path}.value")
            return (
                CreditsInGroup(name, operator, amount)
                if node_type == "CREDITS_IN_GROUP"
                else CreditsInComponent(name, operator, amount)
            )
        if node_type == "TOTAL_CREDITS":
            _check_keys(data, {"type", "operator", "value"}, path=path)
            return TotalCredits(
                _parse_operator(_field(data, "operator", path=path), path=f"{path}.operator"),
                _parse_int(_field(data, "value", path=path), path=f"{path}.value"),
            )
        if node_type == "PERCENTAGE_OF_PLAN":
            _check_keys(data, {"type", "numerator", "denominator"}, path=path)
            return PercentageOfPlan(
                _parse_int(_field(data, "numerator", path=path), path=f"{path}.numerator"),
                _parse_int(
                    _field(data, "denominator", path=path),
                    path=f"{path}.denominator",
                    minimum=1,
                ),
            )
        if node_type == "GROUP_COMPLETED":
            _check_keys(data, {"type", "group"}, path=path)
            return GroupCompleted(
                _parse_text(_field(data, "group", path=path), path=f"{path}.group")
            )
        if node_type == "MANDATORY_COURSES_COMPLETED":
            _check_keys(data, {"type", "course_codes"}, path=path)
            return MandatoryCoursesCompleted(
                _course_codes(_field(data, "course_codes", path=path), path=f"{path}.course_codes")
            )
        if node_type == "MINIMUM_GRADE":
            _check_keys(data, {"type", "course_code", "minimum_grade"}, path=path)
            return MinimumGrade(
                _parse_text(_field(data, "course_code", path=path), path=f"{path}.course_code"),
                _parse_decimal(
                    _field(data, "minimum_grade", path=path), path=f"{path}.minimum_grade"
                ),
            )
        if node_type == "EXTERNAL_REQUIREMENT":
            _check_keys(data, {"type", "key"}, path=path)
            return ExternalRequirement(
                _parse_text(_field(data, "key", path=path), path=f"{path}.key")
            )
        if node_type == "EQUIVALENT_COURSE_PASSED":
            allowed = {"type", "equivalence_key", "course_codes", "course_code"}
            _check_keys(data, allowed, path=path)
            key = _parse_text(
                _field(data, "equivalence_key", path=path), path=f"{path}.equivalence_key"
            )
            if "course_codes" in data and "course_code" in data:
                raise RuleSchemaError("use course_code or course_codes, not both", path=path)
            codes = (
                _course_codes(data["course_codes"], path=f"{path}.course_codes")
                if "course_codes" in data
                else (
                    _parse_text(_field(data, "course_code", path=path), path=f"{path}.course_code"),
                )
            )
            return EquivalentCoursePassed(key, codes)
        if node_type == "UNKNOWN":
            _check_keys(data, {"type", "reason", "raw_source_text"}, path=path)
            raw = data.get("raw_source_text")
            return Unknown(
                _parse_text(_field(data, "reason", path=path), path=f"{path}.reason"),
                _parse_text(raw, path=f"{path}.raw_source_text") if raw is not None else None,
            )
    except ValueError as exc:
        raise RuleSchemaError(str(exc), path=path) from exc
    raise RuleSchemaError(f"unsupported type {node_type!r}", path=path)


def _canonical_child_list(children: tuple[AuditRule, ...]) -> list[dict[str, Any]]:
    serialized = [serialize_rule(child) for child in children]
    return sorted(
        serialized, key=lambda child: json.dumps(child, ensure_ascii=False, sort_keys=True)
    )


def serialize_rule(rule: AuditRule) -> dict[str, Any]:
    if isinstance(rule, All):
        return {"type": "ALL", "children": _canonical_child_list(rule.children)}
    if isinstance(rule, AnyOf):
        return {"type": "ANY", "children": _canonical_child_list(rule.children)}
    if isinstance(rule, Not):
        return {"type": "NOT", "child": serialize_rule(rule.child)}
    if isinstance(rule, CoursePassed):
        return {"type": "COURSE_PASSED", "course_code": rule.course_code}
    if isinstance(rule, CourseInProgress):
        return {"type": "COURSE_IN_PROGRESS", "course_code": rule.course_code}
    if isinstance(rule, CoursePassedOrInProgress):
        return {"type": "COURSE_PASSED_OR_IN_PROGRESS", "course_code": rule.course_code}
    if isinstance(rule, CreditsInGroup):
        return {
            "type": "CREDITS_IN_GROUP",
            "group": rule.group,
            "operator": rule.operator,
            "value": rule.value,
        }
    if isinstance(rule, CreditsInComponent):
        return {
            "type": "CREDITS_IN_COMPONENT",
            "component": rule.component,
            "operator": rule.operator,
            "value": rule.value,
        }
    if isinstance(rule, TotalCredits):
        return {"type": "TOTAL_CREDITS", "operator": rule.operator, "value": rule.value}
    if isinstance(rule, PercentageOfPlan):
        return {
            "type": "PERCENTAGE_OF_PLAN",
            "numerator": rule.numerator,
            "denominator": rule.denominator,
        }
    if isinstance(rule, GroupCompleted):
        return {"type": "GROUP_COMPLETED", "group": rule.group}
    if isinstance(rule, MandatoryCoursesCompleted):
        return {"type": "MANDATORY_COURSES_COMPLETED", "course_codes": sorted(rule.course_codes)}
    if isinstance(rule, MinimumGrade):
        return {
            "type": "MINIMUM_GRADE",
            "course_code": rule.course_code,
            "minimum_grade": format(rule.minimum_grade, "f"),
        }
    if isinstance(rule, ExternalRequirement):
        return {"type": "EXTERNAL_REQUIREMENT", "key": rule.key}
    if isinstance(rule, EquivalentCoursePassed):
        return {
            "type": "EQUIVALENT_COURSE_PASSED",
            "equivalence_key": rule.equivalence_key,
            "course_codes": sorted(rule.course_codes),
        }
    if isinstance(rule, Corequisite):
        return {"type": "COREQUISITE", "course_code": rule.course_code}
    if isinstance(rule, Unknown):
        result: dict[str, Any] = {"type": "UNKNOWN", "reason": rule.reason}
        if rule.raw_source_text is not None:
            result["raw_source_text"] = rule.raw_source_text
        return result
    raise TypeError(f"unsupported rule object {type(rule)!r}")


def serialize_rule_document(rule: AuditRule) -> dict[str, Any]:
    return {"schema_version": AST_SCHEMA_VERSION, "rule": serialize_rule(rule)}


def parse_rule_document(value: object, *, path: str = "$") -> AuditRule:
    data = _mapping(value, path=path)
    if data.get("schema_version") != AST_SCHEMA_VERSION:
        raise RuleSchemaError(
            f"unsupported schema_version {data.get('schema_version')!r}; expected {AST_SCHEMA_VERSION}",
            path=f"{path}.schema_version",
        )
    _check_keys(data, {"schema_version", "rule"}, path=path)
    return parse_rule(_field(data, "rule", path=path), path=f"{path}.rule")


def canonical_rule_json(rule: AuditRule) -> str:
    return json.dumps(
        serialize_rule_document(rule),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def ast_hash(rule: AuditRule) -> str:
    return hashlib.sha256(canonical_rule_json(rule).encode("utf-8")).hexdigest()
