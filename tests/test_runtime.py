from __future__ import annotations

import httpx
import pytest

from mijobs import healthcheck, mcp_server


def test_http_server_options(monkeypatch):
    calls = []
    class Server:
        def run(self, **kwargs):
            calls.append(kwargs)
    monkeypatch.setattr(mcp_server, 'build_server', Server)
    monkeypatch.setenv('MIJOBS_MCP_PORT', '8123')
    mcp_server.serve_http()
    security = calls[0].pop('transport_security')
    assert security.enable_dns_rebinding_protection is True
    assert '127.0.0.1:8123' in security.allowed_hosts
    assert security.allowed_origins == []
    assert calls == [dict(transport='streamable-http', host='0.0.0.0', port=8123,
                          json_response=True, stateless_http=True)]


@pytest.mark.parametrize('value', ['bad', '0', '65536'])
def test_bad_port_rejected(monkeypatch, value):
    monkeypatch.setenv('MIJOBS_MCP_PORT', value)
    with pytest.raises(ValueError, match='port'):
        mcp_server.http_port()


def test_http_health_checks_protocol():
    def respond(request):
        assert request.method == 'POST'
        assert b'initialize' in request.content
        return httpx.Response(200, json={'jsonrpc': '2.0', 'id': 1, 'result': {'protocolVersion': '2025-11-25'}})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        assert healthcheck.check(client, 8000)


@pytest.mark.parametrize('payload', [{'error': {'code': -1}}, [], {'result': {}}])
def test_health_rejects_bad_responses(payload):
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))) as client:
        assert not healthcheck.check(client, 8000)


def test_health_unavailable():
    def fail(request):
        raise httpx.ConnectError('unavailable')
    with httpx.Client(transport=httpx.MockTransport(fail)) as client:
        assert not healthcheck.check(client, 8000)


@pytest.mark.parametrize('headers,status', [({}, 200), ({'Host': 'untrusted.example'}, 421), ({'Origin': 'https://untrusted.example'}, 403)])
def test_http_rebinding_protection(tmp_path, monkeypatch, headers, status):
    from starlette.testclient import TestClient

    monkeypatch.setenv('MIJOBS_DATABASE_URL', f"sqlite:///{tmp_path / 'http.db'}")
    monkeypatch.setenv('MIJOBS_MCP_PORT', '8000')
    monkeypatch.delenv('MIJOBS_MCP_ALLOWED_HOSTS', raising=False)
    monkeypatch.delenv('MIJOBS_MCP_ALLOWED_ORIGINS', raising=False)
    server = mcp_server.build_server()
    options = {}
    monkeypatch.setattr(server, 'run', lambda **kwargs: options.update(kwargs))
    monkeypatch.setattr(mcp_server, 'build_server', lambda: server)
    mcp_server.serve_http()
    app = server.streamable_http_app(
        stateless_http=True, json_response=True,
        transport_security=options['transport_security'],
    )
    with TestClient(app, base_url='http://127.0.0.1:8000') as client:
        response = client.post('/mcp', headers={'Accept': 'application/json, text/event-stream', **headers}, json={
            'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
                'protocolVersion': '2025-11-25', 'capabilities': {},
                'clientInfo': {'name': 'security-test', 'version': '1'},
            },
        })
        assert response.status_code == status
