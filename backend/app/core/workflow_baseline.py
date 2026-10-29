"""Validate the immutable production project baseline before workflow activation.

No inference from project stage, creation date, or maximum ID is permitted.
The manifest is deployment data and must not be committed to the repository.
"""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path

LEGACY = "LEGACY"
PARALLEL_WORKPAPER_V1 = "PARALLEL_WORKPAPER_V1"


@dataclass(frozen=True)
class WorkflowBaseline:
    project_ids: frozenset[int]
    captured_at: datetime
    source_service_id: str
    digest: str

    def version_for(self, project_id: int) -> str:
        if type(project_id) is not int or project_id < 1:
            raise ValueError("A persisted positive project ID is required")
        return LEGACY if project_id in self.project_ids else PARALLEL_WORKPAPER_V1


def load_baseline(path: str | Path, *, expected_service_id: str) -> WorkflowBaseline:
    """Fail closed on missing, altered, or wrong-environment manifests."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    ids = data.get("project_ids")
    if not isinstance(ids, list) or any(type(i) is not int or i < 1 for i in ids):
        raise ValueError("Invalid project ID list")
    if ids != sorted(set(ids)) or data.get("count") != len(ids):
        raise ValueError("Project IDs must be unique, sorted, and match count")
    digest = hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest()
    if digest != data.get("sha256"):
        raise ValueError("Baseline digest mismatch")
    if not expected_service_id or data.get("source_service_id") != expected_service_id:
        raise ValueError("Baseline belongs to another environment")
    captured_at = datetime.fromisoformat(data["captured_at_utc"])
    if captured_at.tzinfo is None:
        raise ValueError("Baseline timestamp must include timezone")
    return WorkflowBaseline(frozenset(ids), captured_at, expected_service_id, digest)
