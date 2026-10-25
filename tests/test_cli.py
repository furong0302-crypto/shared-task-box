from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def test_cli_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            db = str(Path(td) / "cli.db")
            env = os.environ.copy()
            root = Path(__file__).resolve().parents[1]
            env["PYTHONPATH"] = str(root / "src")

            def run(*args):
                cp = subprocess.run(
                    [sys.executable, "-m", "shared_task_box", "--db", db, *args],
                    text=True,
                    capture_output=True,
                    env=env,
                    check=True,
                )
                return json.loads(cp.stdout)

            created = run(
                "create", "--event-id", "cli-create", "--title", "CLI task", "--content", "Do it"
            )
            tid = created["task"]["id"]
            claimed = run(
                "claim", "--event-id", "cli-claim", "--worker", "worker-cli", "--task-id", str(tid)
            )
            self.assertTrue(claimed["claimed"])
            run(
                "progress", str(tid), "--event-id", "cli-progress", "--worker", "worker-cli", "--text", "working"
            )
            run(
                "complete", str(tid), "--event-id", "cli-complete", "--worker", "worker-cli", "--result", "done"
            )
            result = run("result", str(tid))
            self.assertEqual("done", result["status"])
            self.assertEqual("done", result["result"])


if __name__ == "__main__":
    unittest.main()
