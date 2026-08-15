# ─────────────────────────────────────────────────────────────────────────────
# Backend image (FastAPI). Recipe for building the API container.
# Each instruction creates a "layer"; Docker caches them to speed up rebuilds.
# ─────────────────────────────────────────────────────────────────────────────

# Base image: Python 3.12 "slim" = minimal Debian with Python. Light and enough
# (asyncpg, pandas, and openpyxl ship precompiled wheels, so no compiling needed).
FROM python:3.12-slim

# Variables that improve Python's behavior inside containers:
#   PYTHONUNBUFFERED        -> logs are emitted immediately (not buffered)
#   PYTHONDONTWRITEBYTECODE -> no .pyc files (needless clutter in the image)
#   PIP_NO_CACHE_DIR        -> pip keeps no cache (smaller image)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# ffmpeg supplies `ffprobe`, which measures an uploaded recording's REAL duration
# (ADR-0019). This is a hard runtime dependency of the cost control, not a
# convenience: without it every transcription is rejected as unmeasurable, because
# the validator fails closed. Placed BEFORE the pip layer so editing requirements
# does not re-run apt.
#   --no-install-recommends trims the dependency tree substantially.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Working directory inside the container. Everything else is relative to here.
WORKDIR /app

# CACHE TRICK: copy ONLY requirements.txt first and install. Since this layer
# only changes when the dependencies change, Docker reuses the already-cached
# install while you edit code (which is copied afterwards).
COPY requirements.txt .
RUN pip install -r requirements.txt

# Now copy the rest of the backend code.
# (The .dockerignore keeps .env, .venv, tests, etc. out.)
COPY . .

# Documents that the process listens on 8000 (uvicorn). Informational only;
# the actual port publishing is done in docker-compose.yml.
EXPOSE 8000

# Default command if the image is run on its own. In compose we override it to
# run the migrations first.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
