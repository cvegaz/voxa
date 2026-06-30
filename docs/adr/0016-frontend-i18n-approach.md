# 0016. Lightweight in-house i18n for the frontend (ES/EN)

- **Date**: 2026-06-29
- **Status**: Accepted

## Context

Voxa shipped Spanish-only in the UI. ADR-0003 kept the code/docs in English but
deliberately left runtime language untouched, and ADR-0012 set the direction for
full multi-language support. The first concrete step is a user-facing **Spanish /
English** switch that (a) translates the whole UI and (b) sets the **expected
input language** for transcription (Whisper).

We needed an i18n mechanism. The project values a small dependency surface (no
state library, hand-written SQL, in-house helpers), and the scope is modest: two
languages and on the order of ~70 UI strings plus the API error copy.

## Decision

We will use a **small in-house i18n layer** instead of a library
(react-i18next / react-intl):

- A flat, typed catalog (`i18n/translations.ts`) with `es` and `en` maps and
  `{token}` interpolation.
- A React context + `useI18n()` hook exposing `{ lang, setLang, t }`. The context
  has a **functional default** (Spanish), so a component rendered without a
  provider (e.g. in unit tests) still translates — no provider boilerplate in
  tests.
- **Default Spanish**, persisted in `localStorage`, and reflected on `<html lang>`.
- A module-level `getCurrentLanguage()` / `localized(es, en)` so code that runs
  **outside the React tree** (the API error mappers in `types/*.ts` and the
  timeout/network errors in `services/*.ts`) can localize too.
- A top-right `LanguageSwitcher` (two pills, ES/EN); the active one is shaded,
  with a hover tooltip ("Usar Voxa en español" / "Use Voxa in English").
- The selected language is **sent per transcription request** and used as
  Whisper's `language`, replacing the previously hardcoded `"es"`.

## Consequences

- **Positive**: no new runtime dependency; tiny bundle cost; type-checked keys; a
  key-parity test guards the catalog; the whole UI and all API error messages
  switch language; transcription accuracy benefits from the correct forced
  language.
- **Negative / trade-offs**: no ICU pluralization/number/date formatting (we only
  need simple token interpolation); API error messages are captured at
  throw-time, so they do not re-translate if the user switches language *after*
  an error is shown; the `es`/`en` maps must be kept in sync (mitigated by the
  parity test).
- **Neutral / out of scope**: the **LLM extraction prompt** is still
  Spanish-instructed and the **date normalizer** still emits Spanish month
  abbreviations regardless of UI language. Those are AI-pipeline concerns tracked
  under ADR-0012 and `todo.md` #8, not UI chrome.

## Alternatives considered

- **react-i18next / react-intl** — rejected: heavier than warranted for two
  languages and a small string set; adds a dependency and config surface the
  project otherwise avoids. Can be revisited if we need plural rules or
  locale-aware formatting at scale.
- **Stay Spanish-only** — rejected: caps the product's reach and its showcase
  value (ADR-0012).
