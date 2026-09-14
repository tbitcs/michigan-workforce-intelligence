from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mijobs.exchange.store import ExchangeError, Store


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class Employer(Input):
    name: str = Field(min_length=2, max_length=100)
    credential_days: int = Field(default=30, ge=1, le=90)
    identity_verified: Literal[True]


class Signal(Input):
    kind: Literal["surplus", "hiring"]
    county: Literal["26099", "26125", "26163"]
    occupation: str = Field(pattern=r"^\d{2}-\d{4}$")
    skills: list[str] = Field(default_factory=list, max_length=30)
    headcount: int = Field(ge=1, le=10000)
    earliest: date
    latest: date
    expires: date
    minimum_hourly_wage: float = Field(gt=0, le=1000)
    hours_per_week: float = Field(gt=0, le=60)
    confidence: Literal["tentative", "confirmed"] = "tentative"
    share_with_network: bool = False

    @model_validator(mode="after")
    def dates_and_skills(self) -> Signal:
        today = date.today()
        if not today <= self.earliest <= self.latest <= today + timedelta(days=365):
            raise ValueError("Signal dates must be ordered within the next year")
        if not today <= self.expires <= min(self.latest, today + timedelta(days=90)):
            raise ValueError("Signal expiry must be within 90 days and no later than latest date")
        if any(not 1 <= len(s.strip()) <= 60 for s in self.skills):
            raise ValueError("Each skill must contain 1-60 characters")
        self.skills = sorted({s.casefold().strip() for s in self.skills})
        return self


class Proposal(Input):
    surplus_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    hiring_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    headcount: int = Field(ge=1, le=10000)
    worker_consent_attested: Literal[True]


class Decision(Input):
    action: Literal["accept", "decline", "withdraw", "started"]
    start_date: date | None = None
    hourly_wage: float | None = Field(default=None, gt=0, le=1000)
    hours_per_week: float | None = Field(default=None, gt=0, le=60)
    benefits_confirmed: bool = False
    actual_start_date: date | None = None


