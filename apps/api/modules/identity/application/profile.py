from __future__ import annotations

from datetime import date
from typing import Any

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.utils import timezone

from modules.identity.application.audit import record_audit_event
from modules.identity.models import (
    BirthDatePurpose,
    IdentityDataStatus,
    IdentityVerificationMethod,
    PersonProfile,
    User,
)


class PersonProfileError(RuntimeError):
    def __init__(self, message: str, *, code: str = "person_profile_invalid") -> None:
        super().__init__(message)
        self.code = code


def person_profile_view(user: User) -> dict[str, Any]:
    try:
        profile = user.person_profile
    except ObjectDoesNotExist:
        profile = None
    return {
        "email": user.email,
        "first_name": profile.first_name if profile else "",
        "middle_names": profile.middle_names if profile else "",
        "first_surname": profile.first_surname if profile else "",
        "second_surname": profile.second_surname if profile else "",
        "preferred_name": profile.preferred_name if profile else "",
        "birth_date": profile.birth_date if profile else None,
        "age": profile.age_on() if profile else None,
        "data_status": profile.data_status if profile else IdentityDataStatus.NEEDS_REVIEW,
        "verification_method": (
            profile.verification_method if profile else IdentityVerificationMethod.LEGACY_UNKNOWN
        ),
        "version": profile.updated_at.isoformat() if profile else "missing",
    }


@transaction.atomic  # type: ignore[untyped-decorator]
def update_own_person_profile(
    *,
    actor: User,
    first_name: str,
    middle_names: str,
    first_surname: str,
    second_surname: str,
    preferred_name: str,
    birth_date: date,
    expected_version: str | None,
    request: Any | None = None,
) -> PersonProfile:
    if expected_version is None:
        raise PersonProfileError(
            "If-Match is required to rectify identity data.",
            code="person_profile_precondition_required",
        )
    locked_user = User.objects.select_for_update().get(pk=actor.pk)
    try:
        profile = PersonProfile.objects.select_for_update().get(user=locked_user)
    except PersonProfile.DoesNotExist:
        if expected_version.strip('"') != "missing":
            raise PersonProfileError(
                "Identity data changed since it was reviewed.",
                code="person_profile_stale_resource",
            ) from None
        profile = PersonProfile(user=locked_user)
    else:
        if expected_version.strip('"') != profile.updated_at.isoformat():
            raise PersonProfileError(
                "Identity data changed since it was reviewed.",
                code="person_profile_stale_resource",
            )
        if profile.verification_method in {
            IdentityVerificationMethod.INSTITUTION_VERIFIED,
            IdentityVerificationMethod.PREEXISTING_UNCLASSIFIED,
        }:
            raise PersonProfileError(
                "Institutional identity requires a verified administrative correction.",
                code="person_profile_institutional_correction_required",
            )

    previous = {
        "first_name": profile.first_name,
        "middle_names": profile.middle_names,
        "first_surname": profile.first_surname,
        "second_surname": profile.second_surname,
        "preferred_name": profile.preferred_name,
        "birth_date": profile.birth_date,
    }
    profile.first_name = first_name
    profile.middle_names = middle_names
    profile.first_surname = first_surname
    profile.second_surname = second_surname
    profile.preferred_name = preferred_name
    profile.birth_date = birth_date
    profile.birth_date_purpose = BirthDatePurpose.ACADEMIC_ADMINISTRATION
    profile.data_status = IdentityDataStatus.CONFIRMED
    profile.verification_method = IdentityVerificationMethod.SELF_DECLARED
    profile.confirmed_at = timezone.now()
    try:
        profile.save()
    except ValidationError as exc:
        raise PersonProfileError("; ".join(exc.messages), code="person_profile_validation") from exc

    current = {
        "first_name": profile.first_name,
        "middle_names": profile.middle_names,
        "first_surname": profile.first_surname,
        "second_surname": profile.second_surname,
        "preferred_name": profile.preferred_name,
        "birth_date": profile.birth_date,
    }
    record_audit_event(
        request,
        action="PERSON_IDENTITY_SELF_RECTIFIED",
        actor=actor,
        object_type="PersonProfile",
        object_id=profile.pk,
        metadata={
            "changed_fields": sorted(
                field for field in previous if previous[field] != current[field]
            ),
            "verification_method": "authenticated_self_service",
        },
    )
    return profile


def person_profile_export(user: User) -> dict[str, Any]:
    view = person_profile_view(user)
    return {
        "schema_version": "person-profile-export/1.0.0",
        "exported_at": timezone.now(),
        "account": {"email": view["email"]},
        "identity": {
            key: view[key]
            for key in (
                "first_name",
                "middle_names",
                "first_surname",
                "second_surname",
                "preferred_name",
                "birth_date",
                "data_status",
                "verification_method",
            )
        },
    }
