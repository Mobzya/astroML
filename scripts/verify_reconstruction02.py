"""Independently verify R2 observation budgets, saved fits and score/metric denominators."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import binomtest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--policy", type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.run / "run_manifest.json").read_text())
    assert manifest["status"] == "COMPLETE"
    for name, checksum in manifest["sha256"].items():
        assert hashlib.sha256((args.run / name).read_bytes()).hexdigest() == checksum, name
    records = [r for f in sorted(args.run.glob("batch-*.json")) for r in json.loads(f.read_text())]
    assert len(records) == len({r["source_id"] for r in records}) == manifest["expected_pairs"]
    fit_rows, maximum = 0, 0.0
    for r in records:
        lookup = {(v["family"], v["condition"]): v for v in r["views"]}
        assert len(lookup) == 6
        for c in ["complete", "random40", "peak40"]:
            p, n = lookup["pspl", c], lookup["gaussian", c]
            assert len(p["t"]) == (96 if c == "complete" else 58)
            np.testing.assert_array_equal(p["t"], n["t"])
            np.testing.assert_array_equal(p["sigma"], n["sigma"])
            for row in [p, n]:
                t, y, sigma = map(np.asarray, [row["t"], row["flux"], row["sigma"]])
                assert set(t).issubset(lookup[row["family"], "complete"]["t"])
                if row["error"]:
                    assert not row["valid"]
                    continue
                recalculated = {}
                for model, fit in row["fits"].items():
                    pars = fit["parameters"]
                    if model == "constant":
                        prediction = np.full_like(y, pars[0])
                    elif model == "gaussian":
                        b, a, center, width = pars
                        prediction = b + a * np.exp(-((t - center) ** 2) / (2 * width**2))
                    else:
                        u0, t0, te, fs, fb = pars
                        u2 = u0 * u0 + ((t - t0) / te) ** 2
                        prediction = fs * (u2 + 2) / np.sqrt(u2 * (u2 + 4)) + fb
                    chi2 = np.sum(((y - prediction) / sigma) ** 2)
                    bic = (
                        chi2 + np.log(2 * np.pi * sigma * sigma).sum() + len(pars) * np.log(len(t))
                    )
                    for name, value in [("chi2", chi2), ("bic", bic)]:
                        assert np.isclose(value, fit[name], rtol=1e-9, atol=1e-8)
                        maximum = max(maximum, abs(value - fit[name]))
                    recalculated[model] = bic
                    fit_rows += 1
                assert np.isclose(
                    min(recalculated["constant"], recalculated["gaussian"]) - recalculated["pspl"],
                    row["score"],
                    rtol=1e-9,
                    atol=1e-8,
                )
                assert row["valid"] == (
                    row["fits"]["pspl"]["success"] and row["fits"]["gaussian"]["success"]
                )
    if args.summary and args.policy:
        summary, policy = json.loads(args.summary.read_text()), json.loads(args.policy.read_text())
        assert {r["source_id"] for r in records}.isdisjoint(policy["source_ids"])
        config = json.loads(Path("configs/reconstruction_02.json").read_text())
        rng = np.random.default_rng(config["bootstrap_seed"])
        groups = [
            [i for i, r in enumerate(records) if r["seed"] == seed] for seed in config["seeds"]
        ]
        weights = []
        for _ in range(config["bootstrap_replicates"]):
            indices = np.concatenate([rng.choice(g, len(g), replace=True) for g in groups])
            weights.append(np.bincount(indices, minlength=len(records)))
        weights = np.array(weights, dtype=float)
        auc_draws = {}
        for c, expected in summary["conditions"].items():
            p, n, pv, nv = [], [], [], []
            for record in records:
                for row in record["views"]:
                    if row["condition"] == c:
                        (p if row["family"] == "pspl" else n).append(
                            row["score"] if row["score"] is not None else -np.inf
                        )
                        (pv if row["family"] == "pspl" else nv).append(row["valid"])
            p, n, pv, nv = np.array(p), np.array(n), np.array(pv), np.array(nv)
            brute_auc = np.mean((p[:, None] > n).astype(float) + 0.5 * (p[:, None] == n))
            assert np.isclose(brute_auc, expected["auc"])
            threshold = policy["threshold"]
            tp = int(np.count_nonzero(pv & (p >= threshold))) if threshold is not None else 0
            fp = int(np.count_nonzero(nv & (n >= threshold))) if threshold is not None else 0
            assert (tp, fp, len(n)) == (expected["tp"], expected["fp"], expected["negatives"])
            assert np.isclose(fp / len(n), expected["fpr_all"])
            assert np.isclose(tp / len(p), expected["recall_all"])
            assert np.isclose((pv.sum() + nv.sum()) / (len(p) + len(n)), expected["coverage"])
            # Independent pair-comparison matrix and multinomial weights, not rank sums.
            comparisons = (p[:, None] > n).astype(float) + 0.5 * (p[:, None] == n)
            auc_draws[c] = (
                np.einsum("bi,ij,bj->b", weights, comparisons, weights, optimize=True)
                / len(records) ** 2
            )
            np.testing.assert_allclose(
                np.quantile(auc_draws[c], [0.025, 0.975]),
                expected["auc_ci95_pair_bootstrap"],
                atol=1e-12,
            )
            for count, total, key in [
                (fp, len(n), "fpr_all_ci95"),
                (tp, len(p), "recall_all_ci95"),
            ]:
                ref = binomtest(count, total).proportion_ci(confidence_level=0.95, method="exact")
                np.testing.assert_allclose([ref.low, ref.high], expected[key], atol=1e-10)
        np.testing.assert_allclose(
            np.quantile(auc_draws["peak40"] - auc_draws["random40"], [0.025, 0.975]),
            summary["primary_contrast"]["ci95_pair_bootstrap"],
            atol=1e-12,
        )
    print(
        json.dumps(
            {
                "status": "PASS",
                "independent_pairs": len(records),
                "fit_rows": fit_rows,
                "max_absolute_metric_difference": maximum,
            }
        )
    )


if __name__ == "__main__":
    main()
