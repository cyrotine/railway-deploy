# ── VeriFlow Backend ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ── Install system dependencies (Tesseract for OCR) ────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# ── Install Python dependencies ─────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy application source ────────────────────────────────────────────────
COPY main.py config.py orchestrator.py sanitization.py ./
COPY agents/ ./agents/

# ── Expose & run ────────────────────────────────────────────────────────────
EXPOSE 8000

# Use shell form so $PORT is expanded at runtime (Railway injects PORT)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}