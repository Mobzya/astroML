"""Audit code/policy continuity of the completed COV05; no data-driven fitting."""

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
from datetime import datetime
from pathlib import Path

from run_covariance05 import fingerprint


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    args = p.parse_args()
    manifest = json.loads((args.run / "run_manifest.json").read_text())
    assert manifest["status"] == "COMPLETE"
    policy_path = Path("reports/covariance05/frozen_policy.json")
    policy = json.loads(policy_path.read_text())
    commit = manifest["policy_commit"]
    historical = subprocess.check_output(["git", "show", f"{commit}:{policy_path}"])
    assert historical == policy_path.read_bytes()
    assert hashlib.sha256(historical).hexdigest() == manifest["policy_sha256"]
    core = [
        "src",
        "scripts/run_covariance05.py",
        "configs/experiment_05.json",
        "research/experiment_05_protocol.md",
    ]
    assert not git("diff", commit, "HEAD", "--", *core)
    assert not git("diff", "HEAD", "--", *core)
    assert not git("status", "--porcelain", "--", *core)
    current = fingerprint("configs/experiment_05.json")
    assert current == policy["scientific_fingerprint"] == manifest["scientific_fingerprint"]
    versions = {p: importlib.metadata.version(p) for p in manifest["versions"]}
    assert versions == manifest["versions"]
    commit_time = git("show", "-s", "--format=%cI", commit)
    assert datetime.fromisoformat(commit_time) <= datetime.fromisoformat(manifest["created_utc"])
    output = {
        "status": "PASS",
        "policy_commit": commit,
        "policy_committed_at": commit_time,
        "evaluation_created_utc": manifest["created_utc"],
        "policy_sha256": manifest["policy_sha256"],
        "policy_bytes_unmodified": True,
        "core_diff_from_freeze_empty": True,
        "core_working_tree_clean": True,
        "scientific_fingerprint": current,
        "current_audit_commit": git("rev-parse", "HEAD"),
        "evaluation_original_code_sha": manifest["code_sha"],
        "versions_match_manifest": versions,
        "no_detector_fit_performed": True,
    }
    Path("reports/checks/cov05_freeze_audit.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
