"""The suite must run with NO credentials in the environment (ADR-0009).

This file exists because the guarantee failed silently for weeks and nobody could
see it: `.github/workflows/ci.yml` sets no environment variables, so CI had no
`OPENAI_API_KEY` — while every developer machine had one exported and passed. The
red build looked like a flaky test rather than what it was.

The mechanism was subtle. ``openai>=2`` raises ``OpenAIError: Missing
credentials`` from the client **constructor**, and the routes construct their
services eagerly. So a test that mocked the orchestrator, never intending to touch
OpenAI, still exploded on the way in.

These tests assert the property directly rather than the symptom, so any future
service that builds a client eagerly is caught here instead of in CI.
"""

import os
from unittest.mock import patch

import pytest

from app.services import (
    LLMEnrichmentService,
    LLMExtractionService,
    WhisperTranscriptionService,
)

OPENAI_SERVICES = [
    LLMExtractionService,
    LLMEnrichmentService,
    WhisperTranscriptionService,
]


@pytest.fixture
def no_credentials():
    """Run as CI does: nothing in the environment."""
    with patch.dict(os.environ, {}, clear=True):
        yield


class TestServicesConstructWithoutCredentials:
    @pytest.mark.parametrize("service_cls", OPENAI_SERVICES, ids=lambda c: c.__name__)
    def test_constructing_needs_no_api_key(self, service_cls, no_credentials):
        """Building a service must be free.

        Constructing is not calling. A service that may never make a request must
        not demand a credential to exist, or every consumer inherits that
        requirement — including tests that mock the call away entirely.
        """
        service_cls()  # must not raise

    @pytest.mark.parametrize("service_cls", OPENAI_SERVICES, ids=lambda c: c.__name__)
    def test_an_injected_client_is_used_verbatim(self, service_cls, no_credentials):
        """The injection seam still wins — laziness must not bypass it."""
        sentinel = object()
        assert service_cls(client=sentinel)._client is sentinel

    @pytest.mark.parametrize("service_cls", OPENAI_SERVICES, ids=lambda c: c.__name__)
    def test_the_lazy_client_is_built_once(self, service_cls):
        """Reused across calls rather than rebuilt per request.

        A dummy key is required *here* and nowhere else, which is exactly the
        point: this is the only test that deliberately builds the real client, so
        it is the only one that needs a credential to exist. Nothing is sent
        anywhere — the client is constructed and never called.
        """
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-not-a-real-key"}):
            service = service_cls()
            assert service._client is service._client


class TestRoutesImportWithoutCredentials:
    def test_the_app_imports_with_an_empty_environment(self, no_credentials):
        """The failure surfaced through the routes, so pin it at that level too.

        `app.main` pulls in every route module, which pulls in every service.
        Importing must not require a credential.
        """
        import importlib

        import app.main

        importlib.reload(app.main)
