# syntax=docker/dockerfile:1.10

ARG PYTHON_IMAGE=python:3.14-slim@sha256:ce40764625a4ff50df3548277632e7f96c4e77fe75fa848aae9885476e7df5a4
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.11.19@sha256:b46b03ddfcfbf8f547af7e9eaefdf8a39c8cebcba7c98858d3162bd28cf536f6

FROM ${UV_IMAGE} AS uv

FROM ${PYTHON_IMAGE} AS build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1
COPY --from=uv /uv /uvx /usr/local/bin/
WORKDIR /app
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY apps/api/ ./
RUN uv sync --frozen --no-dev \
    && .venv/bin/python manage.py collectstatic --noinput

FROM ${PYTHON_IMAGE} AS runtime
ARG APP_VERSION=0.1.0
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    DJANGO_SETTINGS_MODULE=config.settings \
    APP_VERSION=${APP_VERSION} \
    PATH=/app/.venv/bin:$PATH
WORKDIR /app
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid 10001 --home-dir /app --shell /usr/sbin/nologin app \
    && mkdir -p /app/var/private-imports /staticfiles \
    && chown -R app:app /app /staticfiles
COPY --from=build --chown=app:app /app/.venv /app/.venv
COPY --from=build --chown=app:app /app/config /app/config
COPY --from=build --chown=app:app /app/domain /app/domain
COPY --from=build --chown=app:app /app/modules /app/modules
COPY --from=build --chown=app:app /app/manage.py /app/manage.py
COPY --from=build --chown=app:app /staticfiles /staticfiles
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import socket; s=socket.create_connection(('127.0.0.1', 8000), 2); s.close()"]
STOPSIGNAL SIGTERM
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
