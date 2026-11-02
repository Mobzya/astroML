"""Independent full-density, KKT, white-oracle and primary bootstrap verification."""

import argparse
import json
from pathlib import Path

import numpy as np
from analyze_reconstruction02 import load_records
from scipy.linalg import cholesky, solve_triangular
from scipy.optimize import brentq
from scipy.stats import binomtest, multivariate_normal


def clean_flux(t, family, truth):
    """Independent algebraic means, used only by the verifier, never inference."""
    if family == "pspl":
        p = truth["pspl_parameters"]
        u2 = p["u0"] ** 2 + ((t - p["t0"]) / p["t_e"]) ** 2
        return p["f_s"] * (u2 + 2) / np.sqrt(u2 * (u2 + 4)) + p["f_b"]
    if family == "gaussian":
        p = truth["gaussian_parameters"]
        return p["baseline"] + p["amplitude"] * np.exp(-0.5 * ((t - p["center"]) / p["width"]) ** 2)
    # Derivative of the equal two-Gaussian mixture gives x=2*tanh(2*x).
    peak_x = brentq(lambda x: x - 2 * np.tanh(2 * x), 1, 3)

    def shape(x):
        return 0.5 * (np.exp(-0.5 * (x - 2) ** 2) + np.exp(-0.5 * (x + 2) ** 2))

    peak = shape(peak_x)
    half = brentq(lambda x: shape(x) - peak / 2, 2, 8)
    x = (t - truth["pspl_parameters"]["t0"]) * 2 * half / truth["fwhm_days"]
    return 1 + truth["amplitude"] * shape(x) / peak


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    p.add_argument("--summary", type=Path)
    p.add_argument("--policy", type=Path)
    args = p.parse_args()
    manifest, records = load_records(args.run)
    config = json.loads(Path("configs/experiment_05.json").read_text())
    truths = {
        r["source_id"]: r
        for f in sorted((args.run / "truth").glob("batch-*.json"))
        for r in json.loads(f.read_text())
    }
    count, max_error = 0, 0.0
    assert set(truths) == {r["source_id"] for r in records}
    for record in records:
        assert record["split"] == manifest["phase"]
        truth = truths[record["source_id"]]
        expected_grid = {
            (n, f, c)
            for n in config[manifest["phase"] + "_noise"]
            for f in config[manifest["phase"] + "_families"]
            for c in config[manifest["phase"] + "_conditions"]
        }
        assert len(record["views"]) == len(expected_grid)
        assert {(v["noise"], v["family"], v["condition"]) for v in record["views"]} == expected_grid
        shared_noise, standard_draws = {}, []
        complete = {
            (v["noise"], v["family"]): v for v in record["views"] if v["condition"] == "complete"
        }
        for row in record["views"]:
            t, y, sigma = map(np.asarray, [row["t"], row["flux"], row["sigma"]])
            assert len(t) == (96 if row["condition"] == "complete" else 58)
            idx = [truth["t"].index(v) for v in t]
            true_sigma = np.array(truth["sigma_true"])[idx]
            spec = truth["noise_specs"][row["noise"]]
            distance = np.abs(t[:, None] - t[None, :]) / spec["length_days"]
            kernel = (
                np.exp(-distance)
                if row["noise"] == "ou_biased"
                else (1 + np.sqrt(3) * distance) * np.exp(-np.sqrt(3) * distance)
            )
            oracle = np.diag(true_sigma**2) + spec["amplitude"] ** 2 * kernel
            np.testing.assert_allclose(
                sigma,
                true_sigma * (1 if row["noise"] == "white" else config["reported_sigma_bias"]),
            )
            additive = y - clean_flux(t, row["family"], truth)
            noise_key = row["noise"], row["condition"]
            if noise_key in shared_noise:
                np.testing.assert_allclose(additive, shared_noise[noise_key], atol=1e-11)
            else:
                shared_noise[noise_key] = additive
                if row["condition"] == "complete":
                    standard_draws.append(
                        solve_triangular(cholesky(oracle, lower=True), additive, lower=True)
                    )
            if row["condition"] != "complete":
                full = complete[row["noise"], row["family"]]
                np.testing.assert_array_equal(y, np.array(full["flux"])[idx])
                if row["condition"] == "peak40":
                    all_t = np.array(truth["t"])
                    removed = np.argsort(abs(all_t - truth["pspl_parameters"]["t0"]))[:38]
                    assert set(idx) == set(range(96)) - set(removed)
            for mode, method in row["results"].items():
                assert method["oracle_only"] == (mode == "oracle")
                bics = {}
                for family, fit in method["fits"].items():
                    if fit["bic"] is None:
                        continue
                    if mode == "diagonal":
                        c = np.diag(sigma * sigma)
                    elif mode == "oracle":
                        c = oracle
                    else:
                        phi = fit["noise"]
                        z = np.sqrt(3) * np.abs(t[:, None] - t[None, :]) / phi["length_days"]
                        c = np.diag((phi["sigma_scale"] * sigma) ** 2) + phi[
                            "gp_amplitude"
                        ] ** 2 * (1 + z) * np.exp(-z)
                    pars = fit["parameters"]
                    if family == "constant":
                        design, coefficients = np.ones((len(t), 1)), np.array(pars)
                    elif family == "gaussian":
                        b, a, center, width = pars
                        design = np.column_stack(
                            [np.exp(-((t - center) ** 2) / (2 * width**2)), np.ones(len(t))]
                        )
                        coefficients = np.array([a, b])
                    else:
                        u0, center, te, fs, fb = pars
                        u2 = u0 * u0 + ((t - center) / te) ** 2
                        design = np.column_stack(
                            [(u2 + 2) / np.sqrt(u2 * (u2 + 4)), np.ones(len(t))]
                        )
                        coefficients = np.array([fs, fb])
                    residual = y - design @ coefficients
                    assert np.all(np.isfinite(coefficients)) and np.all(coefficients >= -1e-12)
                    if family != "constant":
                        normalized_center = (center - t.min()) / np.ptp(t)
                        duration = te if family == "pspl" else width
                        assert -1 - 1e-12 <= normalized_center <= 2 + 1e-12
                        assert 0.001 - 1e-12 <= duration / np.ptp(t) <= 2 + 1e-12
                        if family == "pspl":
                            assert 0.01 - 1e-12 <= u0 <= 3 + 1e-12
                    if mode == "estimated":
                        assert 0.5 - 1e-12 <= phi["sigma_scale"] <= 3 + 1e-12
                        assert 1e-4 - 1e-12 <= phi["gp_amplitude"] / np.median(sigma) <= 4 + 1e-12
                        assert 1 - 1e-12 <= phi["length_days"] <= 120 + 1e-12
                    ref = -multivariate_normal.logpdf(residual, cov=c)
                    np.testing.assert_allclose(ref, fit["nll"], rtol=1e-8, atol=1e-7)
                    k = {"constant": 1, "pspl": 5, "gaussian": 4}[family] + (
                        3 if mode == "estimated" else 0
                    )
                    bics[family] = 2 * ref + k * np.log(len(t))
                    np.testing.assert_allclose(bics[family], fit["bic"], rtol=1e-8, atol=1e-7)
                    lower = cholesky(c, lower=True)
                    x = solve_triangular(lower, design, lower=True)
                    wr = solve_triangular(lower, -residual, lower=True)
                    g = x.T @ wr
                    tol = 1e-6 * (1 + np.linalg.norm(x, axis=0) * np.linalg.norm(wr))
                    assert np.all(g[coefficients <= 1e-8] >= -tol[coefficients <= 1e-8])
                    assert np.all(abs(g[coefficients > 1e-8]) <= tol[coefficients > 1e-8])
                    count += 1
                    max_error = max(max_error, abs(ref - fit["nll"]))
                if len(bics) == 3:
                    np.testing.assert_allclose(
                        min(bics["constant"], bics["gaussian"]) - bics["pspl"],
                        method["score"],
                        rtol=1e-8,
                        atol=1e-7,
                    )
                else:
                    assert method["score"] is None and not method["valid"]
                assert method["valid"] == all(f["success"] for f in method["fits"].values())
            if row["noise"] == "white":
                for family in ["constant", "pspl", "gaussian"]:
                    np.testing.assert_allclose(
                        row["results"]["diagonal"]["fits"][family]["nll"],
                        row["results"]["oracle"]["fits"][family]["nll"],
                        atol=1e-9,
                    )
        for draw in standard_draws[1:]:
            np.testing.assert_allclose(draw, standard_draws[0], atol=1e-9)
    if manifest["phase"] == "calibration" and args.policy:
        policy = json.loads(args.policy.read_text())
        assert policy["source_ids"] == [r["source_id"] for r in records]
        for mode in config["methods"]:
            negatives = [
                v["results"][mode]["score"] if v["results"][mode]["valid"] else -np.inf
                for r in records
                for v in r["views"]
                if v["family"] == "gaussian"
            ]
            quantile = np.quantile(negatives, 0.95, method="inverted_cdf")
            threshold = np.nextafter(quantile, np.inf) if np.isfinite(quantile) else None
            assert threshold == policy["thresholds"][mode]
            fp = sum(v >= threshold for v in negatives) if threshold is not None else 0
            assert fp == policy["calibration_fp"][mode]
    if args.summary and args.policy:
        summary, policy = [json.loads(p.read_text()) for p in [args.summary, args.policy]]
        assert {r["source_id"] for r in records}.isdisjoint(policy["source_ids"])
        primary_arrays = {}
        for key, methods in summary["scenarios"].items():
            noise, condition, negative = key.split("/")
            for mode, expected in methods.items():
                p_scores, n_scores, pv, nv = [], [], [], []
                for record in records:
                    chosen = {
                        v["family"]: v["results"][mode]
                        for v in record["views"]
                        if v["noise"] == noise and v["condition"] == condition
                    }
                    for family, scores, valid in [("pspl", p_scores, pv), (negative, n_scores, nv)]:
                        scores.append(
                            chosen[family]["score"]
                            if chosen[family]["score"] is not None
                            else -np.inf
                        )
                        valid.append(chosen[family]["valid"])
                pos, neg, pv, nv = (
                    np.array(p_scores),
                    np.array(n_scores),
                    np.array(pv),
                    np.array(nv),
                )
                threshold = policy["thresholds"][mode]
                tp = int(np.count_nonzero(pv & (pos >= threshold))) if threshold is not None else 0
                fp = int(np.count_nonzero(nv & (neg >= threshold))) if threshold is not None else 0
                assert (tp, fp, len(neg)) == (expected["tp"], expected["fp"], expected["negatives"])
                assert expected["rejected_positive"] == int((~pv).sum())
                assert expected["rejected_negative"] == int((~nv).sum())
                derived = {
                    "fpr_accepted_negative": fp / nv.sum() if nv.any() else None,
                    "selective_risk": (fp + pv.sum() - tp) / (pv.sum() + nv.sum())
                    if pv.sum() + nv.sum()
                    else None,
                    "fdr_balanced": fp / (tp + fp) if tp + fp else None,
                }
                for name, value in derived.items():
                    if value is None:
                        assert expected[name] is None
                    else:
                        np.testing.assert_allclose(value, expected[name])
                np.testing.assert_allclose(
                    np.mean((pos[:, None] > neg) + 0.5 * (pos[:, None] == neg)), expected["auc"]
                )
                np.testing.assert_allclose(
                    [fp / len(neg), tp / len(pos), (pv.sum() + nv.sum()) / (len(pos) + len(neg))],
                    [expected["fpr_all"], expected["recall_all"], expected["coverage"]],
                )
                for k, n, name in [
                    (fp, len(neg), "fpr_all_ci95"),
                    (tp, len(pos), "recall_all_ci95"),
                ]:
                    ci = binomtest(k, n).proportion_ci(confidence_level=0.95, method="exact")
                    np.testing.assert_allclose([ci.low, ci.high], expected[name], atol=1e-10)
                for seed, by_scenario in summary["per_seed"].items():
                    ix = np.array([r["seed"] == int(seed) for r in records])
                    ep = by_scenario[key][mode]
                    stp = (
                        int(np.count_nonzero(pv[ix] & (pos[ix] >= threshold)))
                        if threshold is not None
                        else 0
                    )
                    sfp = (
                        int(np.count_nonzero(nv[ix] & (neg[ix] >= threshold)))
                        if threshold is not None
                        else 0
                    )
                    assert (stp, sfp, int(ix.sum())) == (ep["tp"], ep["fp"], ep["pairs"])
                if key == summary["primary"]["scenario"] and mode in ["diagonal", "estimated"]:
                    primary_arrays[mode] = pos, neg, pv, nv
        config = json.loads(Path("configs/experiment_05.json").read_text())
        rng = np.random.default_rng(config["bootstrap_seed"])
        cg = [np.flatnonzero(np.array(policy["source_seeds"]) == s) for s in config["seeds"]]
        eg = [np.flatnonzero(np.array([r["seed"] for r in records]) == s) for s in config["seeds"]]
        draws = []
        for _ in range(config["bootstrap_replicates"]):
            ci = np.concatenate([rng.choice(g, len(g), replace=True) for g in cg])
            ei = np.concatenate([rng.choice(g, len(g), replace=True) for g in eg])
            cw = np.bincount(ci, minlength=len(policy["source_ids"]))
            ew = np.bincount(ei, minlength=len(records))
            metrics = {}
            for mode, (pos, neg, pv, nv) in primary_arrays.items():
                v = np.array(
                    [
                        [x if x is not None else -np.inf for x in row]
                        for row in policy["negative_calibration_scores"][mode]
                    ]
                ).ravel()
                weights = np.repeat(cw, 2)
                order = np.argsort(v)
                rank = int(np.ceil((1 - config["target_calibration_fpr"]) * weights.sum())) - 1
                selected = v[order[np.searchsorted(np.cumsum(weights[order]), rank, side="right")]]
                threshold = np.nextafter(selected, np.inf) if np.isfinite(selected) else None
                fp = (
                    float(ew @ (nv & (neg >= threshold))) / ew.sum()
                    if threshold is not None
                    else 0.0
                )
                tp = (
                    float(ew @ (pv & (pos >= threshold))) / ew.sum()
                    if threshold is not None
                    else 0.0
                )
                metrics[mode] = fp, tp
            draws.append(
                [
                    metrics["estimated"][0] - metrics["diagonal"][0],
                    metrics["estimated"][1] - metrics["diagonal"][1],
                ]
            )
        np.testing.assert_allclose(
            draws, summary["primary"]["bootstrap_draws_delta_fpr_recall"], atol=1e-12
        )
        ci = np.quantile(draws, [0.025, 0.975], axis=0)
        np.testing.assert_allclose(ci[:, 0], summary["primary"]["delta_fpr_ci95_joint_bootstrap"])
        np.testing.assert_allclose(
            ci[:, 1], summary["primary"]["delta_recall_ci95_joint_bootstrap"]
        )
        primary = summary["scenarios"][summary["primary"]["scenario"]]
        supported = bool(
            ci[1, 0] < 0
            and ci[0, 1] >= -config["recall_noninferiority_margin"]
            and primary["estimated"]["coverage"] >= config["minimum_coverage"]
        )
        assert supported == summary["primary"]["full_success_criterion_supported"]
    print(
        json.dumps(
            {
                "status": "PASS",
                "independent_sources": len(records),
                "fit_rows": count,
                "max_absolute_nll_difference": max_error,
            }
        )
    )


if __name__ == "__main__":
    main()
