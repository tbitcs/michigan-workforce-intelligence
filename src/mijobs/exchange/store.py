from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class ExchangeError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


class Store:
    def __init__(self, path: Path, key: str, operator_token: str):
        if len(operator_token) < 40:
            raise ValueError("Exchange operator token must have at least 40 characters")
        self.path = path
        self.cipher = Fernet(key.encode())
        self.audit_key = hashlib.sha256(("audit:" + key).encode()).digest()
        self.operator_hash = hashlib.sha256(operator_token.encode()).hexdigest()
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(
                "CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, kind TEXT NOT NULL, tenant TEXT NOT NULL, credential TEXT, payload TEXT NOT NULL); CREATE UNIQUE INDEX IF NOT EXISTS credentials ON records(credential) WHERE credential IS NOT NULL; CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY, body TEXT NOT NULL, previous TEXT NOT NULL, digest TEXT NOT NULL);"
            )
            self.verify(db)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self.verify(db)
            yield db

    def fingerprint(self, row: dict[str, Any]) -> str:
        return hashlib.sha256(canonical(row).encode()).hexdigest()

    def verify(self, db: sqlite3.Connection) -> dict[str, Any]:
        previous = "0" * 64
        expected: dict[str, str] = {}
        count = 0
        for row in db.execute("SELECT * FROM audit ORDER BY seq"):
            count += 1
            digest = hmac.new(
                self.audit_key, (previous + row["body"]).encode(), hashlib.sha256
            ).hexdigest()
            if (
                row["seq"] != count
                or row["previous"] != previous
                or not hmac.compare_digest(row["digest"], digest)
            ):
                raise ExchangeError("Confidential audit integrity failure", 503)
            event = json.loads(row["body"])
            if event.get("record_digest"):
                expected[event["record_id"]] = event["record_digest"]
            previous = digest
        records = {r["id"]: self.fingerprint(dict(r)) for r in db.execute("SELECT * FROM records")}
        if records != expected:
            raise ExchangeError("Confidential record coverage failure", 503)
        return {"valid": True, "events": count, "head": previous, "records": len(records)}

    def audit(
        self,
        db: sqlite3.Connection,
        actor: str,
        operation: str,
        record: dict[str, Any] | None = None,
    ) -> None:
        last = db.execute("SELECT seq,digest FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        previous = last["digest"] if last else "0" * 64
        body = canonical(
            {
                "at": datetime.now(UTC).isoformat(),
                "actor": actor,
                "operation": operation,
                "record_id": record["id"] if record else None,
                "record_digest": self.fingerprint(record) if record else None,
            }
        )
        digest = hmac.new(self.audit_key, (previous + body).encode(), hashlib.sha256).hexdigest()
        db.execute(
            "INSERT INTO audit VALUES (?,?,?,?)",
            (last["seq"] + 1 if last else 1, body, previous, digest),
        )

    def put(
        self,
        db: sqlite3.Connection,
        *,
        kind: str,
        tenant: str,
        payload: dict[str, Any],
        actor: str,
        record_id: str | None = None,
        credential: str | None = None,
    ) -> str:
        rid = record_id or secrets.token_hex(16)
        envelope = {"id": rid, "kind": kind, "tenant": tenant, "data": payload}
        row = {
            "id": rid,
            "kind": kind,
            "tenant": tenant,
            "credential": credential,
            "payload": self.cipher.encrypt(canonical(envelope).encode()).decode(),
        }
        db.execute(
            "INSERT INTO records VALUES (:id,:kind,:tenant,:credential,:payload) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,credential=excluded.credential",
            row,
        )
        self.audit(db, actor, "write:" + kind, row)
        return rid

    def unpack(self, row: sqlite3.Row) -> dict[str, Any]:
        try:
            envelope = json.loads(self.cipher.decrypt(row["payload"].encode()))
        except (InvalidToken, ValueError):
            raise ExchangeError("Confidential encryption integrity failure", 503) from None
        if any(envelope[k] != row[k] for k in ("id", "kind", "tenant")):
            raise ExchangeError("Confidential envelope mismatch", 503)
        return {"id": row["id"], "tenant": row["tenant"], **envelope["data"]}

    def get(self, db: sqlite3.Connection, rid: str, kind: str) -> dict[str, Any]:
        row = db.execute("SELECT * FROM records WHERE id=? AND kind=?", (rid, kind)).fetchone()
        if row is None:
            raise ExchangeError("Record not found", 404)
        return self.unpack(row)

    def list(self, db: sqlite3.Connection, kind: str) -> list[dict[str, Any]]:
        return [
            self.unpack(r)
            for r in db.execute("SELECT * FROM records WHERE kind=? ORDER BY id", (kind,))
        ]

    def authenticate(self, db: sqlite3.Connection, token: str) -> str:
        digest = hashlib.sha256(token.encode()).hexdigest()
        if hmac.compare_digest(digest, self.operator_hash):
            return "operator"
        row = db.execute(
            "SELECT * FROM records WHERE credential=? AND kind=?", (digest, "employer")
        ).fetchone()
        if row:
            employer = self.unpack(row)
            if employer["active"] and employer["expires"] >= date.today().isoformat():
                return str(row["id"])
        raise ExchangeError("Invalid or expired credential", 401)

    def provision(self, db: sqlite3.Connection, actor: str, name: str, days: int) -> dict[str, Any]:
        if actor != "operator":
            raise ExchangeError("Operator access required", 403)
        token = secrets.token_urlsafe(32)
        rid = secrets.token_hex(16)
        self.put(
            db,
            kind="employer",
            tenant=rid,
            record_id=rid,
            actor=actor,
            credential=hashlib.sha256(token.encode()).hexdigest(),
            payload={
                "name": name,
                "active": True,
                "expires": (date.today() + timedelta(days=days)).isoformat(),
            },
        )
        return {
            "id": rid,
            "name": name,
            "credential": token,
            "notice": "Shown once. Share securely; never place in URLs or source control.",
        }
