"""
Unit tests for lab run service and API routes.
"""
import json
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import lab_run_service  # noqa: E402


class TestLabRunService(unittest.TestCase):
    """Test lab_run_service CRUD against a temp SQLite DB."""

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".sqlite3")
        lab_run_service.set_db_conn_factory(lambda: sqlite3.connect(self.db_path))
        lab_run_service.ensure_table()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_create_and_fetch(self):
        spec = {"objective": "hybrid", "seed": 42}
        run = lab_run_service.create_run("t1", spec)
        self.assertEqual(run["status"], "queued")
        self.assertEqual(run["tenant_id"], "t1")

        fetched = lab_run_service.get_run(run["id"], "t1")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["spec"]["objective"], "hybrid")

    def test_tenant_isolation(self):
        run = lab_run_service.create_run("t1", {"objective": "hrp"})
        self.assertIsNone(lab_run_service.get_run(run["id"], "t2"))
        self.assertIsNotNone(lab_run_service.get_run(run["id"], "t1"))

    def test_status_transitions(self):
        run = lab_run_service.create_run("t1", {"objective": "markowitz"})
        lab_run_service.update_status(run["id"], "running")
        r = lab_run_service.get_run(run["id"], "t1")
        self.assertEqual(r["status"], "running")
        self.assertIsNotNone(r["started_at"])

        result = {"sharpe_ratio": 1.5, "weights": [0.5, 0.5]}
        lab_run_service.update_status(run["id"], "completed", result=result)
        r = lab_run_service.get_run(run["id"], "t1")
        self.assertEqual(r["status"], "completed")
        self.assertIsNotNone(r["finished_at"])
        self.assertAlmostEqual(r["result"]["sharpe_ratio"], 1.5)

    def test_failed_run(self):
        run = lab_run_service.create_run("t1", {"objective": "vqe"})
        lab_run_service.update_status(run["id"], "running")
        lab_run_service.update_status(run["id"], "failed", error="boom")
        r = lab_run_service.get_run(run["id"], "t1")
        self.assertEqual(r["status"], "failed")
        self.assertEqual(r["error"], "boom")

    def test_list_runs(self):
        for i in range(5):
            lab_run_service.create_run("t1", {"objective": "hybrid", "i": i})
        lab_run_service.create_run("t2", {"objective": "hrp"})

        t1_runs = lab_run_service.list_runs("t1")
        self.assertEqual(len(t1_runs), 5)
        t2_runs = lab_run_service.list_runs("t2")
        self.assertEqual(len(t2_runs), 1)

    def test_list_runs_limit(self):
        for i in range(10):
            lab_run_service.create_run("t1", {"objective": "hybrid"})
        runs = lab_run_service.list_runs("t1", limit=3)
        self.assertEqual(len(runs), 3)

    def test_invalid_execution_kind(self):
        with self.assertRaises(ValueError):
            lab_run_service.create_run("t1", {}, execution_kind="invalid")

    def test_invalid_status(self):
        run = lab_run_service.create_run("t1", {"objective": "hybrid"})
        with self.assertRaises(ValueError):
            lab_run_service.update_status(run["id"], "invalid_status")


if __name__ == "__main__":
    unittest.main()
