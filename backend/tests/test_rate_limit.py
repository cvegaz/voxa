"""Tests for the per-IP rate limit on billable endpoints (ADR-0019 §3, §9).

Two things are under test and only one of them is the limit itself. The other —
**which address we count on** — is where this kind of protection usually fails
silently: behind a reverse proxy the naive implementation buckets the entire
internet together, and the naive *fix* reads a header the caller controls and hands
every visitor an unlimited quota. Both failure modes are pinned down here.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.main import app
from app.rate_limit import client_ip


def _request(peer: str, forwarded: str | None = None) -> Request:
    headers = []
    if forwarded is not None:
        headers.append((b"x-forwarded-for", forwarded.encode()))
    return Request({"type": "http", "client": (peer, 12345), "headers": headers})


class TestClientIpWithoutProxy:
    """Default configuration (TRUSTED_PROXY_HOPS=0): the header is not trusted."""

    def test_uses_the_peer_address(self, monkeypatch):
        monkeypatch.setattr("app.rate_limit.TRUSTED_PROXY_HOPS", 0)
        assert client_ip(_request("203.0.113.7")) == "203.0.113.7"

    def test_ignores_a_forwarded_header_entirely(self, monkeypatch):
        """Fail secure: with no proxy declared, a header is just a caller's claim.

        If we honoured it here, anyone could reset their own quota by sending a
        different value on every request — strictly worse than having no limit,
        because it would look protected.
        """
        monkeypatch.setattr("app.rate_limit.TRUSTED_PROXY_HOPS", 0)
        ip = client_ip(_request("203.0.113.7", forwarded="1.2.3.4"))
        assert ip == "203.0.113.7"


class TestClientIpBehindProxies:
    """The counting rule: from the right, by the number of hops WE operate."""

    def test_single_hop_reads_what_the_proxy_observed(self, monkeypatch):
        monkeypatch.setattr("app.rate_limit.TRUSTED_PROXY_HOPS", 1)
        # Caddy appended the address it actually saw.
        ip = client_ip(_request("172.18.0.5", forwarded="9.9.9.9"))
        assert ip == "9.9.9.9"

    def test_two_hops_skips_the_inner_proxy(self, monkeypatch):
        """Stage-1 topology: Caddy -> frontend nginx -> backend.

        nginx appends Caddy's container address, so the rightmost entry is
        infrastructure, not a visitor. Reading it would bucket everyone together —
        the very bug this is meant to fix.
        """
        monkeypatch.setattr("app.rate_limit.TRUSTED_PROXY_HOPS", 2)
        ip = client_ip(_request("172.18.0.9", forwarded="9.9.9.9, 172.18.0.5"))
        assert ip == "9.9.9.9"

    def test_a_forged_prefix_cannot_shift_the_result(self, monkeypatch):
        """The attacker controls the LEFT of the header; we only ever read the right.

        Reading `parts[0]` is the classic mistake: it is precisely the entry the
        caller wrote. No amount of padding moves our index, because the position is
        fixed by our own topology and not by the header's length.
        """
        monkeypatch.setattr("app.rate_limit.TRUSTED_PROXY_HOPS", 2)
        forged = "1.1.1.1, 2.2.2.2, 3.3.3.3, 9.9.9.9, 172.18.0.5"
        assert client_ip(_request("172.18.0.9", forwarded=forged)) == "9.9.9.9"

    def test_falls_back_to_the_peer_when_the_chain_is_shorter_than_declared(
        self, monkeypatch
    ):
        """A request that skipped the proxy, or a misconfigured hop count.

        Everyone may then share one bucket, which is a degraded limit — but nothing
        is forgeable, which is the property worth protecting.
        """
        monkeypatch.setattr("app.rate_limit.TRUSTED_PROXY_HOPS", 3)
        ip = client_ip(_request("172.18.0.9", forwarded="9.9.9.9"))
        assert ip == "172.18.0.9"

    def test_tolerates_whitespace_and_empty_entries(self, monkeypatch):
        monkeypatch.setattr("app.rate_limit.TRUSTED_PROXY_HOPS", 1)
        ip = client_ip(_request("172.18.0.5", forwarded="  9.9.9.9 ,  "))
        assert ip == "9.9.9.9"

    def test_missing_header_falls_back_to_the_peer(self, monkeypatch):
        monkeypatch.setattr("app.rate_limit.TRUSTED_PROXY_HOPS", 2)
        assert client_ip(_request("172.18.0.9")) == "172.18.0.9"


@pytest.fixture
def client():
    app.state.pool = MagicMock()
    return TestClient(app, raise_server_exceptions=False)


def _post_empty_audio(client: TestClient):
    """Cheapest request that still reaches the endpoint (and thus the limiter).

    It is rejected as EMPTY_AUDIO_FILE inside the handler, which is exactly what we
    want: the limit is exercised without touching the audio pipeline.
    """
    return client.post(
        "/api/transcriptions/transcribe",
        files={"file": ("audio.webm", b"", "audio/webm")},
        data={"duration": "5.0"},
    )


class TestBillableEndpointLimit:
    def test_allows_requests_under_the_hourly_cap(self, client):
        for _ in range(10):
            assert _post_empty_audio(client).status_code == 422

    def test_blocks_past_the_hourly_cap(self, client):
        for _ in range(10):
            _post_empty_audio(client)

        response = _post_empty_audio(client)

        assert response.status_code == 429

    def test_the_429_keeps_the_flattened_error_contract(self, client):
        """ADR-0005: the client never sees a nested detail or snake_case."""
        for _ in range(11):
            response = _post_empty_audio(client)

        body = response.json()
        assert response.status_code == 429
        assert body["errorCode"] == "RATE_LIMITED"
        assert isinstance(body["detail"], str)

    def test_separate_addresses_get_separate_buckets(self, client, monkeypatch):
        """One heavy visitor must not exhaust the quota of everybody else.

        This is the whole point of keying on the real client address rather than on
        the proxy's: under CGNAT a shared address already over-collects, and
        collapsing everyone into ONE bucket would make the limit unusable.
        """
        monkeypatch.setattr("app.rate_limit.TRUSTED_PROXY_HOPS", 1)

        for _ in range(11):
            noisy = client.post(
                "/api/transcriptions/transcribe",
                files={"file": ("audio.webm", b"", "audio/webm")},
                headers={"X-Forwarded-For": "9.9.9.9"},
            )
        assert noisy.status_code == 429

        other = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.webm", b"", "audio/webm")},
            headers={"X-Forwarded-For": "8.8.8.8"},
        )
        assert other.status_code == 422


class TestBillableEndpointCoverage:
    """Every endpoint that spends money must carry the limit — including the one
    whose name does not suggest it.

    Asserted **behaviourally** (send requests until the cap trips) rather than by
    inspecting the route objects. An earlier structural version broke immediately:
    this FastAPI version keeps `_IncludedRouter` wrappers in `app.routes` instead of
    flattened routes, so the check was testing a framework internal rather than the
    property we care about.
    """

    # Bodies valid enough for FastAPI's validation to pass, so the request actually
    # reaches the handler — and therefore the limiter. What the handler then answers
    # (404, 422, 502…) is irrelevant here; only the 429 is.
    ENDPOINTS = [
        (
            "/api/transcriptions/transcribe",
            {"files": {"file": ("a.webm", b"", "audio/webm")}},
        ),
        (
            "/api/extraction/process",
            {"json": {"sessionId": str(uuid4()), "transcribedText": "hola"}},
        ),
        (
            "/api/templates/confirm",
            {
                "json": {
                    "sessionId": str(uuid4()),
                    "context": "Un contexto de prueba suficientemente largo.",
                    "language": "es",
                }
            },
        ),
    ]

    @pytest.mark.parametrize("path,payload", ENDPOINTS, ids=lambda v: str(v)[:40])
    def test_endpoint_is_rate_limited(self, client, path, payload):
        """`/templates/confirm` triggers the LLM enrichment call, so it is billable
        even though it reads like a bookkeeping step."""
        statuses = [client.post(path, **payload).status_code for _ in range(11)]

        assert 429 in statuses, (
            f"{path} never returned 429 in 11 requests — it is not rate limited. "
            f"Statuses: {statuses}"
        )
