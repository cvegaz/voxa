# 0006. Relative API paths via a reverse proxy

- **Date**: 2026-06-26
- **Status**: Accepted

## Context

The frontend needs to reach the backend in three environments — local dev, Docker
Compose, and a future production host — each with different host/port topology.
Hardcoding absolute backend URLs (or threading them through env vars into the
browser bundle) is brittle and invites CORS problems.

## Decision

The frontend will call **relative `/api/...` paths only**, never absolute backend
URLs. The routing is handled by a reverse proxy at the edge:

- **Development**: Vite's dev-server proxy (`vite.config.ts`) forwards `/api` to
  `http://localhost:8000`.
- **Production**: Nginx (`frontend/nginx.conf`) proxies `/api` to the backend
  service.

Because the browser only ever talks to its own origin, CORS is sidestepped in the
common path.

## Consequences

- **Positive**: the same frontend build works in every environment; no
  backend-URL configuration baked into the bundle; CORS largely avoided.
- **Negative / trade-offs**: the proxy is now part of the contract — e.g. the
  `proxy_pass` trailing-slash behavior in Nginx must be kept correct (noted in
  `CLAUDE.md`).
- **Neutral**: anonymous public exposure still requires CORS lockdown at the edge
  (see ADR-0011 / Phase C in `todo.md`).

## Alternatives considered

- **Absolute backend URLs via env vars** — rejected: per-environment rebuilds,
  CORS handling, and leakage of internal topology into the client.
