FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random

WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY apps/api/pyproject.toml /app/pyproject.toml
COPY apps/api/uv.lock /app/uv.lock
RUN pip install --no-cache-dir uv==0.11.19 && uv sync --frozen --no-dev
COPY apps/api /app
RUN chown -R app:app /app
USER app
EXPOSE 8000
CMD ["uv", "run", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
