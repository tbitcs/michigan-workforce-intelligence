from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from mijobs.config import Settings, load_source_catalog
from mijobs.db import initialize_database, make_engine, session_factory
from mijobs.mcp_service import MCPService

T = TypeVar("T")


def build_server() -> Any:
    try:
        from mcp.server import MCPServer
    except ImportError as exc:
        raise RuntimeError("Install the MCP extra: pip install -e '.[mcp]'") from exc

    settings = Settings.from_env()
    engine = make_engine(settings.database_url)
    initialize_database(engine)
    factory = session_factory(engine)
    catalog = load_source_catalog()
    mcp = MCPServer("Michigan Workforce Intelligence")

    def call(fn: Callable[[MCPService], T]) -> T:
        with factory() as session:
            return fn(MCPService(session, catalog, write_enabled=settings.mcp_write_enabled))

    @mcp.tool()
    def sources_list() -> dict[str, Any]:
        """List reviewed official workforce/education source families and methodology notes."""
        return call(lambda service: service.sources_list())

    @mcp.tool()
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

    @mcp.tool()
    def artifacts_get(artifact_id: str) -> dict[str, Any]:
        """Get provenance metadata for one immutable raw source artifact."""
        return call(lambda service: service.artifacts_get(artifact_id))

    @mcp.tool()
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

    @mcp.tool()
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

    @mcp.tool()
    def claims_get(claim_id: str) -> dict[str, Any]:
        """Get one claim and its effective epistemic status."""
        return call(lambda service: service.claims_get(claim_id))

    @mcp.tool()
    def claims_trace(claim_id: str) -> dict[str, Any]:
        """Trace a claim to evidence, source artifacts, revisions, and challenges."""
        return call(lambda service: service.claims_trace(claim_id))

    @mcp.tool()
    def ledger_verify() -> dict[str, Any]:
        """Verify the append-only SHA-256 event chain."""
        return call(lambda service: service.ledger_verify())

    @mcp.tool()
    def ledger_audit() -> dict[str, Any]:
        """Verify both hash-chain integrity and coverage of all evidence-bearing rows."""
        return call(lambda service: service.ledger_audit())

    @mcp.tool()
    def gap_training_pipeline(payload: dict[str, Any]) -> dict[str, Any]:
        """Calculate a narrow occupation training-pipeline gap using compatible annual metrics."""
        return call(lambda service: service.gap_training_pipeline(payload))

    @mcp.tool()
    def gap_market_tightness(online_job_ads: str, available_people: str) -> dict[str, Any]:
        """Calculate a simple job-ad/available-person signal with explicit caveats."""
        return call(lambda service: service.gap_market_tightness(online_job_ads, available_people))

    @mcp.tool()
    def policy_training_scenario(payload: dict[str, Any]) -> dict[str, Any]:
        """Evaluate explicit low/base/high training-policy assumptions; no causal rates are inferred."""
        return call(lambda service: service.policy_training_scenario(payload))

    @mcp.tool()
    def report_context(claim_ids: list[str]) -> dict[str, Any]:
        """Build evidence-linked structured context for report generation."""
        return call(lambda service: service.report_context(claim_ids))

    @mcp.tool()
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


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
