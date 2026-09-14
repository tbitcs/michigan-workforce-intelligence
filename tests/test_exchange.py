import json
from datetime import date, timedelta

import pytest
from cryptography.fernet import Fernet
from starlette.testclient import TestClient

from mijobs.exchange.app import create_app
from mijobs.exchange.store import ExchangeError, Store

OPERATOR = "test-operator-" + "x" * 40


@pytest.fixture
def exchange(tmp_path):
    store = Store(tmp_path / "private.db", Fernet.generate_key().decode(), OPERATOR)
    client = TestClient(create_app(store, hosts=["testserver"], origins=["http://testserver"]))

    def request(method, path, token=OPERATOR, body=None):
        return client.request(method, path, headers={"Authorization": "Bearer " + token}, json=body)

    return store, client, request


def employer(request, name="Employer"):
    response = request(
        "POST",
        "/api/employers",
        body={"name": name, "credential_days": 30, "identity_verified": True},
    )
    assert response.status_code == 200, response.text
    return response.json()


def signal(request, token, kind="surplus", **changes):
    today = date.today()
    data = {
        "kind": kind,
        "county": "26099",
        "occupation": "51-4041",
        "skills": ["CNC", "Drawings"],
        "headcount": 3,
        "earliest": today.isoformat(),
        "latest": (today + timedelta(days=30)).isoformat(),
        "expires": (today + timedelta(days=20)).isoformat(),
        "minimum_hourly_wage": 25,
        "hours_per_week": 40,
        "share_with_network": True,
    }
    data.update(changes)
    return request("POST", "/api/signals", token, data)


def pair(request):
    a, b = employer(request, "Employer A"), employer(request, "Employer B")
    supply = signal(request, a["credential"]).json()
    job = signal(request, b["credential"], "hiring", skills=["CNC", "Inspection"]).json()
    return a, b, supply, job


def propose(request, a, supply, job, count=2):
    return request(
        "POST",
        "/api/transitions",
        a["credential"],
        {
            "surplus_id": supply["id"],
            "hiring_id": job["id"],
            "headcount": count,
            "worker_consent_attested": True,
        },
    )


def offer(**extra):
    return {
        "action": "accept",
        "start_date": date.today().isoformat(),
        "hourly_wage": 26,
        "hours_per_week": 40,
        "benefits_confirmed": True,
        **extra,
    }


def test_full_private_flow_and_encryption(exchange):
    store, client, request = exchange
    a, b, s, j = pair(request)
    assert request("GET", "/api/me", a["credential"]).json()["actor"] == a["id"]
    matches = request("GET", "/api/matches", a["credential"]).json()["matches"]
    assert len(matches) == 1 and matches[0]["remaining_requirements"] == ["inspection"]
    assert len(request("GET", "/api/signals", a["credential"]).json()["signals"]) == 1
    assert len(request("GET", "/api/signals").json()["signals"]) == 2
    t = propose(request, a, s, j).json()
    assert (
        request("POST", "/api/transitions/" + t["id"], b["credential"], offer()).json()["status"]
        == "accepted"
    )
    started = request(
        "POST",
        "/api/transitions/" + t["id"],
        b["credential"],
        {"action": "started", "actual_start_date": date.today().isoformat()},
    )
    assert started.json()["status"] == "started"
    assert len(request("GET", "/api/transitions", b["credential"]).json()["transitions"]) == 1
    assert len(request("GET", "/api/transitions").json()["transitions"]) == 1
    audit = request("GET", "/api/audit").json()
    assert audit["valid"] and audit["records"] == 5
    raw = store.path.read_bytes()
    assert (
        b"Employer A" not in raw
        and b"Inspection" not in raw
        and a["credential"].encode() not in raw
    )
    assert request("DELETE", "/api/employers/" + a["id"]).status_code == 200
    assert request("GET", "/api/me", a["credential"]).status_code == 401
    assert len(request("GET", "/api/employers").json()["employers"]) == 2
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/assets/secret").status_code == 404
    assert "frame-ancestors 'none'" in client.get("/").headers["content-security-policy"]


