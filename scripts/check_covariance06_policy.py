"""Independent calibration-only policy check, before opening evaluation."""

import argparse
import hashlib
import json
from pathlib import Path

from verify_covariance06_statistics import get, load, positive, weighted_threshold


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--calibration", type=Path, required=True)
    p.add_argument("--policy", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    m, cal = load(a.calibration, "calibration")
    policy = json.loads(a.policy.read_text())
    cfg = m["config"]
    assert len(cal) == 240 and len({r["source_id"] for r in cal}) == 240
    assert (
        policy["calibration_complete"]
        and policy["scientific_fingerprint"] == m["scientific_fingerprint"]
    )
    assert policy["source_ids"] == [r["source_id"] for r in cal]
    assert (
        policy["calibration_manifest_sha256"]
        == hashlib.sha256((a.calibration / "manifest.json").read_bytes()).hexdigest()
    )
    assert (
        policy["analysis_producer_sha256"]
        == hashlib.sha256(Path("scripts/covariance06_statistics.py").read_bytes()).hexdigest()
    )
    for file, h in m["scientific_file_sha256"].items():
        assert hashlib.sha256(Path(file).read_bytes()).hexdigest() == h
    results = {}
    for mode in cfg["methods"]:
        threshold = weighted_threshold(cal, [1] * len(cal), mode, cfg)
        saved = policy["thresholds"][mode]
        assert threshold == saved["threshold"]
        assert saved["always_negative"] == (threshold is None)
        count = sum(
            positive(get(r, n, "gaussian", "complete", mode), threshold)
            for r in cal
            for n in cfg["calibration_noise"]
        )
        assert count == saved["calibration_false_positives"] <= 24
        assert (
            saved["calibration_negative_views"] == 480
            and saved["independent_calibration_sources"] == 240
        )
        results[mode] = {
            "threshold": threshold,
            "false_positives_of_480_dependent_calibration_views": count,
            "always_negative": threshold is None,
        }
    proof = {
        "status": "PASS",
        "independent_calibration_sources": 240,
        "methods": results,
        "policy_sha256": hashlib.sha256(a.policy.read_bytes()).hexdigest(),
        "scientific_fingerprint": m["scientific_fingerprint"],
        "empirical_not_population_fpr_guarantee": True,
        "evaluation_or_truth_used": False,
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof))


if __name__ == "__main__":
    main()
