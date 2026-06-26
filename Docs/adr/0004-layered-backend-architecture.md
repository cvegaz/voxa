# 0004. Layered backend architecture

- **Date**: 2026-06-26
- **Status**: Accepted

## Context

The backend handles several concerns: HTTP, business logic (transcription, LLM
extraction/enrichment, validation, Excel writing), and data persistence. Without a
clear separation, these tend to bleed into each other — routes accrue logic,
services reach into the database, and the code becomes hard to test and change.

## Decision

We will organize `backend/app/` into strict layers with a one-directional
dependency rule (outer depends on inner, never the reverse):

- **`routes/`** — FastAPI endpoints. They orchestrate only; no heavy logic.
  Prefixes: `/api/templates`, `/api/transcriptions`, `/api/extraction`.
- **`services/`** — all domain/business logic (whisper, LLM extraction and
  enrichment, validators, `excel_writer`, orchestrator, `prompt_builder`,
  `response_parser`, …).
- **`repositories/`** — data access (PostgreSQL via `asyncpg`).
- **`models/`** — Pydantic models / data schemas.
- **`migrations/`** — versioned SQL (see ADR-0008).

The OpenAI-backed services accept an optional pre-configured client in their
constructor; when `None`, they build one from `OPENAI_API_KEY`. This dependency
injection is what lets tests substitute a mock client.

## Consequences

- **Positive**: each layer is testable in isolation; responsibilities are obvious;
  new features have a clear home.
- **Negative / trade-offs**: more files and a little ceremony for small changes.
- **Neutral**: the layering is a convention enforced by review, not by tooling.

## Alternatives considered

- **Flat / framework-centric structure** (logic in route handlers) — rejected:
  fast at first, but quickly untestable and tangled.
