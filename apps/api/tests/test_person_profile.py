from __future__ import annotations

import datetime
import importlib

from django.apps import apps as django_apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from modules.identity.models import (
    AuditEvent,
    BirthDatePurpose,
    IdentityDataStatus,
    IdentityVerificationMethod,
    PersonProfile,
    User,
)


class PersonProfileTests(TestCase):
    def test_normalizes_structured_name_and_derives_age(self) -> None:
        user = User.objects.create(email="person@example.test")
        profile = PersonProfile.objects.create(
            user=user,
            first_name="  Ana  ",
            middle_names=" María   Fernanda ",
            first_surname=" López ",
            second_surname=" Ruiz ",
            birth_date=datetime.date(2004, 8, 19),
            birth_date_purpose=BirthDatePurpose.ACADEMIC_ADMINISTRATION,
            data_status=IdentityDataStatus.CONFIRMED,
            verification_method=IdentityVerificationMethod.INSTITUTION_VERIFIED,
        )

        self.assertEqual(profile.full_name, "Ana María Fernanda López Ruiz")
        self.assertEqual(profile.age_on(datetime.date(2026, 8, 18)), 21)
        self.assertEqual(profile.age_on(datetime.date(2026, 8, 19)), 22)

    def test_confirmed_identity_requires_first_name_and_first_surname(self) -> None:
        user = User.objects.create(email="incomplete@example.test")
        profile = PersonProfile(user=user, data_status=IdentityDataStatus.CONFIRMED)

        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_birth_date_requires_purpose_and_rejects_future_date(self) -> None:
        user = User.objects.create(email="birth-date@example.test")
        missing_purpose = PersonProfile(
            user=user,
            first_name="Ana",
            first_surname="López",
            birth_date=datetime.date(2004, 8, 19),
            data_status=IdentityDataStatus.CONFIRMED,
            verification_method=IdentityVerificationMethod.INSTITUTION_VERIFIED,
        )
        with self.assertRaises(ValidationError):
            missing_purpose.full_clean()

        missing_purpose.birth_date = datetime.date.today() + datetime.timedelta(days=1)
        missing_purpose.birth_date_purpose = BirthDatePurpose.ACADEMIC_ADMINISTRATION
        with self.assertRaises(ValidationError):
            missing_purpose.full_clean()

    def test_backfill_reverse_preserves_profiles_rectified_after_migration(self) -> None:
        migration = importlib.import_module(
            "modules.student_records.migrations.0007_backfill_person_profiles"
        )
        placeholder_user = User.objects.create(email="placeholder@example.test")
        placeholder = PersonProfile.objects.create(
            user=placeholder_user,
            data_status=IdentityDataStatus.LEGACY_UNSTRUCTURED,
            metadata={"backfilled_from_student_profile": "placeholder"},
        )
        rectified_user = User.objects.create(email="rectified@example.test")
        rectified = PersonProfile.objects.create(
            user=rectified_user,
            first_name="Ana",
            first_surname="Persona",
            birth_date=datetime.date(2000, 1, 1),
            birth_date_purpose=BirthDatePurpose.ACADEMIC_ADMINISTRATION,
            data_status=IdentityDataStatus.CONFIRMED,
            verification_method=IdentityVerificationMethod.SELF_DECLARED,
            metadata={"backfilled_from_student_profile": "rectified"},
        )

        migration.reverse_backfill(django_apps, None)

        self.assertFalse(PersonProfile.objects.filter(pk=placeholder.pk).exists())
        self.assertTrue(PersonProfile.objects.filter(pk=rectified.pk).exists())

    def test_database_rejects_bulk_update_to_incomplete_confirmed_identity(self) -> None:
        profile = PersonProfile.objects.create(
            user=User.objects.create(email="constraint@example.test"),
            data_status=IdentityDataStatus.LEGACY_UNSTRUCTURED,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            PersonProfile.objects.filter(pk=profile.pk).update(
                data_status=IdentityDataStatus.CONFIRMED
            )

    def test_verification_migration_classifies_only_from_audit_evidence(self) -> None:
        migration = importlib.import_module(
            "modules.identity.migrations.0010_person_identity_verification_constraints"
        )

        def confirmed(email: str) -> PersonProfile:
            return PersonProfile.objects.create(
                user=User.objects.create(email=email),
                first_name="Ana",
                first_surname="Persona",
                birth_date=datetime.date(2000, 1, 1),
                birth_date_purpose=BirthDatePurpose.ACADEMIC_ADMINISTRATION,
                data_status=IdentityDataStatus.CONFIRMED,
                verification_method=IdentityVerificationMethod.SELF_DECLARED,
            )

        unknown = confirmed("unknown-origin@example.test")
        self_declared = confirmed("self-origin@example.test")
        institution = confirmed("institution-origin@example.test")
        AuditEvent.objects.create(
            action="PERSON_IDENTITY_SELF_RECTIFIED",
            object_type="PersonProfile",
            object_id=str(self_declared.pk),
        )
        AuditEvent.objects.create(
            action="PERSON_IDENTITY_RECTIFIED",
            object_type="PersonProfile",
            object_id=str(institution.pk),
        )

        migration.classify_existing_confirmed_profiles(django_apps, None)

        unknown.refresh_from_db()
        self_declared.refresh_from_db()
        institution.refresh_from_db()
        self.assertEqual(
            unknown.verification_method,
            IdentityVerificationMethod.PREEXISTING_UNCLASSIFIED,
        )
        self.assertEqual(
            self_declared.verification_method, IdentityVerificationMethod.SELF_DECLARED
        )
        self.assertEqual(
            institution.verification_method,
            IdentityVerificationMethod.INSTITUTION_VERIFIED,
        )
