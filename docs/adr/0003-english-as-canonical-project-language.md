# 0003. English as the canonical project language

- **Date**: 2026-06-26
- **Status**: Accepted

## Context

The codebase was written by a Spanish-speaking author and originally mixed Spanish
and English in comments, docstrings, and documentation. For a public repository
aimed at an international audience (and recruiters), the surrounding prose should
be in one professional language. American English is the de-facto standard for
open-source code.

A separate, harder question is the language of **runtime behavior** — the UI text
the end user reads and the prompts sent to the LLM — which currently target
Spanish users.

## Decision

We will use **American English** as the canonical language for everything that is
*about* the code: identifiers, code comments, docstrings, and all documentation
(`README`, `CLAUDE.md`, `.kiro/specs`, ADRs).

We will **not** translate runtime-behavioral Spanish at this stage: user-facing UI
strings, error messages, and LLM prompts remain in Spanish because they affect
product behavior and are coupled to the current Spanish-first user base. Making
these language-configurable is tracked separately (see ADR-0012).

## Consequences

- **Positive**: the repo reads as a coherent, professional English codebase;
  contributors anywhere can work in it.
- **Negative / trade-offs**: a temporary inconsistency — English code wrapping
  Spanish UI/prompt strings — until i18n lands.
- **Neutral**: a few Spanish domain identifiers remain by design as glossary terms
  in the specs (e.g. `Esquema_Columnas`, `Tipo_Dato`).

## Alternatives considered

- **Translate everything now, including UI and prompts** — rejected: that is a
  behavioral change (it would shift the product's language and require prompt
  re-validation), out of scope for a documentation/quality pass.
- **Stay bilingual** — rejected: unprofessional for a public flagship repo.
