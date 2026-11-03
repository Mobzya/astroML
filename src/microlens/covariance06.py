"""COV06-A development implementation; practical inputs are observations only.

The candidate preserves feasible points, separates solver status from fallback,
and profiles a shared scale analytically. No global-optimum/performance claim.
"""

import copy
import hashlib
import time

import numpy as np
from scipy.linalg import cholesky, solve_triangular
from scipy.optimize import minimize, nnls

from .covariance import matern32_covariance
from .physics import magnification
from .simulation import pspl_fwhm


class EvaluationBudget(Exception):
    """Explicit computation stop, never a statistical objective value."""


def input_hash(obs):
    h = hashlib.sha256()
    for array in (obs.t, obs.flux, obs.sigma):
        h.update(np.asarray(array, dtype="<f8").tobytes())
    return h.hexdigest()


def scaled_profile(design, flux, lower):
    """Nonnegative GLS with stable positive column scaling and physical residual."""
    x = solve_triangular(lower, design, lower=True)
    y = solve_triangular(lower, flux, lower=True)
    maximum = np.max(np.abs(x), axis=0)
    active = maximum > 0
    norms = np.ones(x.shape[1])
    norms[active] = maximum[active] * np.sqrt(np.sum((x[:, active] / maximum[active]) ** 2, axis=0))
    if not np.all(np.isfinite(norms[active])) or np.any(norms[active] <= 0):
        raise ValueError("nonfinite positive column norm")
    coefficients = np.zeros(x.shape[1])
    if active.any():
        gamma, norm = nnls(x[:, active] / norms[active], y)
        if not np.all(np.isfinite(gamma)) or not np.isfinite(norm):
            raise ValueError("nonfinite normalized NNLS output")
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            coefficients[active] = gamma / norms[active]
    if not np.all(np.isfinite(coefficients)):
        raise ValueError("nonfinite decoded NNLS coefficients")
    residual = y - x @ coefficients
    quadratic = float(residual @ residual)
    nll = 0.5 * quadratic + np.log(np.diag(lower)).sum() + 0.5 * len(y) * np.log(2 * np.pi)
    if not np.isfinite(nll):
        raise ValueError("nonfinite physical residual/NLL")
    return coefficients, float(nll), quadratic


def gp_covariance(obs, log_scale, relative_variance, log_length):
    if not np.isfinite(relative_variance) or relative_variance < 0:
        raise ValueError("nonnegative finite GP variance required")
    scale, length = np.exp(log_scale), np.exp(log_length)
    amplitude = np.sqrt(relative_variance) * float(np.median(obs.sigma))
    return matern32_covariance(obs.t, obs.sigma, scale, amplitude, length)


def _design(obs, family, shape):
    span, origin = float(np.ptp(obs.t)), float(np.min(obs.t))
    if family == "constant":
        return np.ones((len(obs.t), 1))
    if family == "pspl":
        u0, center, duration = np.exp(shape[0]), origin + shape[1] * span, np.exp(shape[2]) * span
        signal = magnification(np.hypot(u0, (obs.t - center) / duration))
    else:
        center, width = origin + shape[0] * span, np.exp(shape[1]) * span
        signal = np.exp(-0.5 * ((obs.t - center) / width) ** 2)
    return np.column_stack([signal, np.ones(len(obs.t))])


def _starts_and_bounds(obs, family):
    span, origin = float(np.ptp(obs.t)), float(np.min(obs.t))
    center = float((obs.t[np.argmax(obs.flux)] - origin) / span)
    baseline, peak = float(np.median(obs.flux)), float(np.max(obs.flux))
    cadence = np.diff(np.unique(np.sort(obs.t)))
    above = obs.t[obs.flux >= baseline + (peak - baseline) / 2]
    width = (
        float(np.ptp(above) + np.median(cadence)) if peak > baseline and len(above) else 0.1 * span
    )
    fwhm = float(np.clip(width / span, 0.002, 2))
    if family == "constant":
        return [[]], []
    if family == "pspl":
        starts = [
            [np.log(0.2), center, np.log(0.1)],
            [np.log(0.8), center, np.log(0.1)],
            [np.log(0.4), 0.5, np.log(0.2)],
        ]
        starts += [
            [np.log(u), center, np.log(np.clip(fwhm / pspl_fwhm(u, 1), 0.001, 2))]
            for u in [0.15, 0.5, 1.5]
        ]
        bounds = [(np.log(0.01), np.log(3)), (-1.0, 2.0), (np.log(0.001), np.log(2))]
    else:
        starts = [[center, np.log(0.05)], [center, np.log(0.15)], [0.5, np.log(0.2)]]
        starts += [
            [center, np.log(np.clip(fwhm * factor / (2 * np.sqrt(2 * np.log(2))), 0.001, 2))]
            for factor in [0.5, 1.0, 2.0]
        ]
        bounds = [(-1.0, 2.0), (np.log(0.001), np.log(2))]
    return [list(s) for s in dict.fromkeys(tuple(s) for s in starts)], bounds


