import importlib.util
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


if __name__ == "__main__":
    unittest.main()
