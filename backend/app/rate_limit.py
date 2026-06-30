"""Shared rate limiter (slowapi) used to protect abuse-prone public endpoints.

Defined in its own module so both ``app.main`` (which registers the limiter and
its error handler on the app) and the route modules (which apply ``@limiter.limit``
decorators) can import the same instance without a circular import.
"""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

# Per-IP limiter with in-memory storage (fine for a single-process deployment;
# swap the storage_uri for Redis if the backend is ever scaled horizontally).
limiter = Limiter(key_func=get_remote_address)

# Limit for the public contact form. Configurable so it can be tightened in
# production without a code change. A human never submits this many per minute;
# the cap exists to blunt automated floods.
CONTACT_RATE_LIMIT = os.getenv("CONTACT_RATE_LIMIT", "30/minute")