def _parameters(obs, family, shape, coefficients):
    origin, span = float(np.min(obs.t)), float(np.ptp(obs.t))
    if family == "constant":
        return list(map(float, coefficients))
    if family == "pspl":
        return [
            float(np.exp(shape[0])),
            float(origin + shape[1] * span),
            float(np.exp(shape[2]) * span),
            *map(float, coefficients),
        ]
    return [
        float(coefficients[1]),
        float(coefficients[0]),
        float(origin + shape[0] * span),
        float(np.exp(shape[1]) * span),
    ]


def _fit_mean(
    obs, family, mode, fixed_cov=None, seed=None, maxiter=120, maxfun=2000, deadline=None
):
    started = time.perf_counter()
    shape_starts, shape_bounds = _starts_and_bounds(obs, family)
    dimensions = len(shape_starts[0])
    fixed_lower = cholesky(fixed_cov, lower=True) if fixed_cov is not None else None
    cache = {"phi": None, "lower": fixed_lower, "cov": fixed_cov, "theta": None, "point": None}
    noise_bounds = [(np.log(0.5), np.log(3)), (0.0, 16.0), (0.0, np.log(120))]
    if mode == "estimated":
        if seed is None or seed["nll"] is None:
            return {
                "success": False,
                "optimizer_success": False,
                "fallback_used": False,
                "parameters": None,
                "nll": None,
                "bic": None,
                "starts": [],
                "failure": "unavailable observation-only diagonal initialization",
            }
        s = float(np.clip(np.sqrt(seed["quadratic"] / len(obs.t)), 0.5, 3))
        initials = [
            seed["shape_theta"] + [np.log(s), q, np.log(ell)]
            for q, ell in [(0.0, 12.0), (0.25, 3.0), (1.0, 40.0)]
        ]
        bounds = shape_bounds + noise_bounds
    else:
        initials, bounds = shape_starts, shape_bounds
    best, trace, endpoints, summaries, initial_nlls = None, [], [], [], []
    failures, calls, evaluations = {}, 0, 0
    current = {"evaluations": 0, "index": 0}

    def evaluate(theta, origin):
        nonlocal best, calls, evaluations
        calls += 1
        if deadline is not None and time.perf_counter() >= deadline:
            raise EvaluationBudget("global monotonic deadline")
        theta = np.asarray(theta, float)
        key = tuple(theta)
        if cache["theta"] == key:
            return dict(cache["point"], origin=origin)
        if current["evaluations"] >= maxfun:
            raise EvaluationBudget("per-start likelihood evaluation cap")
        current["evaluations"] += 1
        evaluations += 1
        if not np.all(np.isfinite(theta)) or any(
            x < lo - 1e-12 or x > hi + 1e-12 for x, (lo, hi) in zip(theta, bounds)
        ):
            raise ValueError("nonfinite or out-of-bounds point")
        if mode == "estimated":
            phi = tuple(theta[dimensions:])
            if cache["phi"] != phi:
                c = gp_covariance(obs, *phi)
                cache.update(phi=phi, cov=c, lower=cholesky(c, lower=True))
        coefficients, nll, quadratic = scaled_profile(
            _design(obs, family, theta[:dimensions]), obs.flux, cache["lower"]
        )
        point = {
            "theta": theta.tolist(),
            "coefficients": coefficients.tolist(),
            "nll": nll,
            "quadratic": quadratic,
            "origin": origin,
        }
        cache.update(theta=key, point=point)
        if best is None or nll < best["nll"]:
            best = copy.deepcopy(point)
            trace.append(dict(best, evaluation_number=evaluations))
        return point

    def objective(theta):
        try:
            return evaluate(theta, f"evaluation:{current['index']}")["nll"]
        except EvaluationBudget:
            raise
        except (ValueError, RuntimeError, np.linalg.LinAlgError) as exc:
            reason = f"{type(exc).__name__}:{exc}"
            failures[reason] = failures.get(reason, 0) + 1
            return 1e100

    for index, initial in enumerate(initials):
        current = {"index": index, "evaluations": 0}
        summary = {"index": index, "initial_theta": list(map(float, initial)), "success": False}
        start_time, start_evaluations = time.perf_counter(), evaluations
        try:
            init = evaluate(initial, f"initial:{index}")
            initial_nlls.append(init["nll"])
            summary["initial_nll"] = init["nll"]
            if not initial:
                endpoint, success = init, True
                summary.update(nfev=1, nit=0, message="exact nonnegative GLS")
            else:
                opt = minimize(
                    objective,
                    initial,
                    method="L-BFGS-B",
                    bounds=bounds,
                    options={"maxiter": maxiter, "maxfun": maxfun, "ftol": 1e-10, "gtol": 1e-5},
                )
                endpoint = evaluate(opt.x, f"endpoint:{index}")
                success = bool(
                    opt.success
                    and np.isfinite(opt.fun)
                    and opt.fun < 1e50
                    and np.isclose(opt.fun, endpoint["nll"], rtol=1e-10, atol=1e-8)
                )
                summary["solver_reported_nll"] = float(opt.fun) if np.isfinite(opt.fun) else None
                summary.update(nfev=int(opt.nfev), nit=int(opt.nit), message=str(opt.message))
            summary.update(
                success=success, final_nll=endpoint["nll"], final_theta=endpoint["theta"]
            )
            endpoints.append((endpoint, success))
        except EvaluationBudget as exc:
            summary.update(message=str(exc), budget_exhausted=True)
        except (ValueError, RuntimeError, np.linalg.LinAlgError) as exc:
            reason = f"{type(exc).__name__}:{exc}"
            failures[reason] = failures.get(reason, 0) + 1
            summary.update(message=reason)
        summary.update(
            likelihood_evaluations=evaluations - start_evaluations,
            elapsed_seconds=time.perf_counter() - start_time,
        )
        summaries.append(summary)
        if deadline is not None and time.perf_counter() >= deadline:
            break
    if best is None:
        return {
            "success": False,
            "optimizer_success": False,
            "fallback_used": False,
            "parameters": None,
            "nll": None,
            "bic": None,
            "starts": summaries,
            "numerical_failures": failures,
            "incumbent_trace": [],
        }
    tolerance = 1e-8 * max(1.0, abs(best["nll"]))
    converged = [p for p, ok in endpoints if ok and p["nll"] <= best["nll"] + tolerance]
    selected = min(converged, key=lambda p: p["nll"]) if converged else best
    success = bool(converged)
    shape = selected["theta"][:dimensions]
    noise = None
    c = fixed_cov
    if mode == "estimated":
        logs, q, logell = selected["theta"][dimensions:]
        noise = {
            "sigma_scale": float(np.exp(logs)),
            "relative_variance": float(q),
            "gp_amplitude": float(np.sqrt(q) * np.median(obs.sigma)),
            "length_days": float(np.exp(logell)),
            "length_unidentified_at_zero": q == 0,
        }
        c = gp_covariance(obs, logs, q, logell)
    count = {"constant": 1, "pspl": 5, "gaussian": 4}[family] + (3 if mode == "estimated" else 0)
    return {
        "parameters": _parameters(obs, family, shape, selected["coefficients"]),
        "shape_theta": shape,
        "noise": noise,
        "quadratic": selected["quadratic"],
        "nll": selected["nll"],
        "bic": float(2 * selected["nll"] + count * np.log(len(obs.t))),
        "parameter_count": count,
        "success": success,
        "optimizer_success": success,
        "fallback_used": not success,
        "selected_origin": selected["origin"],
        "initial_incumbent_nll": initial_nlls[0],
        "best_saved_feasible_nll": best["nll"],
        "selected_minus_best_feasible": selected["nll"] - best["nll"],
        "incumbent_tolerance": tolerance,
        "incumbent_trace": trace,
        "starts": summaries,
        "numerical_failures": failures,
        "objective_calls": calls,
        "likelihood_evaluations": evaluations,
        "covariance_condition": float(np.linalg.cond(c)),
        "runtime_seconds": time.perf_counter() - started,
    }