class Service:
    def __init__(self, store: Store, db: sqlite3.Connection, actor: str):
        self.store, self.db, self.actor = store, db, actor

    def own(self, record: dict[str, Any]) -> None:
        if record["tenant"] != self.actor and self.actor != "operator":
            raise ExchangeError("Record not found", 404)

    def employers(self) -> list[dict[str, Any]]:
        if self.actor != "operator":
            raise ExchangeError("Operator access required", 403)
        return self.store.list(self.db, "employer")

    def revoke(self, rid: str) -> dict[str, Any]:
        if self.actor != "operator":
            raise ExchangeError("Operator access required", 403)
        employer = self.store.get(self.db, rid, "employer")
        employer["active"] = False
        self.store.put(
            self.db, kind="employer", tenant=rid, record_id=rid, actor=self.actor, payload=employer
        )
        return {"revoked": rid}

    def signals(self) -> list[dict[str, Any]]:
        return [
            s
            for s in self.store.list(self.db, "signal")
            if self.actor == "operator" or s["tenant"] == self.actor
        ]

    def create_signal(self, signal: Signal) -> dict[str, Any]:
        if self.actor == "operator":
            raise ExchangeError("Use an employer credential to submit signals", 403)
        if len(self.signals()) >= 500:
            raise ExchangeError("Pilot signal capacity reached", 409)
        rid = self.store.put(
            self.db,
            kind="signal",
            tenant=self.actor,
            actor=self.actor,
            payload={
                **signal.model_dump(mode="json"),
                "closed": False,
                "source_class": "employer_self_report",
            },
        )
        return self.store.get(self.db, rid, "signal")

    def close_signal(self, rid: str) -> dict[str, Any]:
        signal = self.store.get(self.db, rid, "signal")
        self.own(signal)
        signal.update(closed=True, share_with_network=False)
        self.store.put(
            self.db,
            kind="signal",
            tenant=signal["tenant"],
            actor=self.actor,
            record_id=rid,
            payload=signal,
        )
        return signal

    def active(self, signal: dict[str, Any]) -> bool:
        employer = self.store.get(self.db, signal["tenant"], "employer")
        return bool(
            not signal["closed"]
            and signal["share_with_network"]
            and signal["expires"] >= date.today().isoformat()
            and employer["active"]
            and employer["expires"] >= date.today().isoformat()
        )

    def compatible(self, surplus: dict[str, Any], hiring: dict[str, Any]) -> bool:
        return bool(
            surplus["kind"] == "surplus"
            and hiring["kind"] == "hiring"
            and surplus["tenant"] != hiring["tenant"]
            and self.active(surplus)
            and self.active(hiring)
            and surplus["occupation"] == hiring["occupation"]
            and surplus["county"] == hiring["county"]
            and max(surplus["earliest"], hiring["earliest"])
            <= min(surplus["latest"], hiring["latest"])
            and hiring["minimum_hourly_wage"] >= surplus["minimum_hourly_wage"]
            and hiring["hours_per_week"] >= surplus["hours_per_week"]
        )

    def matches(self) -> list[dict[str, Any]]:
        own = [s for s in self.signals() if s["kind"] == "surplus" and self.active(s)]
        hiring = [s for s in self.store.list(self.db, "signal") if s["kind"] == "hiring"]
        results = []
        for surplus in own:
            for job in hiring:
                if self.compatible(surplus, job):
                    results.append(
                        {
                            "surplus_id": surplus["id"],
                            "hiring": job,
                            "employer": self.store.get(self.db, job["tenant"], "employer")["name"],
                            "shared_skills": sorted(set(surplus["skills"]) & set(job["skills"])),
                            "remaining_requirements": sorted(
                                set(job["skills"]) - set(surplus["skills"])
                            ),
                            "reason": "Same county and SOC, overlapping dates, stated wage/hours floor met. Credentials, commute, worker choice and actual offer still require review.",
                        }
                    )
        return results[:500]

    def transitions(self) -> list[dict[str, Any]]:
        return [
            t
            for t in self.store.list(self.db, "transition")
            if self.actor == "operator" or self.actor in (t["tenant"], t["receiving_tenant"])
        ]

    def propose(self, proposal: Proposal) -> dict[str, Any]:
        surplus = self.store.get(self.db, proposal.surplus_id, "signal")
        if surplus["tenant"] != self.actor:
            raise ExchangeError("Record not found", 404)
        hiring = self.store.get(self.db, proposal.hiring_id, "signal")
        if not self.compatible(surplus, hiring):
            raise ExchangeError("Signals are not currently shareable and compatible", 409)
        if proposal.headcount > min(surplus["headcount"], hiring["headcount"]):
            raise ExchangeError("Headcount exceeds signal capacity", 409)
        data = {
            **proposal.model_dump(mode="json"),
            "receiving_tenant": hiring["tenant"],
            "status": "proposed",
            "proposed_at": date.today().isoformat(),
            "source_class": "employer_attestation",
        }
        rid = self.store.put(
            self.db, kind="transition", tenant=self.actor, actor=self.actor, payload=data
        )
        return self.store.get(self.db, rid, "transition")

    def decide(self, rid: str, decision: Decision) -> dict[str, Any]:
        t = self.store.get(self.db, rid, "transition")
        if self.actor not in (t["tenant"], t["receiving_tenant"]):
            raise ExchangeError("Record not found", 404)
        action = decision.action
        if action in {"accept", "decline", "started"} and self.actor != t["receiving_tenant"]:
            raise ExchangeError("Receiving employer action required", 403)
        if action == "withdraw":
            if t["status"] not in {"proposed", "accepted"}:
                raise ExchangeError("Only pending or accepted transitions can be withdrawn", 409)
            t["status"] = "withdrawn"
        elif action == "decline":
            if t["status"] != "proposed":
                raise ExchangeError("Only proposed transitions can be declined", 409)
            t["status"] = "declined"
        elif action == "accept":
            if t["status"] != "proposed":
                raise ExchangeError("Transition is not proposed", 409)
            surplus = self.store.get(self.db, t["surplus_id"], "signal")
            hiring = self.store.get(self.db, t["hiring_id"], "signal")
            if not self.compatible(surplus, hiring):
                raise ExchangeError("Signals expired, withdrawn or incompatible", 409)
            if decision.start_date is None or not max(
                surplus["earliest"], hiring["earliest"]
            ) <= decision.start_date.isoformat() <= min(surplus["latest"], hiring["latest"]):
                raise ExchangeError("Confirm a start date within both signal windows")
            if (
                decision.hourly_wage is None
                or decision.hourly_wage < hiring["minimum_hourly_wage"]
                or decision.hours_per_week is None
                or decision.hours_per_week < hiring["hours_per_week"]
                or not decision.benefits_confirmed
            ):
                raise ExchangeError("Confirm wage, hours and benefits meeting the posted offer")
            all_transitions = self.store.list(self.db, "transition")
            for field, signal in [("surplus_id", surplus), ("hiring_id", hiring)]:
                reserved = sum(
                    x["headcount"]
                    for x in all_transitions
                    if x[field] == signal["id"] and x["status"] in {"accepted", "started"}
                )
                if reserved + t["headcount"] > signal["headcount"]:
                    raise ExchangeError("Signal capacity already committed", 409)
            t.update(
                status="accepted",
                offer={
                    "start_date": decision.start_date.isoformat(),
                    "hourly_wage": decision.hourly_wage,
                    "hours_per_week": decision.hours_per_week,
                    "benefits_confirmed": True,
                },
            )
        else:
            if (
                t["status"] != "accepted"
                or decision.actual_start_date is None
                or not date.fromisoformat(t["offer"]["start_date"])
                <= decision.actual_start_date
                <= date.today()
            ):
                raise ExchangeError(
                    "An accepted offer and valid actual start date are required", 409
                )
            t.update(status="started", actual_start_date=decision.actual_start_date.isoformat())
        self.store.put(
            self.db,
            kind="transition",
            tenant=t["tenant"],
            actor=self.actor,
            record_id=rid,
            payload=t,
        )
        return t
