# 0002. Product name and scope: Voxa

- **Date**: 2026-06-26
- **Status**: Accepted

## Context

The project was bootstrapped under the working name `my-data-app`, a generic
placeholder that appeared in the folder name, `package.json`, the API title, and
the UI. A public product needs a single, memorable identity used consistently
everywhere.

The product's scope is also worth stating plainly: capture data by **audio
narration** and persist it into an **Excel file**, using an LLM to extract the
structured fields that match a user-provided template.

## Decision

We will name the product **Voxa** and use that name consistently across the repo:
project folder, `package.json` (`voxa-frontend`), the FastAPI title (`Voxa API`),
the document title, and the in-app heading. The legacy `my-data-app` identifier is
retired.

The product scope is fixed as: *Excel template in → audio narration → transcription
→ LLM field extraction → row written back into the Excel file.*

## Consequences

- **Positive**: one coherent brand; easier to talk about, link, and showcase.
- **Negative / trade-offs**: stray references to the old name may linger (e.g.
  comments in `docker-compose.yml`); these are cleaned up as found.
- **Neutral**: the on-disk folder rename to `voxa` is performed when the editor is
  closed (the folder is locked while open as a workspace).

## Alternatives considered

- **Keep `my-data-app`** — rejected: generic, unmemorable, signals "unfinished".
