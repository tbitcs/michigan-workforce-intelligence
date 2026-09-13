from __future__ import annotations

import inspect
import sys
import types
from collections.abc import Callable
from pathlib import Path

import pytest

from mijobs import mcp_server


class FakeMCPServer:
    def __init__(self, name: str, *, instructions: str = ""):
        self.instructions = instructions
        self.annotations = {}
        self.name = name
        self.tools: dict[str, Callable] = {}
        self.ran = False

    def tool(self, *, annotations=None):
        def decorator(fn: Callable) -> Callable:
            self.tools[fn.__name__] = fn
            self.annotations[fn.__name__] = annotations
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
    types_mod = types.ModuleType("mcp.types")
    types_mod.ToolAnnotations = lambda **kwargs: kwargs
    monkeypatch.setitem(sys.modules, "mcp.types", types_mod)


def test_build_server_exposes_explicit_public_signatures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_mcp(monkeypatch)
    monkeypatch.setenv("MIJOBS_DATABASE_URL", f"sqlite:///{tmp_path / 'mcp.db'}")
    server = mcp_server.build_server()
    assert isinstance(server, FakeMCPServer)
    expected = {
        "sources_list",
        "economic_indicators",
        "economic_trend",
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
        "university_degree_relevance",
        "university_pipeline_balance",
        "university_retention_risk",
        "business_attraction",
        "university_summary",
        "partner_institutions_list",
        "report_context",
        "claims_challenge",
    }
    assert set(server.tools) == expected
    assert "not ingested data" in server.instructions
    assert "never invent current figures" in server.instructions
    for name, tool_hints in server.annotations.items():
        assert tool_hints["read_only_hint"] is (name != "claims_challenge")
        assert tool_hints["destructive_hint"] is False
        assert tool_hints["open_world_hint"] is False
    assert server.annotations["claims_challenge"]["idempotent_hint"] is False
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
