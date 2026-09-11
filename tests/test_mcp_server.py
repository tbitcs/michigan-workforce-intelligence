from __future__ import annotations

import inspect
import sys
import types
from pathlib import Path
from typing import Callable

import pytest

from mijobs import mcp_server


class FakeMCPServer:
    def __init__(self, name: str):
        self.name = name
        self.tools: dict[str, Callable] = {}
        self.ran = False

    def tool(self):
        def decorator(fn: Callable) -> Callable:
            self.tools[fn.__name__] = fn
            return fn

        return decorator

    def run(self) -> None:
        self.ran = True


def _install_fake_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    mcp_mod = types.ModuleType("mcp")
    server_mod = types.ModuleType("mcp.server")
    server_mod.MCPServer = FakeMCPServer
    monkeypatch.setitem(sys.modules, "mcp", mcp_mod)
    monkeypatch.setitem(sys.modules, "mcp.server", server_mod)


def test_build_server_exposes_explicit_public_signatures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_mcp(monkeypatch)
    monkeypatch.setenv("MIJOBS_DATABASE_URL", f"sqlite:///{tmp_path / 'mcp.db'}")
    server = mcp_server.build_server()
    assert isinstance(server, FakeMCPServer)
    expected = {
        "sources_list",
        "observations_search",
        "artifacts_get",
        "claims_search",
        "claims_get",
        "mappings_search",
        "claims_trace",
        "ledger_verify",
        "ledger_audit",
        "gap_training_pipeline",
        "gap_market_tightness",
        "policy_training_scenario",
        "report_context",
        "claims_challenge",
    }
    assert set(server.tools) == expected
    for fn in server.tools.values():
        assert "service" not in inspect.signature(fn).parameters
    assert server.tools["sources_list"]()["sources"]
    assert server.tools["ledger_verify"]()["valid"] is True


def test_main_runs_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_mcp(monkeypatch)
    monkeypatch.setenv("MIJOBS_DATABASE_URL", f"sqlite:///{tmp_path / 'main.db'}")
    server = mcp_server.build_server()
    monkeypatch.setattr(mcp_server, "build_server", lambda: server)
    mcp_server.main()
    assert server.ran is True
