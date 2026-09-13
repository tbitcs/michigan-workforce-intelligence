from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class PartnerInstitution:
    """A partner university/institution tracked for workforce pipeline analysis."""

    unitid: str
    name: str
    city: str
    state: str
    control: str  # P=private, P1=private non-profit, P2=private for-profit, P4=private religious
    sector: str
    iclevel: str  # 1=4-year, 2=2-year, 3=1-year, 4=sub-1-year
    focus_areas: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return f"{self.name} ({self.city}, {self.state})"


# IDs checked against NCES IPEDS; Oakland control checked at oakland.edu/about/.
# Focus-area notes are curated context, not ingested outcomes or proof of partnership.
# These are the primary partner institutions for the Michigan workforce pipeline.
PARTNER_INSTITUTIONS: tuple[PartnerInstitution, ...] = (
    PartnerInstitution(
        unitid="170675",
        name="Lawrence Technological University",
        city="Southfield",
        state="MI",
        control="P1",
        sector="Private non-profit",
        iclevel="1",
        focus_areas=("engineering", "applied_science", "business", "health_sciences"),
        metadata={
            "note": "Strong engineering and applied science pipeline; close ties to "
            "automotive and advanced manufacturing employers in Metro Detroit.",
        },
    ),
    PartnerInstitution(
        unitid="170967",
        name="Rochester Christian University",
        city="Rochester Hills",
        state="MI",
        control="P1",
        sector="Private non-profit",
        iclevel="1",
        focus_areas=("business", "health_sciences", "human_services", "technology"),
        metadata={
            "note": "Christian institution in Rochester Hills; strong in business, "
            "health, and human services programs serving Oakland County.",
        },
    ),
    PartnerInstitution(
        unitid="171571",
        name="Oakland University",
        city="Rochester Hills",
        state="MI",
        control="Public",
        sector="Public",
        iclevel="1",
        focus_areas=("engineering", "computer_science", "business", "health_sciences", "applied_science"),
        metadata={
            "note": "Public doctoral research university in Rochester Hills; broad "
            "engineering, CS, business, and health programs; strong employer partnerships.",
        },
    ),
    PartnerInstitution(
        unitid="169983",
        name="Kettering University",
        city="Flint",
        state="MI",
        control="P1",
        sector="Private non-profit",
        iclevel="1",
        focus_areas=("engineering", "applied_science", "business", "technology"),
        metadata={
            "note": "Applied research university in Flint; strong engineering and "
            "technology pipeline serving Genesee County and the Flint region.",
        },
    ),
)

PARTNER_UNITIDS: frozenset[str] = frozenset(inst.unitid for inst in PARTNER_INSTITUTIONS)


def get_partner_institution(unitid: str) -> PartnerInstitution | None:
    """Look up a partner institution by IPEDS UnitID."""
    for inst in PARTNER_INSTITUTIONS:
        if inst.unitid == unitid:
            return inst
    return None


def partner_institutions_by_focus(focus: str) -> tuple[PartnerInstitution, ...]:
    """Return partner institutions that list a given focus area."""
    return tuple(inst for inst in PARTNER_INSTITUTIONS if focus in inst.focus_areas)