def test_cross_tenant_and_operator_boundaries(exchange):
    _, client, request = exchange
    a, b, s, j = pair(request)
    stranger = employer(request, "Stranger")
    assert request("DELETE", "/api/signals/" + s["id"], b["credential"]).status_code == 404
    assert request("GET", "/api/employers", a["credential"]).status_code == 403
    assert (
        request(
            "POST",
            "/api/employers",
            a["credential"],
            {"name": "bad", "credential_days": 1, "identity_verified": True},
        ).status_code
        == 403
    )
    assert request("DELETE", "/api/employers/" + b["id"], a["credential"]).status_code == 403
    assert request("GET", "/api/audit", a["credential"]).status_code == 403
    assert signal(request, OPERATOR).status_code == 403
    assert propose(request, b, s, j).status_code == 404
    t = propose(request, a, s, j).json()
    assert request("GET", "/api/transitions", stranger["credential"]).json()["transitions"] == []
    assert (
        request(
            "POST", "/api/transitions/" + t["id"], stranger["credential"], {"action": "withdraw"}
        ).status_code
        == 404
    )
    assert (
        request("POST", "/api/transitions/" + t["id"], a["credential"], offer()).status_code == 403
    )
    assert request("GET", "/api/matches", stranger["credential"]).json()["matches"] == []
    assert request("DELETE", "/api/signals/" + "f" * 32, a["credential"]).status_code == 404
    assert request("GET", "/api/unknown").status_code == 404
    assert client.get("/api/me").status_code == 401
    assert request("GET", "/api/me", "bad").status_code == 401
    assert client.get("/api/me", headers={"Origin": "https://attacker.example"}).status_code == 403
    assert client.get("/", headers={"Host": "attacker.example"}).status_code == 400


@pytest.mark.parametrize(
    "changes",
    [
        {"share_with_network": False},
        {"county": "26125"},
        {"occupation": "17-2141"},
        {"minimum_hourly_wage": 20},
        {"hours_per_week": 20},
        {
            "earliest": (date.today() + timedelta(days=40)).isoformat(),
            "latest": (date.today() + timedelta(days=50)).isoformat(),
        },
    ],
)
def test_matching_is_opt_in_and_compatible(exchange, changes):
    _, _, request = exchange
    a, b = employer(request, "A company"), employer(request, "B company")
    s = signal(request, a["credential"]).json()
    j = signal(request, b["credential"], "hiring", **changes).json()
    assert request("GET", "/api/matches", a["credential"]).json()["matches"] == []
    assert propose(request, a, s, j).status_code == 409


@pytest.mark.parametrize(
    "changes",
    [
        {"headcount": 0},
        {"occupation": "nonsense"},
        {"county": "US"},
        {"earliest": "2000-01-01"},
        {"expires": (date.today() + timedelta(days=100)).isoformat()},
        {"skills": ["x" * 61]},
        {"private_worker_name": "do not store"},
        {"minimum_hourly_wage": 0},
    ],
)
def test_signal_validation(exchange, changes):
    _, _, request = exchange
    a = employer(request)
    assert signal(request, a["credential"], **changes).status_code == 422


def test_capacity_consent_and_state_machine(exchange):
    store, _, request = exchange
    a, b, s, j = pair(request)
    assert propose(request, a, s, j, 4).status_code == 409
    invalid = {
        "surplus_id": s["id"],
        "hiring_id": j["id"],
        "headcount": 1,
        "worker_consent_attested": False,
    }
    assert request("POST", "/api/transitions", a["credential"], invalid).status_code == 422
    t = propose(request, a, s, j).json()
    path = "/api/transitions/" + t["id"]
    for body in [
        offer(start_date=None),
        offer(hourly_wage=10),
        offer(benefits_confirmed=False),
        offer(hours_per_week=10),
        {"action": "started", "actual_start_date": date.today().isoformat()},
    ]:
        assert request("POST", path, b["credential"], body).status_code in {400, 409}
    assert request("POST", path, b["credential"], offer()).status_code == 200
    t2 = propose(request, a, s, j).json()
    assert (
        request("POST", "/api/transitions/" + t2["id"], b["credential"], offer()).status_code == 409
    )
    assert request("POST", path, b["credential"], offer()).status_code == 409
    assert request("POST", path, b["credential"], {"action": "decline"}).status_code == 409
    assert (
        request("POST", path, a["credential"], {"action": "withdraw"}).json()["status"]
        == "withdrawn"
    )
    assert request("POST", path, a["credential"], {"action": "withdraw"}).status_code == 409
    assert (
        request(
            "POST", "/api/transitions/" + t2["id"], b["credential"], {"action": "decline"}
        ).json()["status"]
        == "declined"
    )
    t3 = propose(request, a, s, j).json()
    assert request("DELETE", "/api/signals/" + s["id"], a["credential"]).status_code == 200
    assert (
        request("POST", "/api/transitions/" + t3["id"], b["credential"], offer()).status_code == 409
    )
    with store.transaction() as db:
        assert store.verify(db)["valid"]


def test_tamper_and_rollback_fail_closed(exchange):
    store, _, request = exchange
    a = employer(request, "Encrypted employer")
    with store.connect() as db:
        before = store.verify(db)
    def fail_transaction():
        with store.transaction() as db:
            store.provision(db, "operator", "Rollback company", 5)
            raise RuntimeError("rollback")

    with pytest.raises(RuntimeError):
        fail_transaction()
    with store.connect() as db:
        assert store.verify(db) == before
        db.execute("UPDATE records SET tenant=? WHERE id=?", ("attacker", a["id"]))
    assert request("GET", "/api/me").status_code == 503


