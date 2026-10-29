"""Read-only verification of an externally stored deployment manifest."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.workflow_baseline import load_baseline

parser = argparse.ArgumentParser()
parser.add_argument("manifest")
parser.add_argument("--service-id", required=True)
args = parser.parse_args()
baseline = load_baseline(args.manifest, expected_service_id=args.service_id)
print(f"verified count={len(baseline.project_ids)} captured_at={baseline.captured_at.isoformat()} sha256={baseline.digest}")
