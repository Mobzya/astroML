"""Read-only Git-object/calibration/policy/evaluation continuity audit. No event rows."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def git_bytes(*args):
    return subprocess.check_output(["git", *args])


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--calibration", type=Path, required=True)
    p.add_argument("--evaluation", type=Path, required=True)
    p.add_argument("--policy", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    cal = json.loads((a.calibration / "manifest.json").read_text())
    evaluation = json.loads((a.evaluation / "manifest.json").read_text())
    policy = json.loads(a.policy.read_text())
    freeze = "44ec73ee8aa2804eb5a7628fd99fd67a2e0326aa"
    assert (
        cal["status"] == "COMPLETE"
        and cal["phase"] == "calibration"
        and evaluation["phase"] == "evaluation"
    )
    assert cal["scientific_file_sha256"] == evaluation["scientific_file_sha256"]
    hashes = cal["scientific_file_sha256"]
    fp = sha(json.dumps(hashes, sort_keys=True).encode())
    assert (
        fp
        == cal["scientific_fingerprint"]
        == evaluation["scientific_fingerprint"]
        == policy["scientific_fingerprint"]
    )
    for file, h in hashes.items():
        assert sha(git_bytes("show", cal["code_sha"] + ":" + file)) == h
        assert sha(git_bytes("show", freeze + ":" + file)) == h
        assert sha(git_bytes("show", evaluation["code_sha"] + ":" + file)) == h
        assert sha(Path(file).read_bytes()) == h
    assert (
        sha(git_bytes("show", freeze + ":" + str(a.policy)))
        == sha(a.policy.read_bytes())
        == evaluation["policy_sha256"]
    )
    assert policy["calibration_manifest_sha256"] == sha(
        (a.calibration / "manifest.json").read_bytes()
    )
    assert (
        policy["analysis_producer_sha256"]
        == sha(Path("scripts/covariance06_statistics.py").read_bytes())
        == sha(git_bytes("show", freeze + ":scripts/covariance06_statistics.py"))
    )
    assert cal["versions"] == evaluation["versions"] and cal["python"] == evaluation["python"]
    assert not cal["git_dirty"] and not evaluation["git_dirty"]
    assert (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", freeze, evaluation["code_sha"]], check=False
        ).returncode
        == 0
    )
    assert (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", freeze, "origin/main"], check=False
        ).returncode
        == 0
    )
    ci = {r["source_id"] for r in cal["source_manifest"]}
    ei = {r["source_id"] for r in evaluation["source_manifest"]}
    assert len(ci) == 240 and len(ei) == 360 and ci.isdisjoint(ei)
    assert ci == set(policy["source_ids"])
    result = {
        "status": "PASS",
        "scope": "Git objects/source assignment/frozen policy/version continuity only; no fit/metric verification claimed",
        "scientific_files_checked_across_calibration_freeze_evaluation_and_current": len(hashes),
        "scientific_fingerprint": fp,
        "calibration_initial_code_sha": cal["code_sha"],
        "policy_freeze_commit": freeze,
        "evaluation_initial_code_sha": evaluation["code_sha"],
        "policy_sha256": evaluation["policy_sha256"],
        "calibration_sources": 240,
        "assigned_evaluation_sources": 360,
        "evaluation_completed_at_audit": evaluation["completed_sources"],
        "evaluation_status_at_audit": evaluation["status"],
        "python": cal["python"],
        "versions": cal["versions"],
        "new_run_remote_head_and_policy_check_enforced_by_frozen_runner": True,
        "push_before_evaluation_ordering": "Observed in same-chat tool execution: freeze push succeeded, fetch HEAD/origin matched44ec73e, then new-run preconditions passed before generation. Not inferred from commit dates alone.",
        "event_level_data_or_truth_read": False,
        "classification_metrics_computed": False,
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
