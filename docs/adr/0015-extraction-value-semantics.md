# 0015. Extraction value semantics (absent vs. unmentioned, and date formatting)

- **Date**: 2026-06-29
- **Status**: Accepted

## Context

The LLM extracts a value for each schema column from free-form narration. Two
semantic gaps produced wrong or inconsistent data:

- **Absent vs. unmentioned were conflated.** The prompt told the model to return an
  empty string when it "could not identify a value", so *"the place has no
  parking"* (an explicit zero) and *parking simply never came up* both became
  `""`. Those mean different things and must be distinguishable in the spreadsheet.
- **Dates were inconsistent.** Date-typed columns came back in whatever shape the
  model produced (`17/09/2026`, `2026-09-17`, *"17 de septiembre de 2026"*),
  sometimes with a time component.

## Decision

- **Distinguish explicit absence from omission.** The extraction prompt now
  instructs the model to:
  - use an empty string `""` only when a column is **not mentioned**, and
  - use the zero/none value for the data type (**`0`** for numbers, **`"no"`** for
    booleans) when the text **explicitly states absence** (e.g. *"no parking"*).

  This is reinforced with **few-shot examples**. The distinction is preserved
  end-to-end: `ResponseParser` does not coerce `"0"` and `""` into each other, so
  it survives into the stored record and the exported Excel.
- **Normalize date values.** Values of date-typed columns are normalized in the
  backend at parse time to **`DD-mmm-YYYY`** (e.g. `17-sep-2026`; Spanish month
  abbreviation, no time). Values that cannot be parsed as a date are kept verbatim,
  so unrecognized content is never corrupted.

## Consequences

- **Positive**: the spreadsheet preserves real meaning (a measured `0` is not the
  same as a blank); dates are uniform in both the live table and the downloaded
  `.xlsx`; normalization happens once, server-side, so every consumer is
  consistent.
- **Negative / trade-offs**: the absent-vs-unmentioned behavior depends on the
  model following instructions — few-shot examples make it robust but not 100%
  deterministic. Date parsing is heuristic over a fixed set of numeric and Spanish
  textual formats; exotic inputs fall through unchanged.
- **Neutral**: the API value model stays string-based (camelCase contract,
  ADR-0005); the `0` vs `""` distinction is expressed as strings, not SQL NULL.

## Alternatives considered

- **Format dates only in the frontend** — rejected: the exported Excel (rebuilt
  server-side) would keep the inconsistent raw values, so the two views would
  disagree.
- **Coerce absence in the parser instead of the prompt** — rejected: only the model
  understands whether the narration *meant* "none"; a parser cannot infer intent
  from an empty field.
- **Introduce real NULLs for unmentioned values** — deferred: the current
  empty-string contract is sufficient to distinguish the two cases and avoids
  reworking the value model.
