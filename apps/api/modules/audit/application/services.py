from __future__ import annotations

import datetime
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from domain.audit import (
    AcademicExceptionFact,
    AcademicRecord,
    AuditInput,
    AuditResult,
    CurriculumGroup,
    MembershipSnapshot,
    RequirementSnapshot,
    RevisionSnapshot,
    audit_degree,
)
from domain.rules import EvaluationStatus, Unknown, parse_rule
from domain.rules.errors import RuleSchemaError
from modules.audit.models import CreditAllocation, DegreeAuditResult, DegreeAuditRun
from modules.curriculum.models import Course, CurriculumRevision
from modules.student_records.models import ProgramEnrollment


def _evidence_refs(requirement: Any) -> tuple[str, ...]:
    refs: list[str] = []
    for evidence in requirement.evidence.all():
        locator = (
            evidence.line_locator
            or evidence.section
            or (f"page:{evidence.page}" if evidence.page else "source")
        )
        refs.append(f"{evidence.snapshot.sha256}#{locator}")
    return tuple(sorted(set(refs)))


def build_revision_snapshot(revision: CurriculumRevision) -> RevisionSnapshot:
    groups = list(
        revision.requirement_groups.select_related("parent").order_by("sort_order", "code")
    )
    components = {
        str(
            group.metadata.get("source_component_id", group.code.removeprefix("COMPONENT::"))
        ): group.required_credits
        for group in groups
        if group.kind == "COMPONENT"
    }
    curriculum_groups: dict[str, CurriculumGroup] = {}
    for group in groups:
        if group.kind == "COMPONENT":
            continue
        component = str(
            group.metadata.get("source_component_id")
            or (group.parent.metadata.get("source_component_id") if group.parent else "")
        )
        curriculum_groups[group.code] = CurriculumGroup(
            code=group.code,
            component=component,
            label=group.label,
            required_credits=group.required_credits,
            open_elective=group.code == "FREE_ELECTIVE",
        )

    memberships = list(
        revision.memberships.select_related("course_version__course", "group").order_by(
            "course_version__course__code", "group__code"
        )
    )
    membership_snapshots = tuple(
        MembershipSnapshot(
            course_code=membership.course_version.course.code,
            group_code=membership.group.code,
            role=membership.role,
            count_policy=membership.count_policy,
        )
        for membership in memberships
        if membership.group.code in curriculum_groups
    )
    course_credits = {
        membership.course_version.course.code: membership.course_version.credits
        for membership in memberships
    }
    mandatory: dict[str, set[str]] = {}
    for membership in memberships:
        if membership.role == "MANDATORY" and membership.group.code in curriculum_groups:
            mandatory.setdefault(membership.group.code, set()).add(
                membership.course_version.course.code
            )

    def requirement_from_model(
        requirement: Any, owner_course_code: str | None
    ) -> RequirementSnapshot:
        try:
            rule = parse_rule(requirement.ast)
        except RuleSchemaError:
            rule = Unknown(f"invalid_ast:{requirement.code}")
        return RequirementSnapshot(
            code=requirement.code,
            rule=rule,
            purpose=requirement.purpose,
            epistemic_status=requirement.epistemic_status,
            owner_course_code=owner_course_code,
            evidence_refs=_evidence_refs(requirement),
            source_metadata=requirement.metadata,
        )

    requirements = list(revision.requirements.all().order_by("code"))
    owner_ids = {
        requirement.owner_id for requirement in requirements if requirement.owner_type == "COURSE"
    }
    owners = {str(course.pk): course.code for course in Course.objects.filter(pk__in=owner_ids)}
    course_requirements = tuple(
        requirement_from_model(requirement, owners.get(str(requirement.owner_id)))
        for requirement in requirements
        if requirement.owner_type == "COURSE"
    )
    graduation_requirements = tuple(
        requirement_from_model(requirement, None)
        for requirement in requirements
        if requirement.owner_type == "REVISION"
    )
    return RevisionSnapshot(
        revision_id=str(revision.pk),
        content_hash=revision.content_hash,
        total_required_credits=revision.total_required_credits,
        components=components,
        groups=curriculum_groups,
        course_credits=course_credits,
        memberships=membership_snapshots,
        mandatory_courses_by_group={key: frozenset(value) for key, value in mandatory.items()},
        requirements=course_requirements,
        graduation_requirements=graduation_requirements,
    )


