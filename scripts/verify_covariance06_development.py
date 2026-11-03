"""Independent COV06 development density/KKT/bounds/incumbent verification.

No fitter imports or classifier metric selection. Generator truth is used only
for counterfactual checks and a separately labelled feasible-point oracle control.
"""

import argparse
import hashlib
import json
import time
from collections import defaultdict
from itertools import pairwise
from pathlib import Path

import numpy as np
from scipy.linalg import cholesky, solve_triangular
from scipy.optimize import minimize_scalar
from scipy.stats import multivariate_normal

N_SHAPE = {"constant": 0, "pspl": 3, "gaussian": 2}
SIGNAL_COUNT = {"constant": 1, "pspl": 5, "gaussian": 4}


def design(t, family, shape):
    span, origin = np.ptp(t), t.min()
    if family == "constant":
        return np.ones((len(t), 1))
    if family == "pspl":
        u0, center, duration = np.exp(shape[0]), origin + shape[1] * span, np.exp(shape[2]) * span
        u2 = u0**2 + ((t - center) / duration) ** 2
        signal = (u2 + 2) / np.sqrt(u2 * (u2 + 4))
    else:
        center, width = origin + shape[0] * span, np.exp(shape[1]) * span
        signal = np.exp(-((t - center) ** 2) / (2 * width**2))
    return np.column_stack([signal, np.ones(len(t))])


def shape_coefficients(t, family, parameters):
    if family == "constant":
        return [], np.asarray(parameters)
    if family == "pspl":
        u, c, d, fs, fb = parameters
        return [np.log(u), (c - t.min()) / np.ptp(t), np.log(d / np.ptp(t))], np.array([fs, fb])
    b, a, c, w = parameters
    return [(c - t.min()) / np.ptp(t), np.log(w / np.ptp(t))], np.array([a, b])


def covariance(t, sigma, s=1.0, amplitude=0.0, length=12.0):
    z = np.sqrt(3) * abs(t[:, None] - t[None, :]) / length
    return np.diag((s * sigma) ** 2) + amplitude**2 * (1 + z) * np.exp(-z)


def point_check(t, y, sigma, family, shape, coefficients, c, expected):
    coefficients = np.asarray(coefficients)
    assert np.all(np.isfinite(coefficients)) and np.all(coefficients >= -1e-12)
    if family != "constant":
        center = shape[1] if family == "pspl" else shape[0]
        duration = np.exp(shape[2] if family == "pspl" else shape[1])
        assert -1 - 1e-12 <= center <= 2 + 1e-12
        assert 0.001 - 1e-12 <= duration <= 2 + 1e-12
        if family == "pspl":
            assert 0.01 - 1e-12 <= np.exp(shape[0]) <= 3 + 1e-12
    x = design(t, family, shape)
    residual = y - x @ coefficients
    ref = float(-multivariate_normal.logpdf(residual, cov=c))
    np.testing.assert_allclose(ref, expected, rtol=1e-9, atol=1e-7)
    lower = cholesky(c, lower=True)
    wx = solve_triangular(lower, x, lower=True)
    wr = solve_triangular(lower, -residual, lower=True)
    gradient = wx.T @ wr
    tol = 1e-6 * (1 + np.linalg.norm(wx, axis=0) * np.linalg.norm(wr))
    assert np.all(gradient[coefficients <= 1e-8] >= -tol[coefficients <= 1e-8]), (
        "NNLS dual feasibility"
    )
    assert np.all(abs(gradient[coefficients > 1e-8]) <= tol[coefficients > 1e-8]), (
        "NNLS complementarity"
    )
    return ref, float(wr @ wr)


def true_mean(t, family, truth):
    if family == "pspl":
        p = truth["pspl_parameters"]
        u2 = p["u0"] ** 2 + ((t - p["t0"]) / p["t_e"]) ** 2
        return p["f_s"] * (u2 + 2) / np.sqrt(u2 * (u2 + 4)) + p["f_b"]
    p = truth["gaussian_parameters"]
    return p["baseline"] + p["amplitude"] * np.exp(-0.5 * ((t - p["center"]) / p["width"]) ** 2)


