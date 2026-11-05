# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

WORKDIR /app

# System deps for hindsight-client (httpx is pure python, but keep build tools minimal)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Seed on first boot if the DB is missing.
RUN mkdir -p data

EXPOSE 8011

# PORT is provided by Render/Fly/Railway; fall back to 8011 locally.
CMD ["sh", "-c", "python -m dejavu.seed --fresh 2>/dev/null; python -m dejavu.web --host 0.0.0.0 --port ${PORT:-8011}"]
