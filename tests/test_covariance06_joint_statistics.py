"""Decision-table fixtures only: no observations, physical sources or fitting."""

import importlib
import json
from pathlib import Path


def test_producer_agrees_with_independent_weighted_counts(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    producer = importlib.import_module("covariance06_statistics")
    reference = importlib.import_module("verify_covariance06_statistics")
    cfg = json.loads(Path("configs/experiment_06.json").read_text())
    cfg["bootstrap_replicates"] = 3

    def record(i, phase, seed):
        views = []
        for noise in cfg[phase + "_noise"]:
            for family in ["pspl", "gaussian"]:
                for condition in cfg[phase + "_conditions"]:
                    methods = {}
                    for j, mode in enumerate(cfg["methods"]):
                        valid = (i + j) % 17 != 0
                        methods[mode] = {
                            "score": float((i * 7 + j) % 23 + 2 * (family == "pspl"))
                            if valid
                            else None,
                            "valid": valid,
                            "fits": {"constant": {"nll": 1.0, "success": valid}},
                            "runtime_seconds": 0.01,
                        }
                    views.append(
                        {
                            "noise": noise,
                            "family": family,
                            "condition": condition,
                            "results": methods,
                        }
                    )
        return {"source_id": f"decision-fixture-{phase}-{i}", "seed": seed, "views": views}

    cal = [record(i, "calibration", cfg["seeds"][i // 80]) for i in range(240)]
    evaluation = [record(i, "evaluation", cfg["seeds"][i // 120]) for i in range(360)]
    policy = {"source_ids": [r["source_id"] for r in cal], "thresholds": {}}
    for mode in cfg["methods"]:
        policy["thresholds"][mode] = {
            "threshold": producer.threshold(
                [
                    producer.accepted_score(
                        producer.row(r, n, "gaussian", "complete")["results"][mode]
                    )
                    for r in cal
                    for n in cfg["calibration_noise"]
                ]
            )
        }
    summary = producer.analyze(cal, evaluation, policy, cfg)
    checked = reference.verify(cal, evaluation, policy, summary, cfg)
    assert (
        checked["status"] == "PASS"
        and checked["tables_checked"] == 180
        and checked["weighted_joint_bootstrap_replicates_checked"] == 3
    )
