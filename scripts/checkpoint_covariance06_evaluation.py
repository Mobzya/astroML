"""Publishable local checkpoint metadata/shards/restore; no fitting or Git push."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    p.add_argument("--owner", required=True)
    a = p.parse_args()
    lease = json.loads(Path("research/session_state.json").read_text())["active_session"]
    assert (
        lease
        and lease["owner_id"] == a.owner
        and lease["task_id"] == "W1-COV06-EVAL"
        and lease["fitting_pid"] is None
    )
    ledger = json.loads(Path("research/cov06/runner_evaluation_ledger.json").read_text())
    assert not ledger["invocation_in_progress"]
    m = json.loads((a.run / "manifest.json").read_text())
    assert m["phase"] == "evaluation" and m["status"] in ["PARTIAL_CHECKPOINT", "COMPLETE"]
    n = m["completed_sources"]
    assert 0 < n <= 360
    dest = Path(f"reports/covariance06/evaluation/checkpoint-{n:04d}")
    assert not dest.exists(), "Preserve immutable existing checkpoint"
    subprocess.run(
        [
            sys.executable,
            "scripts/archive_covariance06.py",
            str(a.run),
            "--label",
            "cov06-evaluation-v1",
            "--destination",
            str(dest),
            "--shard-root",
            "reports/covariance06/evaluation-shards",
        ],
        check=True,
    )
    proof = Path(f"reports/checks/cov06_evaluation_restore_{n:04d}.json")
    with proof.open("w") as stream:
        subprocess.run(
            [
                sys.executable,
                "scripts/restore_research_shards.py",
                "--index",
                str(dest / "artifacts.json"),
                "--output",
                f"artifacts/cov06-evaluation-restored-{n:04d}",
                "--allow-partial",
            ],
            check=True,
            stdout=stream,
        )
    restored = json.loads(proof.read_text())
    assert restored["data_files"] == 2 * n and restored["independent_sources"] == n
    index = dest / "artifacts.json"
    root_path = Path("reports/covariance06/artifacts.json")
    root = json.loads(root_path.read_text())
    root.update(
        evaluation_index_path=str(index),
        evaluation_index_sha256=sha(index),
        evaluation_archived_sources=n,
        evaluation_status=m["status"],
    )
    root_path.write_text(json.dumps(root, indent=2) + "\n")
    snapshot = {
        "status": m["status"],
        "expected_independent_sources": 360,
        "completed_independent_sources": n,
        "observed_curves_completed": n * 18,
        "saved_mean_fit_records": n * 18 * 5 * 3,
        "full_evaluation_complete": n == 360 and m["status"] == "COMPLETE",
        "latest_checkpoint_index": str(index),
        "latest_checkpoint_index_sha256": sha(index),
        "raw_manifest_path": str(dest / "run_manifest.json"),
        "raw_manifest_sha256": sha(dest / "run_manifest.json"),
        "restore_proof": str(proof),
        "scientific_fingerprint": m["scientific_fingerprint"],
        "policy_sha256": m["policy_sha256"],
        "initial_clean_code_sha": m["code_sha"],
        "cumulative_fit_wall_seconds": m["cumulative_fit_wall_seconds"],
        "versions": m["versions"],
        "python": m["python"],
        "classification_metrics_computed": False,
        "numerical_verification": "PENDING; numerical task not marked DONE by storage helper",
    }
    Path("reports/covariance06/evaluation_manifest.json").write_text(
        json.dumps(snapshot, indent=2) + "\n"
    )
    print(json.dumps(snapshot))


if __name__ == "__main__":
    main()
