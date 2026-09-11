from __future__ import annotations

import httpx
import pytest

from mijobs.sources.official_artifact import OfficialArtifactConnector


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)


def test_official_artifact_rejects_untrusted_or_plain_http() -> None:
    connector = OfficialArtifactConnector(client=_client(lambda req: httpx.Response(200, request=req)))
    with pytest.raises(ValueError):
        connector.fetch(source_id="x", url="http://www.michigan.gov/file.csv")
    with pytest.raises(ValueError):
        connector.fetch(source_id="x", url="https://evil.example/file.csv")
    with pytest.raises(ValueError):
        connector.fetch(source_id="x", url="https://michigan.gov.evil.example/file.csv")


def test_official_artifact_fetch_captures_headers_and_bytes() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"a,b\n1,2\n",
            headers={"content-type": "text/csv; charset=utf-8", "etag": '"v1"'},
            request=request,
        )

    artifact = OfficialArtifactConnector(client=_client(handler)).fetch(
        source_id="mi_mcda_laus",
        url="https://www.michigan.gov/sample.csv",
        dataset_version="2026-08",
        parser_version="laus/1",
    )
    assert artifact.content == b"a,b\n1,2\n"
    assert artifact.media_type == "text/csv"
    assert artifact.dataset_version == "2026-08"
    assert artifact.metadata["http_etag"] == '"v1"'


def test_official_artifact_wraps_http_failure() -> None:
    from mijobs.sources.base import SourceFetchError

    connector = OfficialArtifactConnector(
        client=_client(lambda req: httpx.Response(404, request=req))
    )
    with pytest.raises(SourceFetchError):
        connector.fetch(source_id="mi_mcda_laus", url="https://www.michigan.gov/missing.csv")
