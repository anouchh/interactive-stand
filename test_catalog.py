import hashlib
import tempfile
import unittest
from pathlib import Path

from catalog import inspect_package, summarize


class CatalogTests(unittest.TestCase):
    def test_package(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "card").write_bytes(b"ok")
            item = ["zone", "card", hashlib.sha256(b"ok").hexdigest()]
            self.assertEqual(inspect_package(root, [item]), ({"zone": "card"}, []))
            for items, error in [
                ([], "empty_catalog"),
                ([item, item], "invalid_zone:zone"),
                ([["zone", "card", "bad"]], "checksum:zone"),
                ([["zone", "absent", "bad"]], "unreadable:zone"),
            ]:
                self.assertEqual(inspect_package(root, items), ({}, [error]))

    def test_session(self):
        index = {"motor": "m", "pump": "p"}
        events = [(0, "motor"), (100, "motor"), (250, "motor"),
                  (300, "ghost"), (200, "pump"), (400, "pump")]
        self.assertEqual(summarize(index, events),
                         ({"motor": 2, "pump": 1},
                          [[2, "repeat"], [4, "unknown"], [5, "time"]]))
        self.assertEqual(summarize(index, []), ({"motor": 0, "pump": 0}, []))


if __name__ == "__main__":
    unittest.main()
