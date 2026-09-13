from pathlib import Path

import httpx
import pytest

from mijobs.sources.base import SourceFetchError
from mijobs.sources.http_policy import QuotaStore, governed_client, policy


def test_provider_policies():
    assert policy(httpx.Request("POST", "https://api.bls.gov", json={}))[2] == [(86400, 20)]
    assert policy(httpx.Request("POST", "https://api.bls.gov", json={"registrationkey": "test"}))[
        2
    ] == [(86400, 450)]
    with pytest.raises(SourceFetchError, match="require"):
        policy(httpx.Request("GET", "https://api.census.gov/data"))
    assert policy(httpx.Request("GET", "https://api.census.gov/data?key=test"))[0] == "census"
    assert policy(httpx.Request("GET", "https://api.data.gov?api_key=DEMO_KEY"))[2] == [
        (3600, 25),
        (86400, 45),
    ]
    assert policy(httpx.Request("GET", "https://api.data.gov?api_key=test"))[2] == [(3600, 900)]
    with pytest.raises(SourceFetchError, match="not enabled"):
        policy(httpx.Request("GET", "https://services.onetcenter.org"))
    assert policy(httpx.Request("GET", "https://www.bea.gov"))[1] == 2


def test_persistent_quota_window_and_spacing(tmp_path: Path):
    path = tmp_path / "quota.db"
    first = QuotaStore(path)
    assert first.reserve("x", 2, [(60, 2)], now=100) == 0
    second = QuotaStore(path)
    assert second.reserve("x", 2, [(60, 2)], now=100) == 2
    with pytest.raises(SourceFetchError, match="quota"):
        second.reserve("x", 2, [(60, 2)], now=100)
    assert second.reserve("x", 2, [(60, 2)], now=163) == 0
    with pytest.raises(SourceFetchError, match="queue"):
        second.reserve("x", 100, [(60, 20)], now=163)
    second.block("x", 100)
    with pytest.raises(SourceFetchError, match="cooldown"):
        second.reserve("x", 2, [(60, 20)])


@pytest.mark.parametrize("retry", ["120", "Wed, 01 Jan 2031 00:00:00 GMT", "bad"])
def test_response_cooldown_without_retry(tmp_path, monkeypatch, retry):
    monkeypatch.setenv("MIJOBS_HTTP_STATE", str(tmp_path / "state.db"))
    with governed_client() as client:
        request = httpx.Request("GET", "https://www.bls.gov/example")
        client.event_hooks["request"][0](request)
        response = httpx.Response(429, request=request, headers={"Retry-After": retry})
        with pytest.raises(SourceFetchError, match="no automatic retry"):
            client.event_hooks["response"][0](response)
        with pytest.raises(SourceFetchError, match="cooldown"):
            client.event_hooks["request"][0](request)
