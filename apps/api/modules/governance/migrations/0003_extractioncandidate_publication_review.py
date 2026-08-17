from __future__ import annotations

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("curriculum", "0004_published_revision_metadata_immutability"),
        ("governance", "0002_changeproposal"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ExtractionCandidate",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("entity", models.CharField(max_length=80)),
                ("entity_key", models.CharField(max_length=240)),
                ("operation", models.CharField(max_length=16)),
                ("before", models.JSONField(blank=True, null=True)),
                ("after", models.JSONField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("ACCEPTED", "Accepted"),
                            ("REJECTED", "Rejected"),
                        ],
                        default="PENDING",
                        max_length=16,
                    ),
                ),
                (
                    "epistemic_status",
                    models.CharField(
                        choices=[
                            ("VERIFIED", "Verified"),
                            ("DERIVED", "Derived"),
                            ("INFERRED_PENDING_REVIEW", "Inferred Pending Review"),
                            ("UNKNOWN", "Unknown"),
                            ("DISPUTED", "Disputed"),
                            ("SUPERSEDED", "Superseded"),
                        ],
                        default="INFERRED_PENDING_REVIEW",
                        max_length=32,
                    ),
                ),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("note", models.TextField(blank=True)),
                (
                    "evidence",
                    models.ManyToManyField(
                        blank=True, related_name="extraction_candidates", to="governance.evidence"
                    ),
                ),
                (
                    "proposal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="extraction_candidates",
                        to="governance.changeproposal",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reviewed_extraction_candidates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "source_snapshot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="extraction_candidates",
                        to="governance.sourcesnapshot",
                    ),
                ),
            ],
            options={
                "ordering": ["entity", "entity_key", "operation"],
                "indexes": [
                    models.Index(
                        fields=["proposal", "status"], name="candidate_proposal_status_idx"
                    ),
                    models.Index(
                        fields=["source_snapshot", "entity"], name="candidate_snapshot_entity_idx"
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("proposal", "entity", "entity_key", "operation"),
                        name="extraction_candidate_identity_unique",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="Publication",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("published_at", models.DateTimeField()),
                ("content_hash", models.CharField(max_length=128)),
                ("source_set_hash", models.CharField(max_length=128)),
                ("validation_report", models.JSONField(default=dict)),
                ("semantic_diff", models.JSONField(default=dict)),
                ("confirmation", models.TextField()),
                (
                    "proposal",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="publication",
                        to="governance.changeproposal",
                    ),
                ),
                (
                    "published_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="curriculum_publications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "revision",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="publication",
                        to="curriculum.curriculumrevision",
                    ),
                ),
            ],
            options={
                "ordering": ["-published_at", "-id"],
                "indexes": [
                    models.Index(fields=["published_at"], name="publication_time_idx"),
                    models.Index(
                        fields=["published_by", "published_at"], name="publication_actor_time_idx"
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="Review",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "decision",
                    models.CharField(
                        choices=[
                            ("APPROVE", "Approve"),
                            ("REQUEST_CHANGES", "Request Changes"),
                            ("REJECT", "Reject"),
                        ],
                        max_length=24,
                    ),
                ),
                ("comment", models.TextField(blank=True)),
                ("proposal_version", models.CharField(max_length=80)),
                (
                    "proposal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reviews",
                        to="governance.changeproposal",
                    ),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="curriculum_reviews",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(
                        fields=["proposal", "created_at"], name="review_proposal_time_idx"
                    ),
                    models.Index(
                        fields=["reviewer", "created_at"], name="review_reviewer_time_idx"
                    ),
                ],
            },
        ),
    ]
