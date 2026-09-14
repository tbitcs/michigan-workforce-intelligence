"""Audit or apply the canonical public repository's maintainer access settings."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

REPO = "tbitcs/michigan-workforce-intelligence"
ROOT = Path(__file__).resolve().parents[1]


def api(path: str, method: str = "GET", payload: dict | None = None):
    args = ["gh", "api", "--method", method, path]
    if payload is not None:
        args += ["--input", "-"]
    result = subprocess.run(
        args,
        input=json.dumps(payload) if payload is not None else None,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout) if result.stdout.strip() else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply public visibility and the reviewed maintainer ruleset",
    )
    args = parser.parse_args()
    base = "repos/" + REPO
    collaborators = api(base + "/collaborators?per_page=100")
    invitations = api(base + "/invitations?per_page=100")
    keys = api(base + "/keys?per_page=100")
    writers = [r["login"] for r in collaborators if r["permissions"].get("push")]
    if args.apply:
        if api("user")["login"] != "tbitcs" or writers != ["tbitcs"] or invitations or keys:
            raise SystemExit("Owner-only access review required before applying settings")
        api(
            base,
            "PATCH",
            {
                "private": False,
                "security_and_analysis": {
                    "secret_scanning": {"status": "enabled"},
                    "secret_scanning_push_protection": {"status": "enabled"},
                },
            },
        )
        api(
            base + "/actions/permissions/workflow",
            "PUT",
            {"default_workflow_permissions": "read", "can_approve_pull_request_reviews": False},
        )
        desired = json.loads((ROOT / ".github/maintainer-branches.json").read_text())
        existing = next(
            (r for r in api(base + "/rulesets?per_page=100") if r["name"] == desired["name"]), None
        )
        api(
            base + "/rulesets" + ("/" + str(existing["id"]) if existing else ""),
            "PUT" if existing else "POST",
            desired,
        )
    repo = api(base)
    print(
        json.dumps(
            {
                "repository": REPO,
                "private": repo["private"],
                "writers": writers,
                "pending_invitations": len(invitations),
                "deploy_keys": len(keys),
                "rulesets": api(base + "/rulesets?per_page=100"),
                "workflow_permissions": api(base + "/actions/permissions/workflow"),
                "security": repo.get("security_and_analysis"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
