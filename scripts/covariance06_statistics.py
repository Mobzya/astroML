"""Pre-evaluation COV06 statistics implementation, fixed protocol; no fitting.

All views of a source stay together; joint bootstrap redraws calibration and
independent evaluation by seed. This producer needs an independent verifier.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import beta, rankdata


def threshold(values, alpha=0.05):
    values = np.sort(np.asarray(values, float))
    k = int(np.ceil((1 - alpha) * len(values))) - 1
    if not np.isfinite(values[k]):
        return None
    value = float(np.nextafter(values[k], np.inf))
    return value if np.isfinite(value) else None


def cp(k, n):
    if n == 0:
        return [None, None]
    return [
        0.0 if k == 0 else float(beta.ppf(0.025, k, n - k + 1)),
        1.0 if k == n else float(beta.ppf(0.975, k + 1, n - k)),
    ]


def ratio(a, b):
    return float(a / b) if b else None


def method_score(method):
    return -np.inf if method["score"] is None else method["score"]


def accepted_score(method):
    return method_score(method) if method["valid"] else -np.inf


def decisions(methods, limit):
    if limit is None:
        return np.zeros(len(methods), bool)
    return np.array(
        [m["valid"] and m["score"] is not None and m["score"] >= limit for m in methods]
    )


def ranking(positive, negative):
    # Raw score diagnostics retain finite fallback values; unavailable=-infinity.
    p, n = np.asarray(positive), np.asarray(negative)
    scores = np.r_[p, n]
    labels = np.r_[np.ones(len(p), int), np.zeros(len(n), int)]
    ranks = rankdata(scores, method="average")
    auc = (ranks[: len(p)].sum() - len(p) * (len(p) + 1) / 2) / (len(p) * len(n))
    order = np.argsort(-scores, kind="stable")
    scores, labels = scores[order], labels[order]
    ends = np.r_[np.flatnonzero(scores[:-1] != scores[1:]) + 1, len(scores)]
    cumulative = np.cumsum(labels)
    prev = 0.0
    ap = 0.0
    pr = []
    for end in ends:
        recall = float(cumulative[end - 1] / len(p))
        precision = float(cumulative[end - 1] / end)
        ap += precision * (recall - prev)
        prev = recall
        pr.append(
            {
                "threshold": float(scores[end - 1]) if np.isfinite(scores[end - 1]) else None,
                "unavailable_score_sentinel": not bool(np.isfinite(scores[end - 1])),
                "precision": precision,
                "recall": recall,
            }
        )
    return {
        "raw_auc": float(auc),
        "empirical_average_precision": float(ap),
        "precision_recall_groups": pr,
        "synthetic_prevalence": 0.5,
        "score_is_probability": False,
    }


def cell_metrics(pos, neg, limit):
    tp = decisions(pos, limit)
    fp = decisions(neg, limit)
    vp = np.array([m["valid"] for m in pos])
    vn = np.array([m["valid"] for m in neg])
    ntp, nfp = int(tp.sum()), int(fp.sum())
    output = {
        "positive_sources": len(pos),
        "negative_sources": len(neg),
        "true_positives": ntp,
        "false_positives": nfp,
        "recall_all": ntp / len(pos),
        "fpr_all": nfp / len(neg),
        "recall_cp95": cp(ntp, len(pos)),
        "fpr_cp95": cp(nfp, len(neg)),
        "accepted_positive": int(vp.sum()),
        "accepted_negative": int(vn.sum()),
        "coverage": float((vp.sum() + vn.sum()) / (len(pos) + len(neg))),
        "rejected_positive": int((~vp).sum()),
        "rejected_negative": int((~vn).sum()),
        "fpr_accepted": ratio(nfp, vn.sum()),
        "recall_accepted": ratio(ntp, vp.sum()),
        "selective_risk": ratio(nfp + int((vp & ~tp).sum()), vp.sum() + vn.sum()),
        "balanced_false_discovery_fraction": ratio(nfp, ntp + nfp),
        "unavailable_selected_means": sum(
            f["nll"] is None for m in pos + neg for f in m["fits"].values()
        ),
        "nonconverged_selected_means": sum(
            not f["success"] for m in pos + neg for f in m["fits"].values()
        ),
        "incremental_method_elapsed_sum_seconds": sum(m["runtime_seconds"] for m in pos + neg),
    }
    output.update(ranking([method_score(m) for m in pos], [method_score(m) for m in neg]))
    return output


def stratum_draw(rng, records, seeds):
    return np.concatenate(
        [
            rng.choice(
                [i for i, r in enumerate(records) if r["seed"] == seed],
                sum(r["seed"] == seed for r in records),
                replace=True,
            )
            for seed in seeds
        ]
    )


def row(record, noise, family, condition):
    return next(
        v
        for v in record["views"]
        if (v["noise"], v["family"], v["condition"]) == (noise, family, condition)
    )


def analyze(cal, evaluation, policy, cfg):
    assert len(cal) == 240 and len(evaluation) == 360
    assert {r["source_id"] for r in cal}.isdisjoint(r["source_id"] for r in evaluation)
    tables = []
    for noise in cfg["evaluation_noise"]:
        for condition in cfg["evaluation_conditions"]:
            for mode in cfg["methods"]:
                for seed in [None] + cfg["seeds"]:
                    group = [r for r in evaluation if seed is None or r["seed"] == seed]
                    pos = [row(r, noise, "pspl", condition)["results"][mode] for r in group]
                    neg = [row(r, noise, "gaussian", condition)["results"][mode] for r in group]
                    metrics = cell_metrics(pos, neg, policy["thresholds"][mode]["threshold"])
                    tables.append(
                        {
                            "noise": noise,
                            "condition": condition,
                            "method": mode,
                            "seed": seed,
                            **metrics,
                        }
                    )
    rng = np.random.default_rng(cfg["bootstrap_seed"])
    draws = []
    modes = cfg["primary_methods"]
    noise = cfg["primary_noise"]
    condition = cfg["primary_condition"]
    calibration = {
        mode: np.array(
            [
                [
                    accepted_score(row(r, n, "gaussian", "complete")["results"][mode])
                    for n in cfg["calibration_noise"]
                ]
                for r in cal
            ]
        )
        for mode in modes
    }
    primary = {
        mode: {
            f: [row(r, noise, f, condition)["results"][mode] for r in evaluation]
            for f in ["pspl", "gaussian"]
        }
        for mode in modes
    }
    for rep in range(cfg["bootstrap_replicates"]):
        ci = stratum_draw(rng, cal, cfg["seeds"])
        ei = stratum_draw(rng, evaluation, cfg["seeds"])
        rates = {}
        limits = {}
        for mode in modes:
            limits[mode] = threshold(calibration[mode][ci].ravel(), cfg["target_calibration_fpr"])
            rates[mode] = {
                f: float(decisions(primary[mode][f], limits[mode])[ei].mean())
                for f in ["pspl", "gaussian"]
            }
        a, b = modes
        draws.append(
            {
                "replicate": rep,
                "delta_fpr": rates[a]["gaussian"] - rates[b]["gaussian"],
                "delta_recall": rates[a]["pspl"] - rates[b]["pspl"],
                "bootstrap_thresholds": limits,
            }
        )
    intervals = {
        key: np.quantile([d[key] for d in draws], [0.025, 0.975]).tolist()
        for key in ["delta_fpr", "delta_recall"]
    }
    primary_rows = {
        m: next(
            r
            for r in tables
            if r["noise"] == noise
            and r["condition"] == condition
            and r["method"] == m
            and r["seed"] is None
        )
        for m in modes
    }
    a, b = modes
    observed = {
        "delta_fpr": primary_rows[a]["fpr_all"] - primary_rows[b]["fpr_all"],
        "delta_recall": primary_rows[a]["recall_all"] - primary_rows[b]["recall_all"],
        "estimated_coverage": primary_rows[a]["coverage"],
    }
    supported = (
        intervals["delta_fpr"][1] < 0
        and intervals["delta_recall"][0] >= -cfg["recall_noninferiority_margin"]
        and observed["estimated_coverage"] >= cfg["minimum_coverage"]
    )
    return {
        "primary": {
            "noise": noise,
            "condition": condition,
            "comparison": modes,
            "observed": observed,
            "joint_source_bootstrap_ci95": intervals,
            "frozen_composite_criterion_supported": bool(supported),
            "replicates": cfg["bootstrap_replicates"],
            "bootstrap_seed": cfg["bootstrap_seed"],
        },
        "bootstrap_draws": draws,
        "tables": tables,
        "independent_calibration_sources": 240,
        "independent_evaluation_sources": 360,
        "synthetic_prevalence": 0.5,
        "secondary_intervals_pointwise_descriptive": True,
        "independent_verification": "PENDING",
    }


def read_run(path, phase):
    m = json.loads((path / "manifest.json").read_text())
    assert m["status"] == "COMPLETE" and m["phase"] == phase
    records = []
    for name, h in sorted(m["sha256"].items()):
        assert hashlib.sha256((path / name).read_bytes()).hexdigest() == h
        if name.startswith("source-"):
            records.append(json.loads((path / name).read_text()))
    return m, records


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--calibration", type=Path, required=True)
    p.add_argument("--evaluation", type=Path, required=True)
    p.add_argument("--policy", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists(), "Preserve existing analysis"
    cm, cal = read_run(a.calibration, "calibration")
    em, evaluation = read_run(a.evaluation, "evaluation")
    policy = json.loads(a.policy.read_text())
    assert (
        cm["scientific_fingerprint"]
        == em["scientific_fingerprint"]
        == policy["scientific_fingerprint"]
    )
    assert em["policy_sha256"] == hashlib.sha256(a.policy.read_bytes()).hexdigest()
    assert (
        policy["analysis_producer_sha256"]
        == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    )
    result = analyze(cal, evaluation, policy, em["config"])
    result.update(
        scientific_fingerprint=em["scientific_fingerprint"],
        producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        policy_sha256=em["policy_sha256"],
    )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result["primary"]))


if __name__ == "__main__":
    main()