def main():
    started = time.perf_counter()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    manifest = json.loads((args.run / "manifest.json").read_text())
    assert manifest["status"] == "COMPLETE" and manifest["completed_sources"] == 24
    for name, expected in manifest["sha256"].items():
        assert hashlib.sha256((args.run / name).read_bytes()).hexdigest() == expected, name
    records = [json.loads(p.read_text()) for p in sorted(args.run.glob("source-*.json"))]
    assert len(records) == len({r["source_id"] for r in records}) == 24
    assert {r["seed"] for r in records} == {610301, 610302, 610303}
    assert all(sum(r["seed"] == seed for r in records) == 8 for seed in [610301, 610302, 610303])
    truth_records = {
        r["source_id"]: r
        for p in (args.run / "truth").glob("source-*.json")
        for r in [json.loads(p.read_text())]
    }
    assert set(truth_records) == {r["source_id"] for r in records}
    fit_rows, trace_rows, max_nll_error, max_incumbent_excess = 0, 0, 0.0, 0.0
    oracle_gaps, nfail, availability = defaultdict(list), defaultdict(int), defaultdict(int)
    for record in records:
        assert record["split"] == "development" and record["source_id"].startswith(
            "astroml-cov06-dev-20261103-v1:"
        )
        truth = truth_records[record["source_id"]]
        assert len(record["views"]) == 8
        assert {(v["noise"], v["family"], v["condition"]) for v in record["views"]} == {
            (n, f, c)
            for n in ["white", "matern_biased"]
            for f in ["pspl", "gaussian"]
            for c in ["complete", "peak40"]
        }
        residuals, standard_draws = {}, []
        for row in record["views"]:
            t, y, sigma = map(np.asarray, [row["t"], row["flux"], row["sigma"]])
            assert len(t) == (96 if row["condition"] == "complete" else 58)
            idx = np.searchsorted(truth["t"], t)
            np.testing.assert_array_equal(np.asarray(truth["t"])[idx], t)
            true_sigma = np.asarray(truth["sigma_true"])[idx]
            np.testing.assert_allclose(sigma, true_sigma * (1 if row["noise"] == "white" else 0.65))
            if row["condition"] == "peak40":
                all_t = np.asarray(truth["t"])
                removed = np.argsort(abs(all_t - truth["pspl_parameters"]["t0"]))[:38]
                assert set(idx) == set(range(96)) - set(removed)
            additive = y - true_mean(t, row["family"], truth)
            key = row["noise"], row["condition"]
            if key in residuals:
                np.testing.assert_allclose(additive, residuals[key], atol=1e-10)
            else:
                residuals[key] = additive
                if row["condition"] == "complete":
                    spec = truth["noise_specs"][row["noise"]]
                    c = covariance(
                        t, true_sigma, amplitude=spec["amplitude"], length=spec["length_days"]
                    )
                    standard_draws.append(
                        solve_triangular(cholesky(c, lower=True), additive, lower=True)
                    )
            h = hashlib.sha256()
            for array in [t, y, sigma]:
                h.update(np.asarray(array, dtype="<f8").tobytes())
            assert h.hexdigest() == row["input_hash"]
            for mode, method in row["results"].items():
                assert not method["oracle_only"]
                if mode != "legacy_estimated":
                    assert method["input_hash"] == row["input_hash"]
                nfail[mode] += sum(not f["success"] for f in method["fits"].values())
                availability[mode] += method["valid"]
                bics = {}
                for family, fit in method["fits"].items():
                    if fit["nll"] is None:
                        assert not fit["success"] and fit["bic"] is None
                        continue
                    shape, coefficients = shape_coefficients(t, family, fit["parameters"])
                    phi = fit.get("noise")
                    if mode in ["estimated", "legacy_estimated"]:
                        assert 0.5 - 1e-12 <= phi["sigma_scale"] <= 3 + 1e-12
                        assert 1 - 1e-12 <= phi["length_days"] <= 120 + 1e-12
                        relative = phi["gp_amplitude"] / np.median(sigma)
                        assert 0 <= relative <= 4 + 1e-12
                        if mode == "legacy_estimated":
                            assert relative >= 1e-4 - 1e-12
                        if mode == "estimated":
                            np.testing.assert_allclose(
                                relative**2, phi["relative_variance"], atol=1e-12
                            )
                            assert phi["length_unidentified_at_zero"] == (
                                phi["relative_variance"] == 0
                            )
                        c = covariance(
                            t, sigma, phi["sigma_scale"], phi["gp_amplitude"], phi["length_days"]
                        )
                    else:
                        c = covariance(t, sigma, phi["sigma_scale"] if mode == "scale" else 1.0)
                    ref, quadratic = point_check(
                        t, y, sigma, family, shape, coefficients, c, fit["nll"]
                    )
                    if "quadratic" in fit:
                        np.testing.assert_allclose(
                            quadratic, fit["quadratic"], atol=1e-7, rtol=1e-9
                        )
                    max_nll_error = max(max_nll_error, abs(ref - fit["nll"]))
                    k = SIGNAL_COUNT[family] + (
                        3 if mode in ["estimated", "legacy_estimated"] else int(mode == "scale")
                    )
                    bics[family] = 2 * ref + k * np.log(len(t))
                    np.testing.assert_allclose(bics[family], fit["bic"], atol=1e-7, rtol=1e-9)
                    fit_rows += 1
                    if mode == "scale":
                        parent = row["results"]["diagonal"]["fits"][family]
                        assert (
                            fit["parameters"] == parent["parameters"]
                            and fit["success"] == parent["success"]
                        )
                        q = parent["quadratic"]
                        n_obs = len(t)
                        scalar = lambda s, q=q, n=n_obs: q / (2 * s**2) + n * np.log(s)
                        search = minimize_scalar(
                            scalar, bounds=(0.5, 3.0), method="bounded", options={"xatol": 1e-10}
                        )
                        expected_min = min(search.fun, scalar(0.5), scalar(3.0))
                        np.testing.assert_allclose(
                            scalar(phi["sigma_scale"]), expected_min, atol=1e-7, rtol=1e-9
                        )
                    elif mode != "legacy_estimated":
                        assert all(s["likelihood_evaluations"] <= 2000 for s in fit["starts"])
                        refs = []
                        for point in fit["incumbent_trace"]:
                            theta = point["theta"]
                            n_shape = N_SHAPE[family]
                            if mode == "estimated":
                                logs, q, logell = theta[n_shape:]
                                assert 0 <= q <= 16 + 1e-12
                                assert 0.5 - 1e-12 <= np.exp(logs) <= 3 + 1e-12
                                assert 1 - 1e-12 <= np.exp(logell) <= 120 + 1e-12
                                pc = covariance(
                                    t,
                                    sigma,
                                    np.exp(logs),
                                    np.sqrt(q) * np.median(sigma),
                                    np.exp(logell),
                                )
                            else:
                                pc = covariance(t, sigma)
                            p_ref, _ = point_check(
                                t,
                                y,
                                sigma,
                                family,
                                theta[:n_shape],
                                point["coefficients"],
                                pc,
                                point["nll"],
                            )
                            refs.append(p_ref)
                            trace_rows += 1
                            max_nll_error = max(max_nll_error, abs(p_ref - point["nll"]))
                        assert refs and all(b <= a + 1e-7 for a, b in pairwise(refs))
                        np.testing.assert_allclose(
                            min(refs), fit["best_saved_feasible_nll"], atol=1e-7
                        )
                        tolerance = fit["incumbent_tolerance"]
                        assert ref <= min(refs) + tolerance + 1e-8
                        max_incumbent_excess = max(max_incumbent_excess, ref - min(refs))
                        eligible = [
                            s
                            for s in fit["starts"]
                            if s["success"]
                            and s["final_nll"] <= fit["best_saved_feasible_nll"] + tolerance
                        ]
                        assert fit["success"] == bool(eligible) and fit["fallback_used"] == (
                            not bool(eligible)
                        )
                        if mode == "estimated":
                            np.testing.assert_allclose(
                                fit["initial_incumbent_nll"],
                                row["results"]["scale"]["fits"][family]["nll"],
                                atol=1e-7,
                            )
                            assert ref <= fit["initial_incumbent_nll"] + tolerance + 1e-8
                    if family == row["family"] and mode in ["estimated", "legacy_estimated"]:
                        spec = truth["noise_specs"][row["noise"]]
                        amplitude = max(
                            spec["amplitude"],
                            1e-4 * np.median(sigma) if mode == "legacy_estimated" else 0.0,
                        )
                        feasible_c = covariance(
                            t, sigma, float(np.median(true_sigma / sigma)), amplitude, 12.0
                        )
                        feasible_nll = float(-multivariate_normal.logpdf(additive, cov=feasible_c))
                        oracle_gaps[
                            "/".join([row["noise"], row["condition"], family, mode])
                        ].append(ref - feasible_nll)
                if len(bics) == 3:
                    np.testing.assert_allclose(
                        min(bics["constant"], bics["gaussian"]) - bics["pspl"],
                        method["score"],
                        atol=1e-7,
                    )
                else:
                    assert method["score"] is None
                assert method["valid"] == (
                    len(bics) == 3 and all(f["success"] for f in method["fits"].values())
                )
        for draw in standard_draws[1:]:
            np.testing.assert_allclose(draw, standard_draws[0], atol=1e-9)
    assert fit_rows == 2304
    output = {
        "status": "PASS",
        "purpose": "independent numerical development verification, not classifier evaluation",
        "independent_sources": 24,
        "selected_fit_rows": fit_rows,
        "incumbent_points_checked": trace_rows,
        "max_absolute_nll_difference": max_nll_error,
        "max_selected_minus_best_reference_nll": max_incumbent_excess,
        "nonconverged_selected_fits": dict(nfail),
        "valid_method_sets": dict(availability),
        "oracle_feasible_point_control": {
            k: {
                "views": len(v),
                "missed_feasible_improvements": sum(g > 1e-5 for g in v),
                "max_nll_gap": max(v),
            }
            for k, v in oracle_gaps.items()
        },
        "runtime_seconds": time.perf_counter() - started,
        "classification_metrics_computed": False,
        "source_fingerprint": manifest["scientific_fingerprint"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {k: v for k, v in output.items() if k != "oracle_feasible_point_control"}, indent=2
        )
    )


if __name__ == "__main__":
    main()
