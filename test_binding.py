import csv
import io
import unittest
from catalog import analyze_log, admitted_sessions
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent / "example"


class BindingTests(unittest.TestCase):
    def test_foreign_log_is_rejected(self):
        sessions = {"S1": ("v1", {"motor": "motor.txt"})}
        for line in ["S2\tv1", "S1\tv2"]:
            rows = csv.DictReader(io.StringIO("session\tversion\ttime_ms\tzone\n"
                                              + line + "\t0\tmotor\n"), delimiter="\t")
            with self.assertRaisesRegex(ValueError, "binding"):
                analyze_log(sessions, "S1", rows)

    def test_returned_version_cannot_open_session(self):
        data = json.loads((ROOT / "case.json").read_text())
        data["sessions"][0]["protocol"] = "P2"
        with self.assertRaisesRegex(ValueError, "not_admitted"):
            admitted_sessions(ROOT, data)

