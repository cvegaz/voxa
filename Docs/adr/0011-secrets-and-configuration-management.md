# 0011. Secrets and configuration management

- **Date**: 2026-06-26
- **Status**: Accepted

## Context

Voxa holds a high-value secret: `OPENAI_API_KEY`, which maps directly to real
money on every call (ADR-0007). It also has environment-specific configuration
(`DATABASE_URL`, database credentials). A public repository raises the stakes —
one leaked key in git history is a costly, hard-to-undo mistake.

## Decision

We will keep secrets **out of the repository** and configuration **environment-driven**:

- `backend/.env` holds real values, is listed in `.gitignore`, and is **never
  committed**; `backend/.env.example` documents the variables with empty values.
- `OPENAI_API_KEY` is never hardcoded in code, tests, `docker-compose.yml`, the
  README, or screenshots.
- Inside Docker, `DATABASE_URL` is overridden in `docker-compose.yml` to point at
  the `db` service host (Compose `environment` takes precedence over `env_file`).
- The `postgres/postgres` credentials and the compose password are **development-only**.
- A monthly spending cap is set in the OpenAI dashboard as a safety net.

For real deployment (tracked as Phase C in `todo.md`), secrets come from the
hosting provider's secrets manager — not a versioned `.env` — and production uses a
separate `DATABASE_URL` and a strong database password.

## Consequences

- **Positive**: drastically reduces the risk of leaking a billable key; clean
  separation of config from code; safe to open the repo publicly.
- **Negative / trade-offs**: contributors must create their own `.env` from the
  example; production needs a real secrets-manager integration before exposure.
- **Neutral**: if a key is ever committed, the response is non-negotiable — rotate
  the key and scrub history (git-filter-repo / BFG).

## Alternatives considered

- **Committing a `.env` or default keys for convenience** — rejected outright: a
  public, billable-secret leak.