def _method(mode, fits, runtime, obs):
    available = all(f["bic"] is not None for f in fits.values())
    return {
        "mode": mode,
        "oracle_only": mode == "oracle",
        "input_hash": input_hash(obs),
        "fits": fits,
        "score": min(fits["constant"]["bic"], fits["gaussian"]["bic"]) - fits["pspl"]["bic"]
        if available
        else None,
        "valid": available and all(f["success"] for f in fits.values()),
        "runtime_seconds": runtime,
    }


def _fixed(obs, mode, covariance, maxiter, maxfun, deadline):
    started = time.perf_counter()
    fits = {
        f: _fit_mean(
            obs, f, mode, fixed_cov=covariance, maxiter=maxiter, maxfun=maxfun, deadline=deadline
        )
        for f in ["constant", "pspl", "gaussian"]
    }
    return _method(mode, fits, time.perf_counter() - started, obs)


def _scale(obs, diagonal):
    started, fits = time.perf_counter(), {}
    for name, original in diagonal["fits"].items():
        if original["nll"] is None:
            fits[name] = dict(original)
            continue
        s = float(np.clip(np.sqrt(original["quadratic"] / len(obs.t)), 0.5, 3))
        nll = 0.5 * original["quadratic"] / s**2 + len(obs.t) * np.log(s)
        nll += np.log(obs.sigma).sum() + 0.5 * len(obs.t) * np.log(2 * np.pi)
        count = original["parameter_count"] + 1
        fits[name] = {
            "parameters": original["parameters"],
            "shape_theta": original["shape_theta"],
            "noise": {"sigma_scale": s},
            "quadratic": original["quadratic"] / s**2,
            "reported_diagonal_quadratic": original["quadratic"],
            "nll": float(nll),
            "bic": float(2 * nll + count * np.log(len(obs.t))),
            "parameter_count": count,
            "success": original["success"],
            "optimizer_success": original["optimizer_success"],
            "fallback_used": original["fallback_used"],
            "analytic_scale": True,
            "mean_optimizer_source": "shared_diagonal",
            "starts": [],
            "numerical_failures": {},
            "selected_origin": "analytic_scale_of_diagonal",
        }
    result = _method("scale", fits, time.perf_counter() - started, obs)
    result["shared_diagonal_runtime_seconds"] = diagonal["runtime_seconds"]
    return result


