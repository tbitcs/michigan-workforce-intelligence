"""Portable host launcher. Python standard library plus Docker; gh only for releases."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "michigan-workforce-reports:local"


def version(value: str | None = None) -> str:
    value = value or datetime.now(UTC).strftime("%Y.%m.%d.%H%M%SZ")
    if not re.fullmatch(r"\d{4}\.\d{2}\.\d{2}\.\d{6}Z", value):
        raise ValueError("Version must be UTC YYYY.MM.DD.HHMMSSZ")
    datetime.strptime(value, "%Y.%m.%d.%H%M%SZ")
    return value


def run(args: list[str]) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def container(
    script: str, extra: list[str] | None = None, *, evidence: bool = False, write: bool = False
) -> list[str]:
    cmd = ["docker", "run", "--rm", "--init"]
    if not evidence and os.name != "nt" and hasattr(os, "getuid"):
        cmd += ["--user", f"{os.getuid()}:{os.getgid()}"]
    cmd += [
        "--mount",
        f"type=bind,src={ROOT},dst=/workspace",
        "--workdir",
        "/workspace",
        "--env",
        "MPLCONFIGDIR=/tmp/matplotlib",
    ]
    if evidence:
        cmd += [
            "--env-file",
            str(ROOT / ".env"),
            "--mount",
            "type=volume,src="
            + os.getenv("MIJOBS_EVIDENCE_VOLUME", "michigan-workforce-intelligence_evidence")
            + ",dst=/data"
            + ("" if write else ",readonly"),
        ]
    commit = (
        os.getenv("GITHUB_SHA")
        or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    )
    cmd += ["--env", "REPORT_SOURCE_COMMIT=" + commit]
    if evidence and os.name != "nt" and hasattr(os, "getgid"):
        cmd += ["--env", f"MIJOBS_HOST_GID={os.getgid()}"]
        cmd += [IMAGE, "python", "scripts/run_report_task.py", script, *(extra or [])]
    else:
        cmd += [IMAGE, "python", script, *(extra or [])]
    return cmd


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "build-image",
            "collect",
            "collect-qcew",
            "collect-reference",
            "collect-comparisons",
            "collect-hardship",
            "analyze",
            "build",
            "release",
            "version",
        ],
    )
    parser.add_argument("--version", default=os.getenv("REPORT_VERSION"))
    parser.add_argument(
        "--replace-release",
        help="Explicit old reports-timestamp release to delete after validating the replacement package; preserves its Git tag",
    )
    args = parser.parse_args()
    if args.command == "build-image":
        run(["docker", "build", "--target", "reports", "--tag", IMAGE, "."])
    elif args.command == "collect":
        run(container("scripts/collect_indicators.py", evidence=True, write=True))
    elif args.command.startswith("collect-"):
        scripts = {
            "collect-qcew": "collect_qcew.py",
            "collect-reference": "collect_reference_data.py",
            "collect-comparisons": "collect_comparisons.py",
            "collect-hardship": "collect_hardship.py",
        }
        run(container("scripts/" + scripts[args.command], evidence=True, write=True))
    elif args.command == "analyze":
        run(container("scripts/reanalyze_data.py", evidence=True))
    elif args.command == "build":
        run(container("scripts/build_reports.py", ["--version", version(args.version)]))
    elif args.command == "release":
        stamp = version(args.version)
        if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
            raise SystemExit("Commit reviewed sources before releasing")
        if args.replace_release:
            old = args.replace_release
            if not old.startswith("reports-") or old == "reports-" + stamp:
                raise SystemExit("Expected a different reports-timestamp release")
            version(old.removeprefix("reports-"))
            directory = ROOT / "output/pdf" / stamp
            manifest = json.loads((directory / "manifest.json").read_text())
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip()
            if manifest["version"] != stamp or manifest["source_commit"] != head:
                raise SystemExit("Build the replacement from the current clean commit first")
            required = {
                "executive-brief.pdf",
                "jobs-economic-report.pdf",
                "job-continuity-solutions.pdf",
                "manifest.json",
                f"reports-{stamp}.zip",
            }
            checked = set()
            for line in (directory / "SHA256SUMS.txt").read_text().splitlines():
                digest, name = line.split("  ", 1)
                if (
                    Path(name).name != name
                    or hashlib.sha256((directory / name).read_bytes()).hexdigest() != digest
                ):
                    raise SystemExit("Replacement checksum verification failed")
                checked.add(name)
            if not required <= checked:
                raise SystemExit("Replacement package is incomplete")
            run(["gh", "release", "view", old, "--json", "tagName"])
            run(["gh", "release", "delete", old, "--yes"])
        run(["gh", "workflow", "run", "reports-release.yml", "-f", f"version={stamp}"])
        print(f"Requested reports-{stamp}. Use gh run list --workflow reports-release.yml")
    else:
        print(version(args.version))


if __name__ == "__main__":
    main()
