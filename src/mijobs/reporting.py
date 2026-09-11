from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from mijobs.epistemics import EpistemicService
from mijobs.ledger import audit_evidence_coverage, verify_ledger


class ReportContextBuilder:
    """Build structured, auditable context for a separate report-writing model."""

    def __init__(self, session: Session):
        self.session = session
        self.epistemics = EpistemicService(session)

    def build(self, claim_ids: list[str]) -> dict[str, Any]:
        verification = verify_ledger(self.session)
        if not verification.valid:
            raise RuntimeError(
                f"refusing report context from invalid ledger: {verification.reason}"
            )
        coverage = audit_evidence_coverage(self.session)
        if not coverage.valid:
            raise RuntimeError(
                f"refusing report context with unledgered evidence rows: {coverage.uncovered[:10]}"
            )
        return {
            "schema": "mijobs-report-context/v1",
            "ledger": {
                "valid": verification.valid,
                "event_count": verification.event_count,
                "head_hash": verification.head_hash,
                "coverage_valid": coverage.valid,
                "checked_entities": coverage.checked_entities,
            },
            "claims": [self.epistemics.trace_claim(claim_id) for claim_id in claim_ids],
            "writer_instructions": [
                "Treat observations and source artifacts as evidence; model prose is not evidence.",
                "Label derived/inferred/projected claims explicitly.",
                "Surface open challenges and material caveats.",
                "Do not strengthen a conclusion beyond the evidence quality and scope.",
            ],
        }
