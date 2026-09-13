from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    artifact_root: Path
    mcp_write_enabled: bool
    bls_api_key: str | None
    census_api_key: str | None
    onet_username: str | None
    onet_password: str | None

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            database_url=os.getenv("MIJOBS_DATABASE_URL", "sqlite:///./mijobs.db"),
            artifact_root=Path(os.getenv("MIJOBS_ARTIFACT_ROOT", "./artifacts/raw")),
            mcp_write_enabled=os.getenv("MIJOBS_MCP_WRITE_ENABLED", "false").lower()
            in {"1", "true", "yes", "on"},
            bls_api_key=os.getenv("BLS_API_KEY") or None,
            census_api_key=os.getenv("CENSUS_API_KEY") or None,
            onet_username=os.getenv("ONET_USERNAME") or None,
            onet_password=os.getenv("ONET_PASSWORD") or None,
        )


class SourceDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    publisher: str
    jurisdiction: str
    authority: str
    domain: str
    landing_url: HttpUrl
    api_url: HttpUrl | None = None
    access_mode: str
    credential_env: str | None = None
    topics: list[str]
    geographies: list[str]
    cadence: str
    methodology_notes: str
    implementation_status: str = "catalog_only"
    attribution: str = "Credit the named publisher and original release; no endorsement implied."
    license_url: str | None = None
    api_policy: str = "No automated endpoint enabled until its access rules are reviewed."

    @field_validator("domain")
    @classmethod
    def official_domain(cls, value: str) -> str:
        allowed = (
            value in {"bea.gov", "dol.gov", "federalreserve.gov", "newyorkfed.org", "jobcorps.gov", "huduser.gov", "eia.gov"}
            or value == "michigan.gov"
            or value.endswith(".michigan.gov")
            or value == "bls.gov"
            or value.endswith(".bls.gov")
            or value == "census.gov"
            or value.endswith(".census.gov")
            or value == "nces.ed.gov"
            or value.endswith(".ed.gov")
            or value == "onetcenter.org"
            or value.endswith(".onetcenter.org")
            or value == "apprenticeship.gov"
            or value.endswith(".apprenticeship.gov")
        )
        if not allowed:
            raise ValueError(f"source domain is not in reviewed official allow-list: {value}")
        return value


class SourceCatalog(BaseModel):
    schema_version: str
    reviewed_at: str
    sources: list[SourceDefinition]

    def by_id(self, source_id: str) -> SourceDefinition:
        for source in self.sources:
            if source.id == source_id:
                return source
        raise KeyError(source_id)


def load_source_catalog(path: str | Path | None = None) -> SourceCatalog:
    if path is None:
        root = Path(__file__).resolve().parents[2]
        path = root / "config" / "sources.json"
    raw: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    catalog = SourceCatalog.model_validate(raw)
    ids = [source.id for source in catalog.sources]
    if len(ids) != len(set(ids)):
        raise ValueError("source IDs must be unique")
    return catalog
