"""Independent count/ranking/binomial-root/weighted-bootstrap verifier. No fit imports."""

import argparse
import hashlib
import json
import math
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import brentq
from scipy.stats import binom


def close(a, b):
    if a is None or b is None:
        assert a is b
    else:
        assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10), (a, b)


def ratio(a, b):
    return a / b if b else None


def limits(k, n):
    return [
        0.0 if k == 0 else brentq(lambda p: binom.sf(k - 1, n, p) - 0.025, 0.0, 1.0, xtol=1e-14),
        1.0 if k == n else brentq(lambda p: binom.cdf(k, n, p) - 0.025, 0.0, 1.0, xtol=1e-14),
    ]


def score(m, accepted_only=False):
    return -math.inf if m["score"] is None or (accepted_only and not m["valid"]) else m["score"]


def positive(m, threshold):
    return (
        threshold is not None and m["valid"] and m["score"] is not None and m["score"] >= threshold
    )


def get(record, noise, family, condition, mode):
    found = [
        r["results"][mode]
        for r in record["views"]
        if r["noise"] == noise and r["family"] == family and r["condition"] == condition
    ]
    assert len(found) == 1
    return found[0]


def weighted_threshold(cal, weights, mode, cfg):
    histogram = defaultdict(int)
    for record, weight in zip(cal, weights):
        for noise in cfg["calibration_noise"]:
            histogram[score(get(record, noise, "gaussian", "complete", mode), True)] += int(weight)
    count = sum(histogram.values())
    rank = math.ceil((1 - cfg["target_calibration_fpr"]) * count)
    cursor = 0
    for value, weight in sorted(histogram.items()):
        cursor += weight
        if cursor >= rank:
            result = float(np.nextafter(value, math.inf)) if math.isfinite(value) else None
            return result if result is None or math.isfinite(result) else None
    raise AssertionError("missing weighted order statistic")


def weights(rng, records, seeds):
    result = np.zeros(len(records), dtype=int)
    for seed in seeds:
        indices = [i for i, r in enumerate(records) if r["seed"] == seed]
        sampled = rng.integers(0, len(indices), size=len(indices))
        multiplicities = np.bincount(sampled, minlength=len(indices))
        for i, c in zip(indices, multiplicities):
            result[i] = c
    return result


