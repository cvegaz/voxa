# 0012. Multi-language strategy (end-to-end)

- **Date**: 2026-06-26
- **Status**: Accepted — implemented by ADR-0016 (UI) and ADR-0017 (backend pipeline)

## Context

Voxa is currently Spanish-first in its runtime behavior: the UI strings, the error
messages, the LLM prompts, and the Whisper configuration (`LANGUAGE = "es"`) are
hardcoded to Spanish. ADR-0003 made the *code and docs* English but deliberately
left runtime language untouched.

To serve an international audience — and to back the goal of a flagship product —
the app should work in **any language end to end**, not merely translate the UI
chrome. Spoken input, the prompts that interpret it, and the way values are parsed
and written into the spreadsheet are all language- and locale-sensitive.

## Decision

We will treat full multi-language support as a planned architectural direction
(detailed as items #7 and #8 in `todo.md`). The intended shape:

- **Language as session state**: persist the chosen/detected language on the
  session (DB column + migration) so transcription, extraction, and output stay
  consistent for a given record.
- **Transcription**: drive Whisper from the session language or use auto-detection,
  replacing the hardcoded `LANGUAGE = "es"`.
- **LLM prompts**: make `prompt_builder` / `llm_enrichment_service` prompts
  language-aware via per-language templates.
- **Schema type names**: recognize template data-type words
  (`texto`, `número entero`, `fecha DD/MM/YYYY`, `booleano`) per language, or
  normalize to a language-agnostic internal enum.
- **Locale-aware parsing/formatting** when writing Excel — the riskiest part, where
  a mis-parsed value silently corrupts data:
  - dates (`DD/MM/YYYY` vs `MM/DD/YYYY`),
  - numbers (decimal/thousands separators: `1.000,50` vs `1,000.50`),
  - booleans (`sí/no`, `yes/no`, `true/false`).
- **UI i18n**: externalize all strings with a language selector / browser detection
  and a sensible default.
- **Tests and docs**: fixtures per language (at least ES + EN) across the pipeline,
  and a documented list of supported languages.

## Status note

This ADR is **Proposed**: it records the agreed direction and its scope, not a
shipped implementation. It will move to **Accepted** when the work is scheduled and
the first language beyond Spanish is wired through.

## Consequences

- **Positive**: opens Voxa to an international user base; forces the pipeline to
  stop assuming a single locale, which is sounder design overall.
- **Negative / trade-offs**: significant cross-cutting work touching DB, services,
  prompts, and the writer; locale-aware parsing is subtle and must be tested
  carefully to avoid silent data corruption.
- **Neutral**: ties together ADR-0003 (English code/docs) and the runtime-language
  concern it intentionally deferred.

## Alternatives considered

- **UI-only translation** — rejected as insufficient: the user could read English
  buttons but still be unable to narrate and store a record correctly in their
  language.
- **Stay Spanish-only** — rejected: caps the product's reach and its showcase value.
