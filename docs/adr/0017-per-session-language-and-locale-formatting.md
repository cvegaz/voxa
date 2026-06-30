# 0017. Per-session language and locale formatting

- **Date**: 2026-06-30
- **Status**: Accepted

## Context

ADR-0012 set the direction for end-to-end multi-language support, and ADR-0016
delivered the UI i18n (Spanish/English switcher). This ADR records the concrete
decisions made while implementing the **backend pipeline** so a record is
processed in one language from narration to spreadsheet (todo #8).

Supported languages: **Spanish (default) and English.**

## Decision

- **Language is per-session and fixed at confirm.** It is stored on
  `template_sessions.language` (migration 006). When the user confirms the
  template, the UI sends its current language; from then on transcription
  (Whisper), enrichment, and extraction all read the **session** language.
  Switching the UI language afterwards does **not** change a confirmed session,
  so every row of a session is in one language.
- **Prompts are language-specific.** `PromptBuilder.build()` and
  `LLMEnrichmentService.enrich()` emit Spanish or English templates; the enriched
  context is generated in the session language.
- **Dates are formatted per language.** The normalizer reads numeric input as
  DD/MM in Spanish and MM/DD in English, and outputs `DD-mmm-YYYY`
  (`17-sep-2026`) for Spanish and `MM/DD/YYYY` (`09/17/2026`) for English. The
  session language flows orchestrator → `ResponseParser` → `date_normalizer`.
- **Numbers are left as-is** (no decimal/thousands-separator normalization), to
  avoid mis-reading an ambiguous separator and corrupting a value.
- **Booleans** are handled by the extraction prompt (the model returns the
  localized value, or `"no"` for an explicitly-absent boolean); there is no
  separate normalization layer.
- **Error messages** are localized at the **frontend** by `errorCode` (ADR-0016);
  the backend `detail` strings are intentionally left in Spanish because the
  frontend replaces them (they only surface in logs / Swagger / rare passthroughs).

## Consequences

- **Positive**: a confirmed session is fully consistent in one language end to
  end; date output is predictable and locale-familiar; minimal data-corruption
  risk because numbers are untouched.
- **Negative / trade-offs**: a session cannot mix languages across rows (by
  design); the normalizer's locale handling is a fixed ES/EN heuristic; backend
  `detail` strings remain Spanish (invisible to end users, but present in logs).
- **Neutral**: adding a third language means extending the prompt templates, the
  month tables in `date_normalizer`, and the UI catalog — no architectural change.

## Alternatives considered

- **Language follows the UI live (per request)** — rejected: a single session
  could then mix languages across rows; fixing it at confirm gives clean
  per-session semantics.
- **Locale-aware number parsing** — rejected: ambiguous separators (`1.000`) risk
  silently corrupting values; left as-is.
- **ISO dates (`YYYY-MM-DD`) for both languages** — considered; we chose the
  locale-familiar forms instead (Spanish `DD-mmm-YYYY`, English `MM/DD/YYYY`).

This ADR implements ADR-0012; see also ADR-0016 (UI i18n).
