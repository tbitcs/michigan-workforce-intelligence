"""Publish only verified report assets from a timestamped build directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from reports import version


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=os.getenv("REPORT_VERSION"))
    parser.add_argument("--directory", default="release-assets")
    args = parser.parse_args()
    stamp = version(args.version)
    directory = Path(args.directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest["version"] != stamp:
        raise ValueError("Manifest version does not match release")
    allowed = {
        "jobs-economic-report.pdf",
        "executive-brief.pdf",
        "job-continuity-solutions.pdf",
        "manifest.json",
        "SHA256SUMS.txt",
        f"reports-{stamp}.zip",
    }
    checksums = {}
    for line in (directory / "SHA256SUMS.txt").read_text().splitlines():
        digest, name = line.split("  ", 1)
        if Path(name).name != name:
            raise ValueError("Unexpected checksum path")
        checksums[name] = digest
    for name in allowed - {"SHA256SUMS.txt"}:
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != checksums[name]:
            raise ValueError(f"Checksum mismatch: {name}")
    notes = directory / "release-notes.md"
    notes.write_text(
        "Michigan county/state jobs and economic report, with supplemental job continuity and Job Corps proposals.\n\nEvidence reviewed September 13, 2026; observation periods and limitations appear in each report. APEX and Velocity are candidate partners, not committed participants. Employer case management is proposed, not deployed.\n\nData credits and O*NET attribution are included in every PDF and the package. See THIRD_PARTY_NOTICES.md in the repository.\n",
        encoding="utf-8",
    )
    subprocess.run(
        [
            "gh",
            "release",
            "create",
            f"reports-{stamp}",
            "--target",
            os.environ["GITHUB_SHA"],
            "--title",
            f"Michigan workforce reports {stamp}",
            "--notes-file",
            str(notes),
            *[str(directory / n) for n in sorted(allowed)],
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
