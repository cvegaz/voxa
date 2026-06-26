# 0007. OpenAI for transcription and extraction

- **Date**: 2026-06-26
- **Status**: Accepted

## Context

Voxa's core depends on two AI capabilities: speech-to-text (transcribe the user's
narration) and structured field extraction (turn free text plus a column schema
into typed values). An earlier iteration used the Anthropic Claude API for the
text/extraction step. We wanted a single provider for both capabilities to reduce
operational surface and key management.

## Decision

We will use **OpenAI** for the entire AI pipeline:

- **Transcription**: Whisper (`whisper-1`).
- **Context enrichment and field extraction**: `gpt-4o-mini`.

The codebase was migrated from Anthropic Claude to OpenAI for the
enrichment/extraction step (commit `d605406`). Each OpenAI-backed service:

- accepts an optional `AsyncOpenAI` client for testability (see ADR-0004);
- translates transient failures (connection/timeout/5xx) into **domain
  exceptions** (`exceptions.py`: `LLMUnavailableError`, `LLMInvalidResponseError`,
  `WhisperUnavailableError`, …) and **retries** transient errors with exponential
  backoff.

## Consequences

- **Positive**: one vendor, one key, one SDK; consistent error handling and retry
  strategy; mockable in tests.
- **Negative / trade-offs**: vendor lock-in to OpenAI; **every call spends real
  money** (`OPENAI_API_KEY` = real cost), which drives the abuse/cost controls in
  ADR-0011; external dependency and data leaving the system (privacy implications
  noted in `todo.md` Phase C).
- **Neutral**: model IDs (`whisper-1`, `gpt-4o-mini`) are pinned constants and can
  be revised as OpenAI's lineup evolves.

## Alternatives considered

- **Anthropic Claude** (previous choice) — superseded to consolidate on one
  provider for both speech and text.
- **Local model via Ollama (LLaMA/Mistral)** — deferred; tracked as a future item
  in `todo.md` to remove external-API cost and dependency. Requires evaluating
  extraction quality vs. hosted models.
