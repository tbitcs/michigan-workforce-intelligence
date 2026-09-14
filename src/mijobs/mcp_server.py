from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, TypeVar

from mijobs.config import Settings, load_source_catalog
from mijobs.db import initialize_database, make_engine, session_factory
from mijobs.economic_context import economic_coverage, economic_series
from mijobs.mcp_service import MCPService

T = TypeVar("T")

SERVER_INSTRUCTIONS = (
    "Michigan workforce evidence tools. The source registry lists available source families, "
    "not ingested data. Search observations or claims before stating workforce facts. Empty "
    "results mean evidence is unavailable; never invent current figures. Trace claims to their "
    "artifacts and distinguish deterministic scenarios from causal evidence. "
    "Read/calculation tools do not ingest data. Ingestion coverage and official-release validation "
    "remain incomplete. Challenge writes require explicit user intent and server-side opt-in."
)


def build_server() -> Any:
    try:
        from mcp.server import MCPServer
        from mcp.types import ToolAnnotations
    except ImportError as exc:
        raise RuntimeError("Install the MCP extra: pip install -e '.[mcp]'") from exc

    read_only = ToolAnnotations(
        read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
    )
    write = ToolAnnotations(
        read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False
    )
    settings = Settings.from_env()
    engine = make_engine(settings.database_url)
    initialize_database(engine)
    factory = session_factory(engine)
    catalog = load_source_catalog()
    mcp = MCPServer("Michigan Workforce Intelligence", instructions=SERVER_INSTRUCTIONS)

    def call(fn: Callable[[MCPService], T]) -> T:
        with factory() as session:
            return fn(MCPService(session, catalog, write_enabled=settings.mcp_write_enabled))

    @mcp.tool(annotations=read_only)
    def economic_indicators(geography_code: str | None = None) -> dict[str, Any]:
        """Discover stored economic metrics for counties/states; catalog membership is not data."""
        return call(lambda service: economic_coverage(service.session, geography_code))

    @mcp.tool(annotations=read_only)
    def economic_trend(geography_code: str, metric: str, limit: int = 120) -> dict[str, Any]:
        """Read latest evidence revisions in period order with units, adjustment and provenance."""
        return call(
            lambda service: economic_series(
                service.session, geography_code=geography_code, metric=metric, limit=limit
            )
        )

    @mcp.tool(annotations=read_only)
    def sources_list() -> dict[str, Any]:
        """List reviewed official workforce/education source families and methodology notes."""
        return call(lambda service: service.sources_list())

    @mcp.tool(annotations=read_only)
    def observations_search(
        metric: str | None = None,
        geography_code: str | None = None,
        taxonomy_code: str | None = None,
        source_artifact_id: str | None = None,
        latest_only: bool = True,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Search bounded normalized observations; defaults to latest versions only."""
        return call(
            lambda service: service.observations_search(
                metric=metric,
                geography_code=geography_code,
                taxonomy_code=taxonomy_code,
                source_artifact_id=source_artifact_id,
                latest_only=latest_only,
                limit=limit,
            )
        )

    @mcp.tool(annotations=read_only)
    def artifacts_get(artifact_id: str) -> dict[str, Any]:
        """Get provenance metadata for one immutable raw source artifact."""
        return call(lambda service: service.artifacts_get(artifact_id))

    @mcp.tool(annotations=read_only)
    def claims_search(
        kind: str | None = None,
        asserted_status: str | None = None,
        latest_only: bool = True,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Search claims and return asserted plus challenge-adjusted effective status."""
        return call(
            lambda service: service.claims_search(
                kind=kind,
                asserted_status=asserted_status,
                latest_only=latest_only,
                limit=limit,
            )
        )

    @mcp.tool(annotations=read_only)
    def mappings_search(
        from_system: str | None = None,
        from_code: str | None = None,
        to_system: str | None = None,
        to_code: str | None = None,
        latest_only: bool = True,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Resolve versioned taxonomy crosswalks such as CIP to SOC and O*NET-SOC to SOC."""
        return call(
            lambda service: service.mappings_search(
                from_system=from_system,
                from_code=from_code,
                to_system=to_system,
                to_code=to_code,
                latest_only=latest_only,
                limit=limit,
            )
        )

    @mcp.tool(annotations=read_only)
    def claims_get(claim_id: str) -> dict[str, Any]:
        """Get one claim and its effective epistemic status."""
        return call(lambda service: service.claims_get(claim_id))

    @mcp.tool(annotations=read_only)
    def claims_trace(claim_id: str) -> dict[str, Any]:
        """Trace a claim to evidence, source artifacts, revisions, and challenges."""
        return call(lambda service: service.claims_trace(claim_id))

    @mcp.tool(annotations=read_only)
    def ledger_verify() -> dict[str, Any]:
        """Verify the append-only SHA-256 event chain."""
        return call(lambda service: service.ledger_verify())

    @mcp.tool(annotations=read_only)
    def ledger_audit() -> dict[str, Any]:
        """Verify both hash-chain integrity and coverage of all evidence-bearing rows."""
        return call(lambda service: service.ledger_audit())

    @mcp.tool(annotations=read_only)
    def gap_training_pipeline(payload: dict[str, Any]) -> dict[str, Any]:
        """Calculate a narrow occupation training-pipeline gap using compatible annual metrics."""
        return call(lambda service: service.gap_training_pipeline(payload))

    @mcp.tool(annotations=read_only)
    def gap_market_tightness(online_job_ads: str, available_people: str) -> dict[str, Any]:
        """Calculate a simple job-ad/available-person signal with explicit caveats."""
        return call(lambda service: service.gap_market_tightness(online_job_ads, available_people))

    @mcp.tool(annotations=read_only)
    def policy_training_scenario(payload: dict[str, Any]) -> dict[str, Any]:
        """Evaluate explicit low/base/high training-policy assumptions; no causal rates are inferred."""
        return call(lambda service: service.policy_training_scenario(payload))

    @mcp.tool(annotations=read_only)
    def university_degree_relevance(payload: dict[str, Any]) -> dict[str, Any]:
        """Explore caller-supplied completions, demand and crosswalks; does not fetch or authenticate source data."""
        return call(lambda service: service.university_degree_relevance(payload))

    @mcp.tool(annotations=read_only)
    def university_pipeline_balance(payload: dict[str, Any]) -> dict[str, Any]:
        """Explore caller-supplied pipeline counts; experimental comparison, not a measured Michigan labor shortage."""
        return call(lambda service: service.university_pipeline_balance(payload))

    @mcp.tool(annotations=read_only)
    def university_retention_risk(payload: dict[str, Any]) -> dict[str, Any]:
        """Estimate graduate retention risk using explicit caller-supplied rates; no causal inference."""
        return call(lambda service: service.university_retention_risk(payload))

    @mcp.tool(annotations=read_only)
    def business_attraction(payload: dict[str, Any]) -> dict[str, Any]:
        """Calculate a heuristic 0-1 scenario score from supplied inputs; not a validated prediction."""
        return call(lambda service: service.business_attraction(payload))

    @mcp.tool(annotations=read_only)
    def university_summary(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Summarize supplied scenarios; overlapping regional openings can be double-counted."""
        return call(lambda service: service.university_summary(payload))

    @mcp.tool(annotations=read_only)
    def partner_institutions_list() -> dict[str, Any]:
        """List all registered candidate institutions with their focus areas and metadata."""
        return call(lambda service: service.partner_institutions_list())

    @mcp.tool(annotations=read_only)
    def report_context(claim_ids: list[str]) -> dict[str, Any]:
        """Build evidence-linked structured context for report generation."""
        return call(lambda service: service.report_context(claim_ids))

    @mcp.tool(annotations=write)
    def claims_challenge(
        claim_id: str,
        rationale: str,
        challenger_ref: str | None = None,
    ) -> dict[str, Any]:
        """Append a challenge to a claim. Disabled unless MCP writes are explicitly enabled."""
        return call(
            lambda service: service.claims_challenge(
                claim_id=claim_id, rationale=rationale, challenger_ref=challenger_ref
            )
        )

    return mcp


def http_port() -> int:
    try:
        port = int(os.getenv("MIJOBS_MCP_PORT", "8000"))
    except ValueError as exc:
        raise ValueError("MCP port must be an integer between 1 and 65535") from exc
    if not 1 <= port <= 65535:
        raise ValueError("MCP port must be between 1 and 65535")
    return port


def serve_http() -> None:
    from mcp.server.transport_security import TransportSecuritySettings

    port = http_port()
    hosts = os.getenv("MIJOBS_MCP_ALLOWED_HOSTS", "127.0.0.1,localhost,workforce-mcp,app")
    origins = os.getenv("MIJOBS_MCP_ALLOWED_ORIGINS", "")
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[f"{host.strip()}:{port}" for host in hosts.split(",") if host.strip()],
        allowed_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
    )
    # Container listener; Compose publishes only on loopback. Host/Origin validation stays on.
    build_server().run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,  # nosec B104
        json_response=True,
        stateless_http=True,
        transport_security=security,
    )


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
