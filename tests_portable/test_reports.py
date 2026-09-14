import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "reports", Path(__file__).resolve().parents[1] / "scripts/reports.py"
)
reports = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reports)


class PortableReports(unittest.TestCase):
    def test_timestamp_rejects_shell_and_invalid_calendar(self):
        self.assertEqual(reports.version("2026.09.13.120000Z"), "2026.09.13.120000Z")
        for invalid in ["2026.02.30.120000Z", "2026.09.13.120000Z;echo bad", "../report", ""]:
            if invalid:
                with self.assertRaises(ValueError):
                    reports.version(invalid)

    def test_paths_are_arguments_and_evidence_readonly(self):
        with (
            patch.object(reports, "ROOT", Path("workspace with spaces")),
            patch.dict(reports.os.environ, {"GITHUB_SHA": "test"}),
        ):
            command = reports.container("scripts/reanalyze_data.py", evidence=True)
        self.assertIn("type=bind,src=workspace with spaces,dst=/workspace", command)
        self.assertTrue(any("dst=/data,readonly" in arg for arg in command))
        self.assertEqual(command[-1], "scripts/reanalyze_data.py")

    def test_offline_build_has_no_credentials_or_volume(self):
        command = reports.container("scripts/build_reports.py")
        self.assertNotIn("--env-file", command)
        self.assertFalse(any("dst=/data" in arg for arg in command))

    def test_failure_propagates(self):
        with patch.object(reports.subprocess, "run", side_effect=RuntimeError("failed")):
            with self.assertRaises(RuntimeError):
                reports.run(["docker", "info"])


class ReplacementRelease(unittest.TestCase):
    def test_corrupt_package_never_deletes_release(self):
        self.run_replacement(corrupt=True)

    def test_valid_package_deletes_old_release_before_dispatch(self):
        self.run_replacement(corrupt=False)

    def run_replacement(self, corrupt):
        stamp = "2026.09.14.010000Z"
        old = "reports-2026.09.13.231357Z"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / "output/pdf" / stamp
            out.mkdir(parents=True)
            for name in [
                "executive-brief.pdf",
                "jobs-economic-report.pdf",
                "job-continuity-solutions.pdf",
                f"reports-{stamp}.zip",
            ]:
                (out / name).write_bytes(b"synthetic-package-test")
            (out / "manifest.json").write_text(
                json.dumps({"version": stamp, "source_commit": "head"})
            )
            (out / "SHA256SUMS.txt").write_text(
                "\n".join(
                    hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name
                    for p in out.iterdir()
                    if p.name != "SHA256SUMS.txt"
                )
            )
            if corrupt:
                (out / "executive-brief.pdf").write_bytes(b"changed")
            with (
                patch.object(reports, "ROOT", root),
                patch.object(reports.subprocess, "check_output", side_effect=["", "head"]),
                patch.object(reports, "run") as run,
                patch(
                    "sys.argv",
                    ["reports.py", "release", "--version", stamp, "--replace-release", old],
                ),
            ):
                if corrupt:
                    with self.assertRaises(SystemExit):
                        reports.main()
                    run.assert_not_called()
                else:
                    reports.main()
                    self.assertEqual(
                        run.call_args_list[-2].args[0], ["gh", "release", "delete", old, "--yes"]
                    )
                    self.assertEqual(run.call_args_list[-1].args[0][:3], ["gh", "workflow", "run"])


if __name__ == "__main__":
    unittest.main()
