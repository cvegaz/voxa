# 0005. camelCase API contract with flattened errors

- **Date**: 2026-06-26
- **Status**: Accepted

## Context

The backend is Python (idiomatic `snake_case`) and the frontend is TypeScript
(idiomatic `camelCase`). Left unmanaged, the wire format becomes an inconsistent
mix, and each side litters the other with casing conversions. Separately,
FastAPI's default error shapes are inconvenient for a UI: `HTTPException` can
produce nested `detail` objects, and `RequestValidationError` returns a list of
error objects that a UI cannot render directly.

## Decision

We will make **camelCase the single API contract** on the wire. Pydantic models use
`populate_by_name=True` so they accept snake_case internally while serializing the
agreed camelCase outward.

All errors are flattened — always — to a top-level, camelCase shape:

```json
{ "detail": "<human-readable message>", "errorCode": "<MACHINE_CODE>" }
```

This is enforced centrally by exception handlers in `app/main.py` (for
`StarletteHTTPException` and `RequestValidationError`). Routes never return nested
or snake_case error bodies to the client.

## Consequences

- **Positive**: the frontend consumes one predictable shape; error handling is
  uniform; no ad-hoc casing conversions at call sites.
- **Negative / trade-offs**: a small amount of boilerplate (the handlers and the
  Pydantic config) that must be preserved when adding endpoints.
- **Neutral**: machine-readable `errorCode`s must be kept consistent across the
  codebase.

## Alternatives considered

- **Pass FastAPI's defaults straight through** — rejected: leaks snake_case and
  nested/list error shapes into the UI.
- **Convert casing in the frontend** — rejected: pushes backend concerns onto the
  client and is easy to get wrong per-field.
