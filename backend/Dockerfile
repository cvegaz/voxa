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
