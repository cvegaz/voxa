# 0010. Containerized delivery with Docker Compose

- **Date**: 2026-06-26
- **Status**: Accepted

## Context

The app has three runtime parts (PostgreSQL, the FastAPI backend, the React
frontend) plus a migration step. Asking a user — or a recruiter trying the project
— to install Python, Node, and Postgres and wire them together by hand is a poor
first impression and error-prone.

## Decision

We will ship a **Docker Compose** setup that brings up the whole system with one
command (`docker compose up --build`):

- **`db`**: `postgres:16-alpine`, with a `healthcheck`; the backend waits for it to
  be healthy (`depends_on: condition: service_healthy`).
- **`backend`**: built from `backend/Dockerfile`; on startup runs
  `python scripts/migrate.py` **before** `uvicorn` (so the schema is current), with
  `DATABASE_URL` pointed at the `db` service host.
- **`frontend`**: multi-stage build served by Nginx, exposed on `:8080`, proxying
  `/api` to the backend (see ADR-0006).
- Named volumes (`pgdata`, `excel_data`) persist the database and generated `.xlsx`
  files across restarts. The compose project is named `voxa`.

The host maps Postgres to `5433` to avoid colliding with a developer's local
`5432`.

## Consequences

- **Positive**: one-command, reproducible startup on any machine; clean demo story
  for the README; migrations always applied before serving.
- **Negative / trade-offs**: Docker is a prerequisite; the compose file encodes
  some environment specifics that must diverge in production (see ADR-0011).
- **Neutral**: the migrate-then-serve command is inlined in compose (not a shell
  script) to avoid Windows CRLF breaking a shebang inside the Linux container.

## Alternatives considered

- **Manual local setup / per-service READMEs** — rejected: high friction, poor
  first impression.
- **A single mega-container** — rejected: couples unrelated lifecycles and loses
  the healthcheck/ordering guarantees.
