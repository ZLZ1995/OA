import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from app.core.workflow_baseline import LEGACY, PARALLEL_WORKPAPER_V1, load_baseline


class WorkflowBaselineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "baseline.json"
        self.data = {
            "project_ids": [1, 3, 7], "count": 3,
            "sha256": hashlib.sha256(b"[1,3,7]").hexdigest(),
            "captured_at_utc": "2026-10-29T03:30:24+00:00",
            "source_service_id": "test-service",
        }

    def load(self):
        self.path.write_text(json.dumps(self.data), encoding="utf-8")
        return load_baseline(self.path, expected_service_id="test-service")

    def test_exact_membership_not_high_water_mark(self):
        baseline = self.load()
        for project_id in [1, 3, 7]:
            self.assertEqual(baseline.version_for(project_id), LEGACY)
        for project_id in [2, 4, 8]:
            self.assertEqual(baseline.version_for(project_id), PARALLEL_WORKPAPER_V1)

    def test_rejects_altered_ids(self):
        self.data["project_ids"] = [1, 3, 8]
        with self.assertRaises(ValueError):
            self.load()

    def test_rejects_duplicate_ids(self):
        self.data["project_ids"] = [1, 1, 7]
        with self.assertRaises(ValueError):
            self.load()

    def test_rejects_wrong_environment(self):
        self.data["source_service_id"] = "another-service"
        with self.assertRaises(ValueError):
            self.load()

    def test_rejects_missing_manifest(self):
        with self.assertRaises(FileNotFoundError):
            load_baseline(self.path, expected_service_id="test-service")

    def test_rejects_naive_timestamp(self):
        self.data["captured_at_utc"] = "2026-10-29T03:30:24"
        with self.assertRaises(ValueError):
            self.load()

    def test_rejects_unpersisted_id(self):
        with self.assertRaises(ValueError):
            self.load().version_for(0)