def fit_all_practical(obs, maxiter=120, maxfun=2000, deadline=None):
    """No truth/labels/known covariance argument; share diagonal initialization."""
    diagonal = _fixed(obs, "diagonal", np.diag(obs.sigma**2), maxiter, maxfun, deadline)
    scale = _scale(obs, diagonal)
    started = time.perf_counter()
    fits = {
        f: _fit_mean(
            obs,
            f,
            "estimated",
            seed=diagonal["fits"][f],
            maxiter=maxiter,
            maxfun=maxfun,
            deadline=deadline,
        )
        for f in ["constant", "pspl", "gaussian"]
    }
    estimated = _method("estimated", fits, time.perf_counter() - started, obs)
    estimated["shared_diagonal_runtime_seconds"] = diagonal["runtime_seconds"]
    return {"diagonal": diagonal, "scale": scale, "estimated": estimated}


def fit_covariance06(
    obs, mode="estimated", known_covariance=None, maxiter=120, maxfun=2000, deadline=None
):
    if mode not in ["diagonal", "scale", "estimated", "oracle"]:
        raise ValueError("unknown mode")
    if mode != "oracle" and known_covariance is not None:
        raise ValueError("privileged covariance forbidden outside oracle")
    if mode == "oracle":
        if known_covariance is None:
            raise ValueError("oracle requires explicit known covariance")
        return _fixed(obs, mode, np.asarray(known_covariance), maxiter, maxfun, deadline)
    if mode == "estimated":
        return fit_all_practical(obs, maxiter, maxfun, deadline)["estimated"]
    diagonal = _fixed(obs, "diagonal", np.diag(obs.sigma**2), maxiter, maxfun, deadline)
    return diagonal if mode == "diagonal" else _scale(obs, diagonal)
