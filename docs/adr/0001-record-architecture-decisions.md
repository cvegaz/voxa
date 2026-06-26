# 0001. Record architecture decisions

- **Date**: 2026-06-26
- **Status**: Accepted

## Context

Voxa is moving from a personal project toward a public, "flagship" portfolio
product. As the codebase grows, the rationale behind its design lives only in the
author's head, in commit messages, and partially in `CLAUDE.md`. That knowledge is
easy to lose and hard for an outside reader to reconstruct.

Good architectural practice is to make decisions — and their trade-offs —
explicit and durable.

## Decision

We will keep **Architecture Decision Records** under `docs/adr/`, one Markdown file
per significant decision, using Michael Nygard's lightweight format. ADRs are
numbered sequentially and are immutable once accepted: a decision that changes is
captured by a new ADR that supersedes the old one rather than by editing history.

The initial set of ADRs (0002–0012) back-fills the decisions already made so far.

## Consequences

- **Positive**: design rationale is discoverable; onboarding and code review are
  faster; the repo signals engineering maturity to readers.
- **Negative / trade-offs**: a small ongoing discipline cost — non-trivial
  decisions now warrant a short write-up.
- **Neutral**: ADRs complement, not replace, `CLAUDE.md` (operational guide) and
  the `.kiro/specs/` design specs (per-module requirements/design).

## Alternatives considered

- **No formal record** — keep relying on commit messages and tribal knowledge.
  Rejected: does not scale and undermines the professionalism goal.
- **A single decision-log file** — simpler, but mixes unrelated decisions, grows
  unwieldy, and loses per-decision status/supersession. Rejected in favor of one
  file per decision.
