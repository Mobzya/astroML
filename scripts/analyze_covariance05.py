"""Freeze covariance calibration or analyze independently generated fixed-policy data."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from analyze_reconstruction02 import load_records

from microlens.evaluation import calibration_threshold, decision_metrics


def values(records, mode, noise, condition, family):
    p, n, pv, nv = [], [], [], []
    for record in records:
        selected = {
            v["family"]: v["results"][mode]
            for v in record["views"]
            if v["noise"] == noise and v["condition"] == condition
        }
        for name, scores, valid in [("pspl", p, pv), (family, n, nv)]:
            scores.append(
                selected[name]["score"] if selected[name]["score"] is not None else -np.inf
            )
            valid.append(selected[name]["valid"])
    return list(map(np.asarray, [p, n, pv, nv]))


def bootstrap_primary(records, policy, config):
    cg = [
        [i for i, r in enumerate(policy["source_seeds"]) if r == seed] for seed in config["seeds"]
    ]
    eg = [[i for i, r in enumerate(records) if r["seed"] == seed] for seed in config["seeds"]]
    arrays = {
        m: values(
            records,
            m,
            config["primary_noise"],
            config["primary_condition"],
            config["primary_negative_family"],
        )
        for m in ["diagonal", "estimated"]
    }
    cal = {
        m: np.array(
            [
                [v if v is not None else -np.inf for v in pair]
                for pair in policy["negative_calibration_scores"][m]
            ]
        )
        for m in arrays
    }
    rng = np.random.default_rng(config["bootstrap_seed"])
    draws = []
    for _ in range(config["bootstrap_replicates"]):
        ci = np.concatenate([rng.choice(g, len(g), replace=True) for g in cg])
        ei = np.concatenate([rng.choice(g, len(g), replace=True) for g in eg])
        metrics = {}
        for mode, mode_arrays in arrays.items():
            threshold = calibration_threshold(
                cal[mode][ci].ravel(), config["target_calibration_fpr"]
            )
            p, n, pv, nv = [a[ei] for a in mode_arrays]
            tp = int(np.count_nonzero(pv & (p >= threshold))) if threshold is not None else 0
            fp = int(np.count_nonzero(nv & (n >= threshold))) if threshold is not None else 0
            metrics[mode] = (fp / len(n), tp / len(p))
        draws.append(
            [
                metrics["estimated"][0] - metrics["diagonal"][0],
                metrics["estimated"][1] - metrics["diagonal"][1],
            ]
        )
    return np.array(draws)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Preserve existing summary")
    config = json.loads(Path("configs/experiment_05.json").read_text())
    manifest, records = load_records(args.run)
    result = {
        "phase": manifest["phase"],
        "independent_sources": len(records),
        "scientific_fingerprint": manifest["scientific_fingerprint"],
        "source_ids": [r["source_id"] for r in records],
        "source_seeds": [r["seed"] for r in records],
        "runtime_seconds": manifest["runtime_seconds_accumulated"],
        "maximum_worker_rss_kib": max(r["worker_max_rss_kib"] for r in records),
    }
    if manifest["phase"] == "calibration":
        result.update(thresholds={}, negative_calibration_scores={}, calibration_fp={})
        for mode in config["methods"]:
            matrix = []
            for record in records:
                row = []
                for noise in config["calibration_noise"]:
                    selected = next(
                        v["results"][mode]
                        for v in record["views"]
                        if v["family"] == "gaussian" and v["noise"] == noise
                    )
                    row.append(selected["score"] if selected["valid"] else None)
                matrix.append(row)
            numeric = np.array([[v if v is not None else -np.inf for v in r] for r in matrix])
            threshold = calibration_threshold(numeric.ravel(), config["target_calibration_fpr"])
            result["thresholds"][mode] = threshold
            result["negative_calibration_scores"][mode] = matrix
            result["calibration_fp"][mode] = (
                int(np.count_nonzero(numeric >= threshold)) if threshold is not None else 0
            )
        result["negative_views_per_method"] = len(records) * len(config["calibration_noise"])
    else:
        if not args.policy:
            raise SystemExit("Frozen policy required")
        policy = json.loads(args.policy.read_text())
        assert policy["scientific_fingerprint"] == manifest["scientific_fingerprint"]
        assert set(result["source_ids"]).isdisjoint(policy["source_ids"])
        assert hashlib.sha256(args.policy.read_bytes()).hexdigest() == manifest["policy_sha256"]
        result.update(scenarios={}, per_seed={})
        for noise in config["evaluation_noise"]:
            for condition in config["evaluation_conditions"]:
                for family in ["gaussian", "double_bump"]:
                    key = f"{noise}/{condition}/{family}"
                    result["scenarios"][key] = {
                        mode: decision_metrics(
                            *values(records, mode, noise, condition, family),
                            policy["thresholds"][mode],
                        )
                        for mode in config["methods"]
                    }
        for seed in config["seeds"]:
            selected = [r for r in records if r["seed"] == seed]
            result["per_seed"][str(seed)] = {
                key: {
                    mode: decision_metrics(
                        *values(selected, mode, *key.split("/")), policy["thresholds"][mode]
                    )
                    for mode in config["methods"]
                }
                for key in result["scenarios"]
            }
        key = "/".join(
            [
                config["primary_noise"],
                config["primary_condition"],
                config["primary_negative_family"],
            ]
        )
        primary = result["scenarios"][key]
        draws = bootstrap_primary(records, policy, config)
        ci = np.quantile(draws, [0.025, 0.975], axis=0)
        supported = bool(
            ci[1, 0] < 0
            and ci[0, 1] >= -config["recall_noninferiority_margin"]
            and primary["estimated"]["coverage"] >= config["minimum_coverage"]
        )
        result["primary"] = {
            "scenario": key,
            "comparison": "estimated_minus_diagonal",
            "delta_fpr": primary["estimated"]["fpr_all"] - primary["diagonal"]["fpr_all"],
            "delta_recall": primary["estimated"]["recall_all"] - primary["diagonal"]["recall_all"],
            "delta_fpr_ci95_joint_bootstrap": ci[:, 0].tolist(),
            "delta_recall_ci95_joint_bootstrap": ci[:, 1].tolist(),
            "full_success_criterion_supported": supported,
            "joint_calibration_evaluation_bootstrap": True,
            "bootstrap_draws_delta_fpr_recall": draws.tolist(),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {k: result[k] for k in ["phase", "independent_sources", "runtime_seconds"]}, indent=2
        )
    )
    if "thresholds" in result:
        print(
            json.dumps(
                {"thresholds": result["thresholds"], "calibration_fp": result["calibration_fp"]}
            )
        )
    else:
        print(
            json.dumps(
                {k: v for k, v in result["primary"].items() if not k.startswith("bootstrap_draws")}
            )
        )


if __name__ == "__main__":
    main()
