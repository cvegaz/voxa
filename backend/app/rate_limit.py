"""Shared rate limiter (slowapi) used to protect abuse-prone public endpoints.

Defined in its own module so both ``app.main`` (which registers the limiter and
its error handler on the app) and the route modules (which apply ``@limiter.limit``
decorators) can import the same instance without a circular import.

Client identity behind a reverse proxy (ADR-0019 §9)
----------------------------------------------------
slowapi's default ``get_remote_address`` returns the address of the **immediate
peer**. In production that peer is our own reverse proxy, so every visitor on Earth
would share a single rate-limit bucket and the limit would be inert exactly where it
matters. The real address has to come from ``X-Forwarded-For`` — but that header is
attacker-controlled, so reading it naively is worse than not reading it at all.

The rule: **count from the right, never from the left.** Each proxy we control
*appends* the peer it saw, so with ``h`` proxies of our own the client's real address
sits at ``parts[-h]``. Anything further left was supplied by the caller and may be
pure fiction. A spoofer can prepend a hundred fake entries and never shift the entry
we read, because its position is fixed by our own topology rather than by the
header's length.

Concretely, in the Stage-1 topology (Caddy → frontend nginx → backend) a request
carrying a forged ``X-Forwarded-For: 1.2.3.4`` arrives at the backend as::

    1.2.3.4,        9.9.9.9,          172.18.0.5
    ^ the forgery   ^ seen by Caddy   ^ seen by nginx
                      (the real one)

so ``TRUSTED_PROXY_HOPS=2`` reads ``9.9.9.9``. Reading ``parts[0]`` — the common
mistake — would read the forgery and let anyone reset their own quota at will.
"""

import os

from slowapi import Limiter
from starlette.requests import Request


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc
    if value < 0:
        raise ValueError(f"{name} must be zero or positive, got {value}")
    return value


# How many reverse proxies WE operate in front of the backend. Each one appends an
# entry to X-Forwarded-For.
#
# Default 0 — fail secure. With no proxy configured we use the peer address and
# ignore the header entirely, so a direct-exposure or local-dev deployment cannot be
# spoofed by simply sending a header. Production sets this explicitly (2 for
# Caddy → nginx → backend).
TRUSTED_PROXY_HOPS = _env_int("TRUSTED_PROXY_HOPS", 0)


def client_ip(request: Request) -> str:
    """Return the address to rate-limit on. See the module docstring for the rule."""
    peer = request.client.host if request.client else "unknown"

    if TRUSTED_PROXY_HOPS <= 0:
        return peer

    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return peer

    parts = [part.strip() for part in forwarded.split(",") if part.strip()]

    # Fewer entries than proxies means the chain is not what we were told it is
    # (a misconfiguration, or a request that skipped the proxy). Fall back to the
    # peer: everyone may share a bucket, but nothing is forgeable.
    if len(parts) < TRUSTED_PROXY_HOPS:
        return peer

    return parts[-TRUSTED_PROXY_HOPS]


# Per-IP limiter with in-memory storage (fine for a single-process deployment;
# swap the storage_uri for Redis if the backend is ever scaled horizontally).
limiter = Limiter(key_func=client_ip)

# Limit for the public contact form. Configurable so it can be tightened in
# production without a code change. A human never submits this many per minute;
# the cap exists to blunt automated floods.
CONTACT_RATE_LIMIT = os.getenv("CONTACT_RATE_LIMIT", "30/minute")

# Limits for the endpoints that spend real money on OpenAI — transcription,
# extraction, and template confirmation (confirm triggers the enrichment call, so
# it is billable too).
#
# Two windows on purpose: the hourly cap blunts a burst, the daily one blunts a slow
# drip that would stay under it. A legitimate anonymous trial is one template plus
# three narrations, so neither comes close to being hit by a real visitor.
#
# This is only the FIRST layer. A per-IP limit cannot stop a distributed or
# VPN-rotating caller — that is what the global spend ledger is for.
BILLABLE_RATE_LIMIT_HOUR = os.getenv("BILLABLE_RATE_LIMIT_HOUR", "10/hour")
BILLABLE_RATE_LIMIT_DAY = os.getenv("BILLABLE_RATE_LIMIT_DAY", "20/day")
