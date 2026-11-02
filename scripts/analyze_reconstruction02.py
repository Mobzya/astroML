"""Read saved R2 fits; freeze calibration or analyze independent evaluation."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from microlens.evaluation import auc_from_pairs, calibration_threshold, decision_metrics


def load_records(run):
    manifest = json.loads((run / "run_manifest.json").read_text())
    if manifest["status"] != "COMPLETE":
        raise ValueError("Cannot report an incomplete run as complete")
    for name, checksum in manifest["sha256"].items():
        if hashlib.sha256((run / name).read_bytes()).hexdigest() != checksum:
            raise ValueError(f"Checksum mismatch {name}")
    records = [r for f in sorted(run.glob("batch-*.json")) for r in json.loads(f.read_text())]
    if len(records) != manifest["expected_pairs"] or len({r["source_id"] for r in records}) != len(
        records
    ):
        raise ValueError("Pair counts or uniqueness failed")
    return manifest, records


def score(row):
    return row["score"] if row["score"] is not None else -np.inf


def arrays(records, condition):
    p, n, pv, nv = [], [], [], []
    for record in records:
        rows = {v["family"]: v for v in record["views"] if v["condition"] == condition}
        p.append(score(rows["pspl"]))
        n.append(score(rows["gaussian"]))
        pv.append(rows["pspl"]["valid"])
        nv.append(rows["gaussian"]["valid"])
    return list(map(np.asarray, [p, n, pv, nv]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--config", default="configs/reconstruction_02.json")
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output exists; preserve it.")
    config = json.loads(Path(args.config).read_text())
    manifest, records = load_records(args.run)
    result = {
        "phase": manifest["phase"],
        "pairs": len(records),
        "scientific_fingerprint": manifest["scientific_fingerprint"],
        "source_ids": [r["source_id"] for r in records],
        "runtime_seconds": manifest["runtime_seconds_accumulated"],
        "maximum_worker_rss_kib": max(r["worker_max_rss_kib"] for r in records),
        "invalid_views": {
            c: int(sum(not v["valid"] for r in records for v in r["views"] if v["condition"] == c))
            for c in config["conditions"]
        },
    }
    if manifest["phase"] == "calibration":
        _, negatives, _, valid = arrays(records, "complete")
        threshold = calibration_threshold(
            np.where(valid, negatives, -np.inf), config["target_calibration_fpr"]
        )
        result.update(
            threshold=threshold,
            calibration_condition="complete",
            target_fpr=config["target_calibration_fpr"],
            n_negative=len(negatives),
            calibration_fp=int(np.count_nonzero(valid & (negatives >= threshold)))
            if threshold is not None
            else 0,
            calibration_source_manifest_sha256=hashlib.sha256(
                json.dumps(result["source_ids"]).encode()
            ).hexdigest(),
        )
    elif manifest["phase"] == "evaluation":
        if not args.policy:
            raise SystemExit("Need frozen policy")
        policy = json.loads(args.policy.read_text())
        if policy["scientific_fingerprint"] != manifest["scientific_fingerprint"]:
            raise ValueError("Policy/scientific fingerprint mismatch")
        if set(result["source_ids"]) & set(policy["source_ids"]):
            raise ValueError("Calibration/evaluation source overlap")
        result["policy_sha256"] = hashlib.sha256(args.policy.read_bytes()).hexdigest()
        if result["policy_sha256"] != manifest["policy_sha256"]:
            raise ValueError("Wrong policy for evaluation")
        result["conditions"] = {
            c: decision_metrics(*arrays(records, c), policy["threshold"])
            for c in config["conditions"]
        }
        seed_groups = [
            [i for i, r in enumerate(records) if r["seed"] == seed] for seed in config["seeds"]
        ]
        rng = np.random.default_rng(config["bootstrap_seed"])
        draws = {c: [] for c in config["conditions"]}
        contrasts = []
        all_arrays = {c: arrays(records, c) for c in config["conditions"]}
        for _ in range(config["bootstrap_replicates"]):
            chosen = np.concatenate(
                [rng.choice(group, len(group), replace=True) for group in seed_groups]
            )
            values = {}
            for c in config["conditions"]:
                p, n, _, _ = all_arrays[c]
                values[c] = auc_from_pairs(p[chosen], n[chosen])
                draws[c].append(values[c])
            contrasts.append(values["peak40"] - values["random40"])
        for c in config["conditions"]:
            result["conditions"][c]["auc_ci95_pair_bootstrap"] = np.quantile(
                draws[c], [0.025, 0.975]
            ).tolist()
        result["primary_contrast"] = {
            "name": "auc_peak40_minus_random40",
            "value": result["conditions"]["peak40"]["auc"]
            - result["conditions"]["random40"]["auc"],
            "ci95_pair_bootstrap": np.quantile(contrasts, [0.025, 0.975]).tolist(),
            "replicates": config["bootstrap_replicates"],
            "stratified_by_seed": True,
        }
        result["per_seed"] = {
            str(seed): {
                c: decision_metrics(
                    *arrays([r for r in records if r["seed"] == seed], c), policy["threshold"]
                )
                for c in config["conditions"]
            }
            for seed in config["seeds"]
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "source_ids"}, indent=2))


if __name__ == "__main__":
    main()
