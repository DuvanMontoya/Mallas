# ADR-0011 — Django 6.0.8 por compatibilidad con Django Ninja

**Estado:** ACCEPTED  
**Fecha:** 2026-08-15

## Contexto

La verificación oficial confirmó que Django 6.1 ya tiene release notes, pero la versión estable resuelta de `django-ninja` (1.6.2) declara el límite `django < 6.1`. El resolver de `uv` rechazó la combinación antes de instalarla.

## Decisión

Usar Django 6.0.8, la última patch estable de la serie compatible con Django Ninja 1.6.2, y mantener el backend preparado para una actualización posterior cuando Django Ninja publique compatibilidad con 6.1.

## Consecuencias

- Se conserva el contrato OpenAPI tipado y el framework preferido por el proyecto.
- Python 3.14 sigue soportado por Django 6.0.
- La actualización a Django 6.1 queda condicionada a una resolución reproducible y pruebas completas; no se introduce una prerelease ni un fork.

## Evidencia

- `uv lock` del 2026-08-15: `django-ninja==1.6.2` exige `django>=3.1,<6.1`.
- [Django 6.0 release notes](https://docs.djangoproject.com/en/6.0/releases/).
- [Django Ninja package metadata](https://pypi.org/project/django-ninja/).
