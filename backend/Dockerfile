FROM python:3.12-slim AS base
WORKDIR /app/backend
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# tesseract-ocr: the system binary pytesseract shells out to for the OCR
# fallback path (app.services.extraction.ocr) - not pip-installable, so it
# needs its own apt-get step rather than living in pyproject.toml.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir -e .

# Local development target (unchanged from before this file had stages):
# root user, --reload, source overlaid by docker-compose.yml's bind mount.
# docker-compose.yml pins `target: dev` explicitly - without that pin, a
# multi-stage Dockerfile with no --target defaults to building the *last*
# stage (production), which would silently break local dev.
FROM base AS dev
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production target: no --reload, non-root. Runs as a fixed unprivileged
# numeric UID (rather than a named user via useradd) so it doesn't depend on
# user-management tools being present in the slim base image; the app only
# reads/writes paths passed in via UPLOAD_ROOT/REPORT_ROOT/KB_SOURCE_DIR, so
# it never needs a real home directory or /etc/passwd entry.
FROM base AS production
USER 10001:10001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