def test_chain_and_cipher_integrity(exchange):
    store, _, request = exchange
    a = employer(request)
    with store.connect() as db:
        row = db.execute("SELECT * FROM records WHERE id=?", (a["id"],)).fetchone()
        record = dict(row)
        record["payload"] = "invalid"
        with pytest.raises(ExchangeError, match="encryption"):
            store.unpack(record)
        envelope = {"id": "wrong", "kind": "employer", "tenant": a["id"], "data": {}}
        record["payload"] = store.cipher.encrypt(json.dumps(envelope).encode()).decode()
        with pytest.raises(ExchangeError, match="mismatch"):
            store.unpack(record)
        db.execute("UPDATE audit SET digest=? WHERE seq=1", ("bad",))
    assert request("GET", "/api/me").status_code == 503


def test_bad_inputs_and_rate_limit(exchange):
    _, client, request = exchange
    headers = {"Authorization": "Bearer " + OPERATOR}
    assert client.post("/api/signals", headers=headers, content="invalid").status_code == 400
    assert client.post("/api/signals", headers=headers, json=[]).status_code == 400
    assert client.post("/api/signals", headers=headers, content="x" * 17000).status_code == 413
    assert (
        client.post(
            "/api/signals", headers=headers, json={"unexpected": "secret value"}
        ).status_code
        == 422
    )
    for _ in range(181):
        response = request("GET", "/api/me", "bad")
    assert response.status_code == 429


def test_bad_key_and_token(tmp_path):
    with pytest.raises(ValueError):
        Store(tmp_path / "x", Fernet.generate_key().decode(), "short")
    with pytest.raises(ValueError):
        Store(tmp_path / "x", "invalid", OPERATOR)


def test_private_mcp_protocol_and_scope(exchange):
    _, client, request = exchange
    a, _b, _s, _j = pair(request)

    def rpc(body, token=a["credential"]):
        return client.post("/mcp", headers={"Authorization": "Bearer " + token}, json=body)

    assert (
        rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize"}).json()["result"]["serverInfo"][
            "name"
        ]
        == "michigan-confidential-exchange"
    )
    assert rpc({"jsonrpc": "2.0", "method": "notifications/initialized"}).status_code == 202
    assert rpc({"jsonrpc": "2.0", "id": 2, "method": "ping"}).json()["result"] == {}
    listing = rpc({"jsonrpc": "2.0", "id": 3, "method": "tools/list"}).json()["result"]["tools"]
    assert len(listing) == 3 and all(t["annotations"]["readOnlyHint"] for t in listing)
    for tool in listing:
        result = rpc(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": tool["name"], "arguments": {}},
            }
        )
        assert result.status_code == 200 and not result.json()["result"]["isError"]
    rows = rpc(
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "exchange_signals"}}
    ).json()["result"]["structuredContent"]["signals"]
    assert len(rows) == 1 and rows[0]["tenant"] == a["id"]
    assert rpc({"jsonrpc": "2.0", "id": 6, "method": "unknown"}).json()["error"]["code"] == -32601
    assert (
        rpc({"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": []}}).json()[
            "error"
        ]["code"]
        == -32602
    )
    assert rpc({"jsonrpc": "2.0", "id": 8, "method": "ping", "params": []}).status_code == 400
    assert rpc({"method": "ping"}).status_code == 400
    assert rpc({"jsonrpc": "2.0", "id": 9, "method": "tools/list"}, "bad").status_code == 401


def test_expired_employer_hidden_from_network(exchange):
    store, _, request = exchange
    a, b, _s, _j = pair(request)
    with store.transaction() as db:
        record = store.get(db, b["id"], "employer")
        record["expires"] = "2000-01-01"
        store.put(
            db,
            kind="employer",
            tenant=b["id"],
            record_id=b["id"],
            actor="operator",
            payload=record,
            credential=__import__("hashlib").sha256(b["credential"].encode()).hexdigest(),
        )
    assert request("GET", "/api/me", b["credential"]).status_code == 401
    assert request("GET", "/api/matches", a["credential"]).json()["matches"] == []


def test_official_mcp_client(exchange):
    import asyncio

    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    store, _, _ = exchange

    async def run():
        app = create_app(store)
        async with (
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                headers={"Authorization": "Bearer " + OPERATOR},
            ) as http,
            streamable_http_client("http://localhost:8085/mcp", http_client=http) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            listing = await session.list_tools()
            assert {t.name for t in listing.tools} == {
                "exchange_signals",
                "exchange_matches",
                "exchange_transitions",
            }
            for tool in listing.tools:
                result = await session.call_tool(tool.name, {})
                assert not result.is_error

    asyncio.run(run())
