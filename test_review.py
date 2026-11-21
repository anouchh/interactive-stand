import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEADER = "session\tversion\ttime_ms\tzone\n"


class ReviewTests(unittest.TestCase):
    def run_both(self, rows):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "events.tsv"
            log.write_text(HEADER + rows, encoding="utf-8")
            commands = [
                [sys.executable, "catalog.py", "--log", str(log)],
                ["java", "java/Kiosk.java", "example/accepted.tsv", str(log), "S1"],
            ]
            return [subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
                    for cmd in commands]

    def test_time_format(self):
        rows = "".join(f"S1\tv1\t{value}\tmotor\n"
                       for value in ["1_000", "+1", " 4", "９", "", "000", "250"])
        python, java = self.run_both(rows)
        for result in (python, java):
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.count("time"), 5)
        self.assertIn("'motor': 2", python.stdout)
        self.assertIn("motor=2", java.stdout)

    def test_missing_column(self):
        for result in self.run_both("S1\tv1\t0\tmotor\nS1\tv1\t250\n"):
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("line 3: expected 4 columns, got 3", result.stderr)
