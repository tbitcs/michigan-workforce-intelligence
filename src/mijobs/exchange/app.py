from __future__ import annotations

import json
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import uvicorn
from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Route

from mijobs.exchange.service import Decision, Employer, Proposal, Service, Signal
from mijobs.exchange.store import ExchangeError, Store

ASSETS = Path(__file__).with_name("static")


class Guard(BaseHTTPMiddleware):
    def __init__(self, app: Any, origins: list[str]):
        super().__init__(app)
        self.origins = origins
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.headers.get("origin") and request.headers["origin"] not in self.origins:
            return JSONResponse({"error": "Origin not allowed"}, status_code=403)
        if request.url.path.startswith(("/api", "/mcp")):
            client = request.client.host if request.client else "local"
            now = time.monotonic()
            queue = self.requests[client]
            while queue and queue[0] < now - 60:
                queue.popleft()
            if len(queue) >= 180:
                return JSONResponse(
                    {"error": "Request rate exceeded"},
                    status_code=429,
                    headers={"Retry-After": "60"},
                )
            queue.append(now)
        response = await call_next(request)
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "X-Frame-Options": "DENY",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            }
        )
        return response


def dispatch(
    store: Store, token: str, method: str, path: str, body: dict[str, Any]
) -> dict[str, Any]:
    with store.transaction() as db:
        actor = store.authenticate(db, token)
        service = Service(store, db, actor)
        result: dict[str, Any]
        if path == "/api/me" and method == "GET":
            result = {"actor": actor, "role": "operator" if actor == "operator" else "employer"}
        elif path == "/api/employers" and method == "POST":
            value = Employer.model_validate(body)
            result = store.provision(db, actor, value.name, value.credential_days)
        elif path == "/api/employers" and method == "GET":
            result = {"employers": service.employers()}
        elif path.startswith("/api/employers/") and method == "DELETE":
            result = service.revoke(path.rsplit("/", 1)[1])
        elif path == "/api/signals" and method == "POST":
            result = service.create_signal(Signal.model_validate(body))
        elif path == "/api/signals" and method == "GET":
            result = {"signals": service.signals()}
        elif path.startswith("/api/signals/") and method == "DELETE":
            result = service.close_signal(path.rsplit("/", 1)[1])
        elif path == "/api/matches" and method == "GET":
            result = {
                "matches": service.matches(),
                "limitations": "Candidate routes, not verified placements; matching is limited to same county and SOC.",
            }
        elif path == "/api/transitions" and method == "POST":
            result = service.propose(Proposal.model_validate(body))
        elif path == "/api/transitions" and method == "GET":
            result = {
                "transitions": service.transitions(),
                "limitations": "Consent and outcomes are employer attestations, not independently verified jobs saved.",
            }
        elif path.startswith("/api/transitions/") and method == "POST":
            result = service.decide(path.rsplit("/", 1)[1], Decision.model_validate(body))
        elif path == "/api/audit" and method == "GET":
            if actor != "operator":
                raise ExchangeError("Operator access required", 403)
            result = store.verify(db)
        else:
            raise ExchangeError("Route not found", 404)
        store.audit(db, actor, "access:" + method + ":" + path.split("/")[2])
        return result


PRIVATE_TOOLS = {
    "exchange_signals": "/api/signals",
    "exchange_matches": "/api/matches",
    "exchange_transitions": "/api/transitions",
}


