from __future__ import annotations

from django.db import connection
from ninja import NinjaAPI, Schema


class HealthResponse(Schema):
    status: str
    service: str
    version: str


class ReadyResponse(Schema):
    status: str
    service: str
    database: str


api = NinjaAPI(
    title="Curriculum Navigator API",
    version="1.0.0",
    description="API versionada para navegación curricular y planificación académica explicable.",
    urls_namespace="curriculum_navigator_api",
)


@api.get("/health/live", response=HealthResponse, tags=["Operations"])
def live_health(request: object) -> dict[str, str]:
    del request
    return {"status": "ok", "service": "api", "version": "0.1.0"}


@api.get("/health/ready", response=ReadyResponse, tags=["Operations"])
def ready_health(request: object) -> dict[str, str]:
    del request
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return {"status": "ready", "service": "api", "database": "ok"}
