# 0009. Test-driven development

- **Date**: 2026-06-26
- **Status**: Accepted

## Context

The system has many moving parts that are easy to break silently: the API
contract (ADR-0005), Excel parsing/writing, LLM response parsing, and validation
rules. A regression in any of these corrupts user data or breaks the flow. For a
showcase repository, a visible, healthy test suite is also a strong quality signal.

## Decision

We will practice **test-first development**, keeping a broad automated suite:

- **Backend**: `pytest` with `hypothesis` (property-based tests where it adds
  value). Each service and endpoint has a corresponding test; OpenAI clients are
  injected as mocks (see ADR-0004 / ADR-0007).
- **Frontend**: `vitest` with Testing Library.

When logic changes, the corresponding test is updated or added — functionality is
not left uncovered.

## Consequences

- **Positive**: regressions are caught early; the contract and parsing edge cases
  are pinned; the suite documents expected behavior and reassures readers.
- **Negative / trade-offs**: tests are part of the cost of every change; mocks for
  external APIs must be maintained.
- **Neutral**: tests run locally (`pytest`, `npm test`) and are the natural basis
  for a future CI pipeline (`todo.md`).

## Alternatives considered

- **Manual / ad-hoc testing only** — rejected: does not scale and provides no
  regression safety net for data-integrity-critical code.
