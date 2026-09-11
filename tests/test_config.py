from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from mijobs.config import Settings, SourceCatalog, load_source_catalog


def test_default_source_catalog_is_unique_and_official() -> None:
    catalog = load_source_catalog()
    ids = [source.id for source in catalog.sources]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 16
    assert catalog.by_id("mi_mcda_laus").domain == "michigan.gov"
    assert catalog.by_id("us_onet").domain == "onetcenter.org"


def test_source_catalog_rejects_unreviewed_domain(tmp_path: Path) -> None:
    path = tmp_path / "sources.json"
    raw = {
        "schema_version": "1",
        "reviewed_at": "2026-09-11",
        "sources": [
            {
                "id": "bad",
                "name": "Bad",
                "publisher": "Unknown",
                "jurisdiction": "US",
                "authority": "unknown",
                "domain": "example.com",
                "landing_url": "https://example.com",
                "api_url": None,
                "access_mode": "api",
                "credential_env": None,
                "topics": ["x"],
                "geographies": ["state"],
                "cadence": "annual",
                "methodology_notes": "none",
            }
        ],
    }
    path.write_text(json.dumps(raw))
    with pytest.raises(ValidationError):
        load_source_catalog(path)


def test_settings_parse_write_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MIJOBS_MCP_WRITE_ENABLED", "yes")
    monkeypatch.setenv("MIJOBS_DATABASE_URL", "sqlite:///custom.db")
    settings = Settings.from_env()
    assert settings.mcp_write_enabled is True
    assert settings.database_url == "sqlite:///custom.db"
