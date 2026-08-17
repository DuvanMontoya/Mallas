# IDOR/BOLA negative test matrix

The API must return no private data or mutation success merely because the
caller knows a UUID. Every row is an ownership/scope decision made in the
backend; the frontend is not part of the security boundary.

| Resource/action | Owner or scope | Negative case | Expected result | Evidence |
|---|---|---|---|---|
| `GET /api/v1/academic-overview?enrollment_id=` | student, assigned advisor, scoped admin | unrelated student | `403`/safe not-found, no audit payload | `test_academic_overview.py`, identity ownership tests |
| `GET /api/v1/history/imports/{id}` | enrollment owner/advisor/admin | another student's batch | `403` with stable Problem Details | `test_student_history.py` |
| `POST /api/v1/history/imports/{id}/confirm` | enrollment editor | another student's batch | `403`, no attempt/audit mutation | `test_student_history.py` |
| `PATCH/DELETE /api/v1/history/attempts/{id}` | student owner or scoped admin | another student's attempt | `403`, original attempt unchanged | `test_student_history.py` |
| `GET/PATCH /api/v1/planning/scenarios/{id}` | scenario owner | another user's scenario | `403`/safe not-found | `test_planning.py` |
| share/revoke scenario | scenario owner | another user's scenario/share token | `403`, token unchanged | `test_planning.py` |
| `GET /api/v1/governance/proposals/{id}` | scoped editor/reviewer/admin | unrelated program or student | `403`, no source/proposal disclosure | `test_governance_backoffice.py` |
| governance review/publish | scoped reviewer/admin plus lifecycle state | editor, submitter, stale version | `403`/`409`, no publication receipt | `test_governance_backoffice.py`, `test_publication_impact.py` |
| institutional analytics/export | explicit institution/program scope | student/advisor or omitted scope | `403`/validation error, no row-level PII | `test_analytics.py` |
| notifications/{id} read/preferences | recipient user | delivery belonging to another recipient | safe not-found/`403`, no body | `test_notifications.py` |
| curriculum source snapshots | editorial role | student or unrelated role | `403`, raw bytes remain private | governance API tests |

## Required repeatability

```powershell
$env:DATABASE_URL='postgresql://curriculum:curriculum_local_only@127.0.0.1:5432/curriculum'
uv run --frozen python -m pytest -q tests/test_identity_security.py tests/test_student_history.py tests/test_planning.py tests/test_governance_backoffice.py tests/test_analytics.py tests/test_notifications.py
```

The same checks run in SQLite in the canonical verification suite. PostgreSQL
adds trigger and transaction coverage for the production database boundary.
