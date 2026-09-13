"""MCP protocol readiness probe used by Docker health checks."""
from __future__ import annotations

import httpx

from mijobs.mcp_server import http_port


def check(client: httpx.Client, port: int) -> bool:
    try:
        response = client.post(
            f'http://127.0.0.1:{port}/mcp',
            headers={'Accept': 'application/json, text/event-stream'},
            json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
                'protocolVersion': '2025-11-25', 'capabilities': {},
                'clientInfo': {'name': 'mijobs-health', 'version': '1.0'},
            }},
        )
        response.raise_for_status()
        payload = response.json()
        return (isinstance(payload, dict) and isinstance(payload.get('result'), dict)
                and bool(payload['result'].get('protocolVersion')))
    except (httpx.HTTPError, ValueError):
        return False


def main() -> int:
    with httpx.Client(timeout=4) as client:
        return 0 if check(client, http_port()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
