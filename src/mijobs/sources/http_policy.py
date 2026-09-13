"""Conservative cross-process outbound quotas; never persist credentials or request URLs."""

from __future__ import annotations

import os
import sqlite3
import time
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx

from mijobs.sources.base import SourceFetchError


def policy(request: httpx.Request) -> tuple[str, float, list[tuple[int, int]]]:
    host = request.url.host
    if host == "api.bls.gov":
        registered = b'"registrationkey"' in request.content
        return "bls", 1.1, [(86400, 450 if registered else 20)]
    if host == "api.census.gov":
        if not request.url.params.get("key"):
            raise SourceFetchError("Census API requests require CENSUS_API_KEY")
        return "census", 1.1, [(86400, 450)]
    if host == "api.data.gov":
        demo = request.url.params.get("api_key") in {None, "DEMO_KEY"}
        return "scorecard", 1.1, [(3600, 25), (86400, 45)] if demo else [(3600, 900)]
    # Implemented O*NET access is bulk downloads, not authenticated Web Services.
    if host == "services.onetcenter.org":
        raise SourceFetchError(
            "O*NET Web Services integration is not enabled; use reviewed bulk data"
        )
    return host, 2.0, [(86400, 200)]


class QuotaStore:
    def __init__(self, path: Path):
        self.path = path

    def reserve(
        self,
        bucket: str,
        interval: float,
        limits: list[tuple[int, int]],
        *,
        now: float | None = None,
    ) -> float:
        moment = time.time() if now is None else now
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path, timeout=30) as db:
            db.execute("CREATE TABLE IF NOT EXISTS requests (bucket TEXT, at REAL)")
            db.execute("CREATE TABLE IF NOT EXISTS cooldown (bucket TEXT PRIMARY KEY, until REAL)")
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM requests WHERE at < ?", (moment - 86400,))
            blocked = db.execute("SELECT until FROM cooldown WHERE bucket=?", (bucket,)).fetchone()
            if blocked and blocked[0] > moment:
                raise SourceFetchError(
                    "Provider cooldown active; retry after the documented waiting period"
                )
            for window, maximum in limits:
                count = db.execute(
                    "SELECT COUNT(*) FROM requests WHERE bucket=? AND at>?",
                    (bucket, moment - window),
                ).fetchone()[0]
                if count >= maximum:
                    raise SourceFetchError(
                        "Conservative provider request quota exhausted; retry later"
                    )
            last = db.execute("SELECT MAX(at) FROM requests WHERE bucket=?", (bucket,)).fetchone()[
                0
            ]
            scheduled = max(moment, (last or 0) + interval)
            if scheduled - moment > 60:
                raise SourceFetchError("Provider request queue is full; retry later")
            db.execute("INSERT INTO requests VALUES (?, ?)", (bucket, scheduled))
        return scheduled - moment

    def block(self, bucket: str, seconds: float) -> None:
        with sqlite3.connect(self.path, timeout=30) as db:
            db.execute(
                "INSERT INTO cooldown VALUES (?, ?) ON CONFLICT(bucket) DO UPDATE SET until=MAX(until, excluded.until)",
                (bucket, time.time() + seconds),
            )


def governed_client(*, timeout: float = 60, follow_redirects: bool = False) -> httpx.Client:
    state = Path(
        os.getenv(
            "MIJOBS_HTTP_STATE",
            "/data/http-policy.sqlite3" if Path("/data").is_dir() else ".cache/http-policy.sqlite3",
        )
    )
    store = QuotaStore(state)

    def before(request: httpx.Request) -> None:
        bucket, interval, limits = policy(request)
        delay = store.reserve(bucket, interval, limits)
        if delay:
            time.sleep(delay)

    def after(response: httpx.Response) -> None:
        if response.status_code in {429, 503}:
            value = response.headers.get("Retry-After", "60")
            try:
                seconds = float(value)
            except ValueError:
                try:
                    seconds = parsedate_to_datetime(value).timestamp() - time.time()
                except (ValueError, TypeError):
                    seconds = 60
            bucket, _, _ = policy(response.request)
            store.block(bucket, max(60, seconds))
            raise SourceFetchError(
                f"Provider HTTP {response.status_code}; cooldown recorded, no automatic retry"
            )

    return httpx.Client(
        timeout=timeout,
        follow_redirects=follow_redirects,
        headers={"User-Agent": "MichiganWorkforceIntelligence/0.1 (public aggregate research)"},
        event_hooks={"request": [before], "response": [after]},
    )