def percentile(values, q):
    values = sorted(values)
    position = (len(values) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def load(run, phase):
    m = json.loads((run / "manifest.json").read_text())
    assert m["phase"] == phase and m["status"] == "COMPLETE"
    rows = []
    for file, h in sorted(m["sha256"].items()):
        assert hashlib.sha256((run / file).read_bytes()).hexdigest() == h
        if file.startswith("source-"):
            rows.append(json.loads((run / file).read_text()))
    return m, rows


def verify(cal, evaluation, policy, summary, cfg):
    assert len(cal) == 240 and len(evaluation) == 360
    assert len({r["source_id"] for r in cal + evaluation}) == 600
    assert set(policy["source_ids"]) == {r["source_id"] for r in cal}
    for mode in cfg["methods"]:
        close(
            weighted_threshold(cal, np.ones(len(cal), int), mode, cfg),
            policy["thresholds"][mode]["threshold"],
        )
    table_keys = set()
    for table in summary["tables"]:
        noise, condition, mode, seed = (table[k] for k in ["noise", "condition", "method", "seed"])
        key = (noise, condition, mode, seed)
        assert key not in table_keys
        table_keys.add(key)
        group = [r for r in evaluation if seed is None or r["seed"] == seed]
        n = len(group)
        pos = [get(r, noise, "pspl", condition, mode) for r in group]
        neg = [get(r, noise, "gaussian", condition, mode) for r in group]
        threshold = policy["thresholds"][mode]["threshold"]
        tp = sum(positive(m, threshold) for m in pos)
        fp = sum(positive(m, threshold) for m in neg)
        ap = sum(m["valid"] for m in pos)
        an = sum(m["valid"] for m in neg)
        expected = {
            "positive_sources": n,
            "negative_sources": n,
            "true_positives": tp,
            "false_positives": fp,
            "recall_all": tp / n,
            "fpr_all": fp / n,
            "accepted_positive": ap,
            "accepted_negative": an,
            "coverage": (ap + an) / (2 * n),
            "rejected_positive": n - ap,
            "rejected_negative": n - an,
            "fpr_accepted": ratio(fp, an),
            "recall_accepted": ratio(tp, ap),
            "selective_risk": ratio(fp + ap - tp, ap + an),
            "balanced_false_discovery_fraction": ratio(fp, tp + fp),
            "nonconverged_selected_means": sum(
                not f["success"] for m in pos + neg for f in m["fits"].values()
            ),
            "unavailable_selected_means": sum(
                f["nll"] is None for m in pos + neg for f in m["fits"].values()
            ),
            "incremental_method_elapsed_sum_seconds": sum(m["runtime_seconds"] for m in pos + neg),
        }
        for k, v in expected.items():
            close(v, table[k])
        for a, b in zip(limits(tp, n), table["recall_cp95"]):
            close(a, b)
        for a, b in zip(limits(fp, n), table["fpr_cp95"]):
            close(a, b)
        ps = [score(m) for m in pos]
        ns = [score(m) for m in neg]
        auc = sum((a > b) + 0.5 * (a == b) for a in ps for b in ns) / (n * n)
        close(auc, table["raw_auc"])
        positives = Counter(ps)
        negatives = Counter(ns)
        ctp = 0
        total = 0
        average_precision = 0.0
        pr = []
        for value in sorted(positives.keys() | negatives.keys(), reverse=True):
            ctp += positives[value]
            total += positives[value] + negatives[value]
            average_precision += (ctp / total) * positives[value] / n
            pr.append((value, ctp / total, ctp / n))
        close(average_precision, table["empirical_average_precision"])
        assert len(pr) == len(table["precision_recall_groups"])
        for (value, precision, recall), saved in zip(pr, table["precision_recall_groups"]):
            close(value if math.isfinite(value) else None, saved["threshold"])
            close(precision, saved["precision"])
            close(recall, saved["recall"])
            assert saved["unavailable_score_sentinel"] == (not math.isfinite(value))
    assert table_keys == {
        (n, c, m, s)
        for n in cfg["evaluation_noise"]
        for c in cfg["evaluation_conditions"]
        for m in cfg["methods"]
        for s in [None] + cfg["seeds"]
    }
    rng = np.random.default_rng(cfg["bootstrap_seed"])
    independent = []
    for replicate, saved in enumerate(summary["bootstrap_draws"]):
        cw = weights(rng, cal, cfg["seeds"])
        ew = weights(rng, evaluation, cfg["seeds"])
        outcomes = {}
        assert saved["replicate"] == replicate
        for mode in cfg["primary_methods"]:
            limit = weighted_threshold(cal, cw, mode, cfg)
            close(limit, saved["bootstrap_thresholds"][mode])
            outcomes[mode] = {
                f: sum(
                    int(w)
                    * positive(
                        get(r, cfg["primary_noise"], f, cfg["primary_condition"], mode), limit
                    )
                    for r, w in zip(evaluation, ew)
                )
                / int(ew.sum())
                for f in ["pspl", "gaussian"]
            }
        a, b = cfg["primary_methods"]
        df = outcomes[a]["gaussian"] - outcomes[b]["gaussian"]
        dr = outcomes[a]["pspl"] - outcomes[b]["pspl"]
        close(df, saved["delta_fpr"])
        close(dr, saved["delta_recall"])
        independent.append((df, dr))
    assert len(independent) == cfg["bootstrap_replicates"]
    intervals = {
        k: [percentile([d[i] for d in independent], p) for p in [0.025, 0.975]]
        for i, k in enumerate(["delta_fpr", "delta_recall"])
    }
    for key, values in intervals.items():
        for a, b in zip(values, summary["primary"]["joint_source_bootstrap_ci95"][key]):
            close(a, b)
    a, b = cfg["primary_methods"]
    primary = {
        mode: next(
            t
            for t in summary["tables"]
            if t["noise"] == cfg["primary_noise"]
            and t["condition"] == cfg["primary_condition"]
            and t["method"] == mode
            and t["seed"] is None
        )
        for mode in [a, b]
    }
    close(
        primary[a]["fpr_all"] - primary[b]["fpr_all"], summary["primary"]["observed"]["delta_fpr"]
    )
    close(
        primary[a]["recall_all"] - primary[b]["recall_all"],
        summary["primary"]["observed"]["delta_recall"],
    )
    close(primary[a]["coverage"], summary["primary"]["observed"]["estimated_coverage"])
    supported = (
        intervals["delta_fpr"][1] < 0
        and intervals["delta_recall"][0] >= -cfg["recall_noninferiority_margin"]
        and primary[a]["coverage"] >= cfg["minimum_coverage"]
    )
    assert supported == summary["primary"]["frozen_composite_criterion_supported"]
    return {
        "status": "PASS",
        "independent_calibration_sources": 240,
        "independent_evaluation_sources": 360,
        "tables_checked": len(table_keys),
        "weighted_joint_bootstrap_replicates_checked": len(independent),
        "cp_reference": "independent binomial-tail root, not producer beta.ppf",
        "auc_reference": "all positive-negative score pairs with half ties",
        "ap_reference": "independent score-group count sums",
        "primary_criterion_supported": bool(supported),
        "no_fitting_or_truth_inputs": True,
    }


def main():
    started = time.perf_counter()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--calibration", type=Path, required=True)
    p.add_argument("--evaluation", type=Path, required=True)
    p.add_argument("--policy", type=Path, required=True)
    p.add_argument("--summary", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    cm, cal = load(a.calibration, "calibration")
    em, evaluation = load(a.evaluation, "evaluation")
    policy = json.loads(a.policy.read_text())
    summary = json.loads(a.summary.read_text())
    assert (
        cm["scientific_fingerprint"]
        == em["scientific_fingerprint"]
        == policy["scientific_fingerprint"]
        == summary["scientific_fingerprint"]
    )
    assert (
        em["policy_sha256"]
        == summary["policy_sha256"]
        == hashlib.sha256(a.policy.read_bytes()).hexdigest()
    )
    result = verify(cal, evaluation, policy, summary, em["config"])
    result.update(
        runtime_seconds=time.perf_counter() - started,
        verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        summary_sha256=hashlib.sha256(a.summary.read_bytes()).hexdigest(),
    )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