def build_audit_input(
    enrollment: ProgramEnrollment,
    *,
    external_requirements: dict[str, EvaluationStatus | bool | None] | None = None,
    audit_date: datetime.date | None = None,
) -> AuditInput:
    revision = build_revision_snapshot(enrollment.revision_basis)
    attempts = list(
        enrollment.course_attempts.select_related("course_version__course").order_by(
            "course_version__course__code", "attempt_number", "id"
        )
    )
    history = tuple(
        AcademicRecord(
            course_code=attempt.course_version.course.code,
            status=attempt.status,
            attempt_id=str(attempt.pk),
            credits_earned=attempt.credits_earned or None,
            grade=str(attempt.grade) if attempt.grade is not None else None,
        )
        for attempt in attempts
    )
    recognitions = list(
        enrollment.recognitions.select_related("target_course_version__course").order_by("id")
    )
    recognized_courses: set[str] = set()
    recognition_sources: dict[str, set[str]] = {}
    recognized_credits: dict[str, int | None] = {}
    for recognition in recognitions:
        target_code = recognition.target_course_version.course.code
        recognized_courses.add(target_code)
        source_code = (
            recognition.source_course_version.course.code
            if recognition.source_course_version_id
            else "EXTERNAL_RECOGNITION"
        )
        recognition_sources.setdefault(target_code, set()).add(source_code)
        if recognition.credits_applied > 0:
            previous = recognized_credits.get(target_code)
            recognized_credits[target_code] = (
                recognition.credits_applied
                if previous is None
                else max(previous, recognition.credits_applied)
            )
    exceptions = tuple(
        AcademicExceptionFact(
            exception_id=str(exception.pk),
            status=exception.status,
            scope=exception.scope,
        )
        for exception in enrollment.academic_exceptions.all().order_by("id")
    )
    return AuditInput(
        revision=revision,
        history=history,
        recognized_courses=frozenset(recognized_courses),
        recognitions={key: frozenset(value) for key, value in recognition_sources.items()},
        recognized_credits=recognized_credits,
        external_requirements=external_requirements or {},
        exceptions=exceptions,
        audit_date=audit_date.isoformat() if audit_date else None,
    )


@transaction.atomic  # type: ignore[untyped-decorator]
def run_degree_audit(
    enrollment_id: UUID | str,
    *,
    external_requirements: dict[str, EvaluationStatus | bool | None] | None = None,
    audit_date: datetime.date | None = None,
) -> tuple[AuditResult, DegreeAuditRun, DegreeAuditResult]:
    enrollment = ProgramEnrollment.objects.select_related(
        "revision_basis", "plan", "program", "student"
    ).get(pk=enrollment_id)
    audit_input = build_audit_input(
        enrollment,
        external_requirements=external_requirements,
        audit_date=audit_date,
    )
    result = audit_degree(audit_input)
    run = DegreeAuditRun.objects.create(
        enrollment=enrollment,
        revision=enrollment.revision_basis,
        history_fingerprint=audit_input.history_fingerprint,
        exception_fingerprint=audit_input.exception_fingerprint,
        engine_version=result.engine_version,
        result_hash=result.result_hash,
        generated_at=timezone.now(),
        input_snapshot={"audit_input": audit_input.to_dict(), "result": result.to_dict()},
    )
    persisted_result = DegreeAuditResult.objects.create(
        run=run,
        status=result.status.value,
        total_approved_credits=result.earned_credits,
        total_applied_credits=result.applied_credits,
        total_excess_credits=result.unapplied_credits,
        payload=result.to_dict(),
        unknown_count=len(result.unknowns),
    )
    attempts = {
        str(attempt.pk): attempt
        for attempt in enrollment.course_attempts.select_related("course_version__course")
    }
    course_versions = {
        membership.course_version.course.code: membership.course_version
        for membership in enrollment.revision_basis.memberships.select_related(
            "course_version__course"
        )
    }
    for order, allocation in enumerate(result.ledger.allocations):
        CreditAllocation.objects.create(
            result=persisted_result,
            course_attempt=attempts.get(allocation.attempt_id),
            course_version=course_versions.get(allocation.course_code),
            requirement_code=allocation.requirement_code,
            allocated_credits=allocation.applied_credits,
            allocation_order=order,
        )
    return result, run, persisted_result
