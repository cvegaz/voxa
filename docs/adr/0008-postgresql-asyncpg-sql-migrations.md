# 0008. PostgreSQL with asyncpg and SQL migrations

- **Date**: 2026-06-26
- **Status**: Accepted

## Context

The backend is fully async (FastAPI + `uvicorn`) and needs durable storage for
sessions, schemas, transcriptions, and extracted records. We want predictable
schema evolution that is reviewable and reproducible across environments, without
hiding SQL behind an ORM abstraction.

## Decision

We will use **PostgreSQL** (16) accessed with **`asyncpg`** through a connection
pool created on application startup (`lifespan`) and closed on shutdown.

Schema changes are managed as **plain, versioned SQL migrations**: `migrations/00N_*.sql`
each paired with a `_rollback.sql`. They are applied by `scripts/migrate.py`, which
runs at container startup *before* `uvicorn` serves traffic.

## Consequences

- **Positive**: full control over SQL; migrations are explicit, diff-friendly, and
  reproducible; the async driver fits the stack; rollbacks are first-class.
- **Negative / trade-offs**: no ORM conveniences (relations, lazy loading); SQL is
  hand-written and migrations are applied by a custom runner rather than a managed
  tool.
- **Neutral**: production must point `DATABASE_URL` at a separate database from dev
  (see ADR-0011).

## Alternatives considered

- **SQLAlchemy + Alembic** — rejected for now: heavier abstraction than this
  project needs; the team prefers explicit SQL.
- **A non-relational store** — rejected: the data is tabular and relational by
  nature (it ends up in a spreadsheet).
