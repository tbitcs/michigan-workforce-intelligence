from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx

from mijobs.sources.base import FetchedArtifact, SourceConnector, SourceFetchError


class OfficialArtifactConnector(SourceConnector):
    """Fetch reviewed public files from official government domains."""

    source_id = "official_artifact"
    DEFAULT_ALLOWED_HOST_SUFFIXES = (
        "michigan.gov",
        "bls.gov",
        "census.gov",
        "ed.gov",
        "onetcenter.org",
        "apprenticeship.gov",
    )

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        allowed_host_suffixes: tuple[str, ...] | None = None,
    ):
        self.client = client or httpx.Client(timeout=60.0, follow_redirects=True)
        self.allowed_host_suffixes = allowed_host_suffixes or self.DEFAULT_ALLOWED_HOST_SUFFIXES

    def healthcheck(self) -> bool:
        return True

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("official artifact URL must use https")
        host = parsed.hostname.lower()
        if not any(host == suffix or host.endswith(f".{suffix}") for suffix in self.allowed_host_suffixes):
            raise ValueError(f"host not in official allow-list: {host}")

    def fetch(
        self,
        *,
        source_id: str,
        url: str,
        dataset_version: str | None = None,
        parser_version: str | None = None,
    ) -> FetchedArtifact:
        self._validate_url(url)
        response = self.client.get(url)
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SourceFetchError(f"official artifact fetch failed: {exc}") from exc
        final_url = str(response.url)
        self._validate_url(final_url)
        media_type = response.headers.get("content-type", "application/octet-stream").split(";", 1)[0]
        return FetchedArtifact(
            source_id=source_id,
            locator=final_url,
            retrieved_at=datetime.now(UTC),
            content=response.content,
            media_type=media_type,
            dataset_version=dataset_version,
            parser_version=parser_version,
            metadata={"http_etag": response.headers.get("etag"), "last_modified": response.headers.get("last-modified")},
        )
