"""Independent COV06 bounded-witness numerical/input/source verifier; no fitting.

Pure reference helpers from development verifier never open its data. No old
R2/COV05 event-level records are accessed. No classification selection/metrics.
"""

import argparse
import hashlib
import json
import time
from collections import Counter
from itertools import pairwise
from pathlib import Path

import numpy as np
from scipy.linalg import cholesky, solve_triangular
from scipy.optimize import minimize_scalar
from verify_covariance06_development import (
    N_SHAPE,
    SIGNAL_COUNT,
    covariance,
    design,
    point_check,
    shape_coefficients,
    true_mean,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def assigned(namespace, seed, counts, phase):
    total = sum(counts.values())
    key = f"{namespace}:{seed}:split-assignment"
    order = np.random.default_rng(
        int.from_bytes(hashlib.sha256(key.encode()).digest()[:16], "big")
    ).permutation(total)
    start = sum(n for name, n in counts.items() if name < phase)
    return [f"{namespace}:{seed}:{i:08d}" for i in order[start : start + counts[phase]]]


def true_cov(t, sigma, noise, spec):
    if noise == "ou_biased":
        return np.diag(sigma**2) + spec["amplitude"] ** 2 * np.exp(
            -abs(t[:, None] - t[None, :]) / spec["length_days"]
        )
    return covariance(t, sigma, amplitude=spec["amplitude"], length=spec["length_days"])


def theta_cov(t, sigma, mode, theta, dim, oracle):
    if mode in ["estimated", "legacy_estimated"]:
        a, b, c = theta[dim:]
        assert 0.5 - 1e-12 <= np.exp(a) <= 3 + 1e-12
        assert 1 - 1e-12 <= np.exp(c) <= 120 + 1e-12
        q = np.exp(b) ** 2 if mode == "legacy_estimated" else b
        assert 0 <= q <= 16 + 1e-12
        if mode == "legacy_estimated":
            assert q >= 1e-8 - 1e-18
        return covariance(t, sigma, np.exp(a), np.sqrt(q) * np.median(sigma), np.exp(c))
    return oracle if mode == "oracle" else covariance(t, sigma)


def profiled_nll(t, y, family, shape, c):
    # Independent active-set enumeration for at most two nonnegative coefficients.
    lower = cholesky(c, lower=True)
    x = solve_triangular(lower, design(t, family, shape), lower=True)
    wy = solve_triangular(lower, y, lower=True)
    maximum = np.max(abs(x), axis=0)
    active = maximum > 0
    x = x[:, active] / maximum[active]
    candidates = [np.zeros(x.shape[1])]
    beta = np.linalg.lstsq(x, wy, rcond=None)[0]
    if np.all(beta >= 0):
        candidates.append(beta)
    for j in range(x.shape[1]):
        norm = x[:, j] @ x[:, j]
        b = np.zeros(x.shape[1])
        b[j] = max(0.0, (x[:, j] @ wy) / norm) if norm > 0 else 0.0
        candidates.append(b)
    q = min(float((wy - x @ b) @ (wy - x @ b)) for b in candidates)
    return 0.5 * q + np.log(np.diag(lower)).sum() + 0.5 * len(t) * np.log(2 * np.pi)


def verify(run, allow_partial=False, allow_interrupted=False):
    started = time.perf_counter()
    m = json.loads((run / "manifest.json").read_text())
    cfg = m["config"]
    phase = m["phase"]
    interrupted = m["status"] == "INTERRUPTED"
    assert (
        m["status"] == "COMPLETE"
        or (allow_partial and m["status"] == "PARTIAL_CHECKPOINT")
        or (allow_interrupted and interrupted)
    ), (
        "Interrupted recovery requires explicit --allow-interrupted; this cannot certify cost or full evaluation"
    )
    if interrupted:
        assert m["recovery"]["resource_budget_reconciled"] is False
        assert m["recovery"]["fitting_resume_forbidden"] is True
    for name, h in m["sha256"].items():
        assert sha(run / name) == h, name
    counts = cfg["source_counts_per_seed"]
    expected = [
        {"source_id": sid, "seed": seed, "split": phase}
        for seed in cfg["seeds"]
        for sid in assigned(cfg["namespace"], seed, counts, phase)
    ]
    assert m["source_manifest"] == expected
    records = [
        json.loads((run / n).read_text()) for n in sorted(m["sha256"]) if n.startswith("source-")
    ]
    assert len(records) == len({r["source_id"] for r in records}) == m["completed_sources"]
    assert len(m["sha256"]) == 2 * len(records)
    if m["status"] == "COMPLETE":
        assert len(records) == len(expected)
    assert m["workers"] <= 4 and m["blas_threads"] == 1 and not m["git_dirty"]
    assert m["cumulative_fit_wall_seconds"] < (
        cfg["logical_pilot_wall_time_cap_seconds"]
        if phase == "pilot"
        else cfg["cumulative_phase_fit_budget_seconds"][phase]
    )
    expected_grid = {
        (n, f, c)
        for n in cfg[phase + "_noise"]
        for f in cfg[phase + "_families"]
        for c in cfg[phase + "_conditions"]
    }
    selected, witnesses, endpoints = 0, 0, 0
    failed_legacy_endpoint_metadata = []
    maxerror = 0.0
    fail = Counter()
    valid = Counter()
    for record in records:
        index = next(i for i, s in enumerate(expected) if s["source_id"] == record["source_id"])
        assert record["seed"] == expected[index]["seed"] and record["split"] == phase
        truth = json.loads((run / f"truth/source-{index:04d}.json").read_text())
        assert truth["source_id"] == record["source_id"]
        p = truth["pspl_parameters"]
        g = truth["gaussian_parameters"]
        assert (
            0.15 <= p["u0"] <= 1
            and 60 <= p["t0"] <= 180
            and 8 <= p["t_e"] <= 35
            and 0.3 <= p["f_s"] <= 0.9
        )
        np.testing.assert_allclose(p["f_s"] + p["f_b"], 1.0, atol=1e-14)
        peak = p["f_s"] * ((p["u0"] ** 2 + 2) / np.sqrt(p["u0"] ** 2 * (p["u0"] ** 2 + 4)) - 1)
        np.testing.assert_allclose(
            [truth["amplitude"], g["amplitude"], g["center"], g["baseline"]],
            [peak, peak, p["t0"], 1.0],
            atol=1e-12,
        )
        half = p["t0"] + np.array([-0.5, 0.5]) * truth["fwhm_days"]
        np.testing.assert_allclose(true_mean(half, "pspl", truth), 1 + peak / 2, atol=1e-11)
        np.testing.assert_allclose(true_mean(half, "gaussian", truth), 1 + peak / 2, atol=1e-11)
        hetero = np.asarray(truth["sigma_true"]) * cfg["snr"] / peak
        assert np.all((hetero >= 0.8) & (hetero <= 1.2))
        assert len(record["views"]) == len(expected_grid)
        assert {(v["noise"], v["family"], v["condition"]) for v in record["views"]} == expected_grid
        residuals = {}
        zs = []
        for row in record["views"]:
            t, y, sigma = map(np.asarray, [row["t"], row["flux"], row["sigma"]])
            all_t = np.asarray(truth["t"])
            idx = np.searchsorted(all_t, t)
            np.testing.assert_array_equal(all_t[idx], t)
            assert len(t) == (
                cfg["n_observations"]
                if row["condition"] == "complete"
                else round(0.6 * cfg["n_observations"])
            )
            if row["condition"] == "peak40":
                removed = np.argsort(abs(all_t - truth["pspl_parameters"]["t0"]))[
                    : len(all_t) - len(t)
                ]
                assert set(idx) == set(range(len(all_t))) - set(removed)
            if row["condition"] == "random40":
                key = record["source_id"] + ":mask"
                rng = np.random.default_rng(
                    int.from_bytes(hashlib.sha256(key.encode()).digest()[:16], "big")
                )
                assert set(idx) == set(rng.choice(len(all_t), len(t), replace=False))
            true_sigma = np.asarray(truth["sigma_true"])[idx]
            noise = row["noise"]
            spec = truth["noise_specs"][noise]
            np.testing.assert_allclose(
                sigma, true_sigma * (1 if noise == "white" else cfg["reported_sigma_bias"])
            )
            np.testing.assert_allclose(
                spec["amplitude"],
                0
                if noise == "white"
                else cfg["noise_amplitude_over_median_sigma"] * np.median(truth["sigma_true"]),
            )
            assert spec["length_days"] == cfg["noise_length_days"]
            oracle = true_cov(t, true_sigma, noise, spec)
            additive = y - true_mean(t, row["family"], truth)
            key = noise, row["condition"]
            if key in residuals:
                np.testing.assert_allclose(additive, residuals[key], atol=1e-11)
            else:
                residuals[key] = additive
                if row["condition"] == "complete":
                    zs.append(solve_triangular(cholesky(oracle, lower=True), additive, lower=True))
            # Every subset is exactly the corresponding full-cadence noise, not redrawn.
            full = next(
                v
                for v in record["views"]
                if v["noise"] == noise
                and v["family"] == row["family"]
                and v["condition"] == "complete"
            )
            np.testing.assert_allclose(np.asarray(full["flux"])[idx], y, atol=0, rtol=0)
            h = hashlib.sha256()
            for a in [t, y, sigma]:
                h.update(np.asarray(a, dtype="<f8").tobytes())
            assert h.hexdigest() == row["input_hash"]
            assert set(row["results"]) == set(cfg["methods"])
            for mode, method in row["results"].items():
                assert (
                    method["oracle_only"] == (mode == "oracle")
                    and method["input_hash"] == row["input_hash"]
                )
                valid[mode] += method["valid"]
                bics = {}
                for family, fit in method["fits"].items():
                    fail[mode] += not fit["success"]
                    if fit["nll"] is None:
                        assert fit["bic"] is None and not fit["success"]
                        continue
                    shape, beta = shape_coefficients(t, family, fit["parameters"])
                    phi = fit.get("noise")
                    dim = N_SHAPE[family]
                    if mode in ["estimated", "legacy_estimated"]:
                        c = covariance(
                            t, sigma, phi["sigma_scale"], phi["gp_amplitude"], phi["length_days"]
                        )
                        assert (
                            0.5 - 1e-12 <= phi["sigma_scale"] <= 3 + 1e-12
                            and 1 <= phi["length_days"] <= 120 + 1e-10
                        )
                        relative = phi["gp_amplitude"] / np.median(sigma)
                        assert 0 <= relative <= 4 + 1e-12
                        if mode == "estimated":
                            np.testing.assert_allclose(
                                relative**2, phi["relative_variance"], atol=1e-12
                            )
                    else:
                        c = (
                            oracle
                            if mode == "oracle"
                            else covariance(
                                t, sigma, phi["sigma_scale"] if mode == "scale" else 1.0
                            )
                        )
                    ref, q = point_check(t, y, sigma, family, shape, beta, c, fit["nll"])
                    selected += 1
                    maxerror = max(maxerror, abs(ref - fit["nll"]))
                    if "quadratic" in fit:
                        np.testing.assert_allclose(q, fit["quadratic"], atol=1e-7, rtol=1e-9)
                    count = SIGNAL_COUNT[family] + (
                        3 if mode in ["estimated", "legacy_estimated"] else int(mode == "scale")
                    )
                    bics[family] = 2 * ref + count * np.log(len(t))
                    np.testing.assert_allclose(bics[family], fit["bic"], atol=1e-7, rtol=1e-9)
                    if mode == "scale":
                        parent = row["results"]["diagonal"]["fits"][family]
                        assert (
                            fit["parameters"] == parent["parameters"]
                            and fit["success"] == parent["success"]
                        )
                        n_obs = len(t)
                        scalar = lambda s, q=parent["quadratic"], n=n_obs: (
                            q / (2 * s * s) + n * np.log(s)
                        )
                        search = minimize_scalar(
                            scalar, bounds=(0.5, 3), method="bounded", options={"xatol": 1e-10}
                        )
                        np.testing.assert_allclose(
                            scalar(phi["sigma_scale"]),
                            min(search.fun, scalar(0.5), scalar(3)),
                            atol=1e-7,
                        )
                    elif mode != "legacy_estimated":
                        history = fit["incumbent_nll_history"]
                        points = fit["incumbent_witnesses"]
                        assert fit["full_step_parameters_archived"] is False
                        assert len(history) == fit["incumbent_point_count"] and all(
                            b < a for a, b in pairwise(history)
                        )
                        assert (
                            history[0] == points[0]["nll"]
                            and history[-1] == points[-1]["nll"] == fit["best_saved_feasible_nll"]
                        )
                        assert history[0] == fit["initial_incumbent_nll"]
                        tol = 1e-8 * max(1, abs(history[-1]))
                        np.testing.assert_allclose(tol, fit["incumbent_tolerance"], rtol=1e-14)
                        assert ref <= history[-1] + tol + 1e-8
                        np.testing.assert_allclose(
                            fit["selected_minus_best_feasible"],
                            fit["nll"] - history[-1],
                            atol=1e-12,
                        )
                        for point in points:
                            pc = theta_cov(t, sigma, mode, point["theta"], dim, oracle)
                            point_check(
                                t,
                                y,
                                sigma,
                                family,
                                point["theta"][:dim],
                                point["coefficients"],
                                pc,
                                point["nll"],
                            )
                            witnesses += 1
                        eligible = [
                            s
                            for s in fit["starts"]
                            if s["success"] and s["final_nll"] <= history[-1] + tol
                        ]
                        assert fit["success"] == bool(eligible) and fit["fallback_used"] == (
                            not bool(eligible)
                        )
                        if mode == "estimated":
                            np.testing.assert_allclose(
                                history[0],
                                row["results"]["scale"]["fits"][family]["nll"],
                                atol=1e-7,
                            )
                            initial = points[0]["theta"]
                            np.testing.assert_allclose(
                                initial[:dim],
                                row["results"]["diagonal"]["fits"][family]["shape_theta"],
                                atol=0,
                                rtol=0,
                            )
                            assert initial[dim + 1] == 0
                    for start in fit["starts"]:
                        if mode != "legacy_estimated":
                            assert start["likelihood_evaluations"] <= cfg["maxfun"]
                        else:
                            assert start["actual_objective_calls"] == start["nfev"]
                        for prefix in ["initial", "final"]:
                            theta = start.get(prefix + "_theta")
                            value = start.get(prefix + "_nll")
                            if theta is None or value is None or value >= 1e50:
                                continue
                            cstart = theta_cov(t, sigma, mode, theta, dim, oracle)
                            check = profiled_nll(t, y, family, theta[:dim], cstart)
                            # No independent KKT claim for discarded non-selected states.
                            if (
                                mode == "legacy_estimated"
                                and prefix == "final"
                                and not start["success"]
                            ):
                                # Failed OptimizeResult.fun need not equal fun(OptimizeResult.x),
                                # e.g. an unsuccessful line search. It is solver metadata,
                                # not an independently evaluated physical endpoint NLL.
                                if not np.isclose(check, value, atol=1e-7, rtol=1e-9):
                                    failed_legacy_endpoint_metadata.append(
                                        {
                                            "source_id": record["source_id"],
                                            "view": row["key"],
                                            "family": family,
                                            "solver_message": start["message"],
                                            "solver_reported_fun": value,
                                            "independent_profile_nll_at_returned_x": float(check),
                                            "absolute_difference": float(abs(check - value)),
                                            "selected_fit_density_still_checked": True,
                                        }
                                    )
                            else:
                                np.testing.assert_allclose(
                                    check,
                                    value,
                                    atol=1e-7,
                                    rtol=1e-9,
                                    err_msg=f"{record['source_id']} {row['key']} {mode} {family} {prefix}",
                                )
                            endpoints += 1
                if len(bics) == 3:
                    np.testing.assert_allclose(
                        method["score"],
                        min(bics["constant"], bics["gaussian"]) - bics["pspl"],
                        atol=1e-7,
                    )
                else:
                    assert method["score"] is None
                assert method["valid"] == (
                    len(bics) == 3 and all(f["success"] for f in method["fits"].values())
                )
        for z in zs[1:]:
            np.testing.assert_allclose(z, zs[0], atol=1e-9)
    return {
        "status": "PASS_NUMERICAL_ONLY_RESOURCE_UNRESOLVED" if interrupted else "PASS",
        "resource_budget_verified": False if interrupted else None,
        "fitting_resume_authorized_by_this_verifier": False,
        "phase": phase,
        "independent_sources": len(records),
        "observed_curves": len(records) * len(expected_grid),
        "selected_fit_rows": selected,
        "first_best_witnesses_checked": witnesses,
        "start_states_profiled": endpoints,
        "max_absolute_nll_difference": maxerror,
        "nonconverged_selected_fits": dict(fail),
        "valid_method_sets": dict(valid),
        "scientific_fingerprint": m["scientific_fingerprint"],
        "runtime_seconds": time.perf_counter() - started,
        "failed_legacy_endpoint_solver_metadata_mismatches": failed_legacy_endpoint_metadata,
        "classification_metrics_computed": False,
        "full_intermediate_parameters_verified": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--allow-partial", action="store_true")
    p.add_argument(
        "--allow-interrupted",
        action="store_true",
        help="Check recovered selected fits, explicitly NOT unknown runtime or a complete benchmark",
    )
    a = p.parse_args()
    result = verify(a.run, a.allow_partial, a.allow_interrupted)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
