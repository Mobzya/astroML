"""Freeze the predeclared global empirical calibration policy; no evaluation access."""

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from run_covariance06 import fingerprint


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    p.add_argument("--verifier", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists(), "Never overwrite a frozen policy"
    m = json.loads((a.run / "manifest.json").read_text())
    v = json.loads(a.verifier.read_text())
    cfg = m["config"]
    assert (
        m["phase"] == "calibration" and m["status"] == "COMPLETE" and m["completed_sources"] == 240
    )
    assert v["status"] == "PASS" and v["phase"] == "calibration" and v["independent_sources"] == 240
    assert m["scientific_fingerprint"] == v["scientific_fingerprint"] == fingerprint()[0]
    assert v["selected_fit_rows"] == 240 * 4 * 5 * 3
    records = []
    for name, h in sorted(m["sha256"].items()):
        assert sha(a.run / name) == h
        if name.startswith("source-"):
            records.append(json.loads((a.run / name).read_text()))
    scores = {mode: [] for mode in cfg["methods"]}
    rows = []
    for record in records:
        assert record["split"] == "calibration"
        negatives = [
            v for v in record["views"] if v["family"] == "gaussian" and v["condition"] == "complete"
        ]
        assert len(negatives) == 2
        for row in negatives:
            for mode, method in row["results"].items():
                score = (
                    method["score"] if method["valid"] and method["score"] is not None else -np.inf
                )
                scores[mode].append(score)
                rows.append(
                    [record["source_id"], row["key"], mode, method["valid"], method["score"]]
                )
    policies = {}
    for mode, values in scores.items():
        assert len(values) == 480
        ordered = np.sort(values)
        index = int(np.ceil((1 - cfg["target_calibration_fpr"]) * len(values))) - 1
        boundary = ordered[index]
        threshold = float(np.nextafter(boundary, np.inf)) if np.isfinite(boundary) else None
        if threshold is not None and not np.isfinite(threshold):
            threshold = None
        policies[mode] = {
            "threshold": threshold,
            "always_negative": threshold is None,
            "calibration_negative_views": len(values),
            "independent_calibration_sources": 240,
            "ascending_order_index": index,
            "strict_above_order_statistic": True,
            "calibration_false_positives": 0
            if threshold is None
            else int(np.sum(np.array(values) >= threshold)),
        }
    output = {
        "experiment_id": cfg["experiment_id"],
        "calibration_complete": True,
        "created_utc": datetime.now(UTC).isoformat(),
        "scientific_fingerprint": m["scientific_fingerprint"],
        "source_ids": [r["source_id"] for r in records],
        "calibration_manifest_sha256": sha(a.run / "manifest.json"),
        "calibration_verifier_sha256": sha(a.verifier),
        "thresholds": policies,
        "calibration_score_rows_sha256": hashlib.sha256(
            json.dumps(rows, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest(),
        "freeze_code_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "freeze_script_sha256": sha(__file__),
        "target_calibration_fpr": cfg["target_calibration_fpr"],
        "rule": "pool white/Matérn complete Gaussian; invalid=-inf; nextafter ascending ceil(.95*n)-1; no-positive if boundary nonfinite",
        "not_a_population_or_subgroup_fpr_guarantee": True,
        "evaluation_generated_by_this_script": False,
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": "FROZEN_LOCAL_NOT_YET_PUSHED", "thresholds": policies}))


if __name__ == "__main__":
    main()