def mcp_request(store: Store, token: str, body: dict[str, Any]) -> dict[str, Any] | None:
    dispatch(store, token, "GET", "/api/me", {})
    if body.get("jsonrpc") != "2.0":
        raise ExchangeError("JSON-RPC 2.0 required")
    method = body.get("method")
    rid = body.get("id")
    if method == "notifications/initialized" and rid is None:
        return None
    params = body.get("params", {})
    if not isinstance(params, dict):
        raise ExchangeError("Object parameters required")
    if method == "initialize":
        result: dict[str, Any] = {
            "protocolVersion": "2025-11-25",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "michigan-confidential-exchange", "version": "0.1.0"},
            "instructions": "Private employer self-reports and attestations, scoped to the authenticated caller. No causal jobs-saved claims; never copy confidential results into public report releases.",
        }
    elif method == "tools/list":
        result = {
            "tools": [
                {
                    "name": name,
                    "description": "Read caller-authorized confidential "
                    + name.removeprefix("exchange_")
                    + ". Employer assertions, not verified government evidence.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                    "annotations": {
                        "readOnlyHint": True,
                        "destructiveHint": False,
                        "openWorldHint": False,
                    },
                }
                for name in PRIVATE_TOOLS
            ]
        }
    elif method == "tools/call":
        name = params.get("name")
        if (
            not isinstance(name, str)
            or name not in PRIVATE_TOOLS
            or params.get("arguments", {}) != {}
        ):
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "error": {"code": -32602, "message": "Unknown tool or unsupported arguments"},
            }
        data = dispatch(store, token, "GET", PRIVATE_TOOLS[name], {})
        result = {
            "content": [{"type": "text", "text": json.dumps(data)}],
            "structuredContent": data,
            "isError": False,
        }
    elif method == "ping":
        result = {}
    else:
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "error": {"code": -32601, "message": "Method not found"},
        }
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def create_app(
    store: Store, *, hosts: list[str] | None = None, origins: list[str] | None = None
) -> Starlette:
    async def health(request: Request) -> Response:
        try:
            with store.connect() as db:
                store.verify(db)
        except ExchangeError:
            return JSONResponse({"status": "integrity_failure"}, status_code=503)
        return JSONResponse({"status": "ok", "service": "confidential-employer-exchange"})

    async def page(request: Request) -> Response:
        name = request.path_params.get("asset", "index.html")
        if name not in {"index.html", "app.js", "style.css"}:
            return Response(status_code=404)
        return FileResponse(ASSETS / name)

    async def api(request: Request) -> Response:
        try:
            auth = request.headers.get("authorization", "")
            if not auth.startswith("Bearer ") or len(auth) > 256:
                raise ExchangeError("Bearer credential required", 401)
            content = bytearray()
            async for chunk in request.stream():
                content.extend(chunk)
                if len(content) > 16384:
                    raise ExchangeError("Request too large", 413)
            body = json.loads(content) if content else {}
            if not isinstance(body, dict):
                raise ExchangeError("JSON object required")
            if request.url.path == "/mcp":
                result = await run_in_threadpool(mcp_request, store, auth[7:], body)
                return Response(status_code=202) if result is None else JSONResponse(result)
            result = await run_in_threadpool(
                dispatch, store, auth[7:], request.method, request.url.path, body
            )
            return JSONResponse(result)
        except ExchangeError as exc:
            return JSONResponse({"error": str(exc)}, status_code=exc.status)
        except ValidationError as exc:
            return JSONResponse(
                {
                    "error": "Invalid fields",
                    "fields": [
                        {"field": ".".join(map(str, e["loc"])), "type": e["type"]}
                        for e in exc.errors()
                    ],
                },
                status_code=422,
            )
        except (ValueError, UnicodeDecodeError):
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    return Starlette(
        routes=[
            Route("/health", health),
            Route("/mcp", api, methods=["POST"]),
            Route("/", page),
            Route("/assets/{asset}", page),
            Route("/api/{path:path}", api, methods=["GET", "POST", "DELETE"]),
        ],
        middleware=[
            Middleware(TrustedHostMiddleware, allowed_hosts=hosts or ["localhost", "127.0.0.1"]),
            Middleware(
                Guard, origins=origins or ["http://localhost:8085", "http://127.0.0.1:8085"]
            ),
        ],
    )


def main() -> None:
    store = Store(
        Path(os.environ.get("EXCHANGE_DATABASE", "/confidential/exchange.sqlite3")),
        os.environ["EXCHANGE_ENCRYPTION_KEY"],
        os.environ["EXCHANGE_OPERATOR_TOKEN"],
    )
    port = int(os.environ.get("EXCHANGE_PORT", "8085"))
    app = create_app(store, origins=[f"http://localhost:{port}", f"http://127.0.0.1:{port}"])
    uvicorn.run(app, host="0.0.0.0", port=port, access_log=False, proxy_headers=False)


if __name__ == "__main__":
    main()
