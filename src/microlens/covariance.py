"""Development covariance fitter. No frozen detector or performance claim yet.

Latent GP values are marginalized; hyperparameters are optimized. Nonnegative
linear mean coefficients are profiled. Oracle C is accepted only in oracle mode.
"""

import time

import numpy as np
from scipy.linalg import cholesky, solve_triangular
from scipy.optimize import minimize, nnls

from .physics import magnification


def matern32_covariance(t, sigma, scale=1.0, amplitude=0.0, length=12.0):
    t, sigma = np.asarray(t, float), np.asarray(sigma, float)
    if t.ndim != 1 or sigma.shape != t.shape or not np.all(np.isfinite(t)):
        raise ValueError("finite 1D equal-length times/errors required")
    if not np.all(np.isfinite(sigma)) or np.any(sigma <= 0):
        raise ValueError("strictly positive finite errors required")
    if (
        not np.all(np.isfinite([scale, amplitude, length]))
        or scale <= 0
        or amplitude < 0
        or length <= 0
    ):
        raise ValueError("invalid covariance parameters")
    z = np.sqrt(3) * np.abs(t[:, None] - t[None, :]) / length
    return np.diag((scale * sigma) ** 2) + amplitude**2 * (1 + z) * np.exp(-z)


def profile_linear(design, observed_flux, lower):
    """Fixed C=LL^T, exact nonnegative generalized least squares and full NLL."""
    white_design = solve_triangular(lower, design, lower=True)
    white_flux = solve_triangular(lower, observed_flux, lower=True)
    coefficients, norm = nnls(white_design, white_flux)
    if not np.all(np.isfinite(coefficients)) or not np.isfinite(norm):
        raise ValueError("nonfinite NNLS coefficients or residual norm")
    nll = (
        0.5 * norm * norm
        + np.log(np.diag(lower)).sum()
        + 0.5 * len(observed_flux) * np.log(2 * np.pi)
    )
    if not np.isfinite(nll):
        raise ValueError("nonfinite profiled Gaussian NLL")
    return coefficients, float(nll)


def fit_covariance_models(obs, mode="estimated", known_covariance=None, maxiter=120, maxfun=2000):
    """Same mean families/starts, with fixed diagonal, oracle C or joint estimated C.

    Hyperparameters in estimated mode see only obs. Bounds/starts are provisional
    development choices in research/covariance_development_design.md.
    """
    if mode not in ("diagonal", "oracle", "estimated"):
        raise ValueError("unknown noise mode")
    if mode != "oracle" and known_covariance is not None:
        raise ValueError("privileged covariance is forbidden outside oracle mode")
    if mode == "oracle" and known_covariance is None:
        raise ValueError("oracle mode needs an explicitly privileged covariance")
    t, y, sigma = obs.t, obs.flux, obs.sigma
    span, origin = float(np.ptp(t)), float(np.min(t))
    center = float((t[np.argmax(y)] - origin) / span)
    nominal_sigma = float(np.median(sigma))
    fixed_cov = np.diag(sigma**2) if mode == "diagonal" else known_covariance
    fixed_lower = None if mode == "estimated" else cholesky(fixed_cov, lower=True)
    noise_starts = [np.log([1.0, 0.2, 3.0]), np.log([1.0, 1.0, 12.0]), np.log([1.5, 2.0, 40.0])]
    noise_bounds = [(np.log(0.5), np.log(3)), (np.log(1e-4), np.log(4)), (np.log(1), np.log(120))]
    results = {}
    started = time.perf_counter()
    for name in ("constant", "pspl", "gaussian"):
        if name == "constant":
            starts, bounds, count = [[], [], []], [], 1
        elif name == "pspl":
            starts = [
                [np.log(0.2), center, np.log(0.1)],
                [np.log(0.8), center, np.log(0.1)],
                [np.log(0.4), 0.5, np.log(0.2)],
            ]
            bounds = [(np.log(0.01), np.log(3)), (-1.0, 2.0), (np.log(0.001), np.log(2))]
            count = 5
        else:
            starts = [[center, np.log(0.05)], [center, np.log(0.15)], [0.5, np.log(0.2)]]
            bounds = [(-1.0, 2.0), (np.log(0.001), np.log(2))]
            count = 4
        n_shape = len(starts[0])
        cache = {"phi": None, "lower": fixed_lower, "cov": fixed_cov}
        failures = []

        def unpack(theta, name=name):
            if name == "constant":
                return np.ones((len(t), 1))
            if name == "pspl":
                u0, peak, te = np.exp(theta[0]), origin + theta[1] * span, np.exp(theta[2]) * span
                amp = magnification(np.hypot(u0, (t - peak) / te))
            else:
                peak, width = origin + theta[0] * span, np.exp(theta[1]) * span
                amp = np.exp(-0.5 * ((t - peak) / width) ** 2)
            return np.column_stack([amp, np.ones(len(t))])

        def evaluate(theta, n_shape=n_shape, cache=cache, unpack=unpack):
            if mode == "estimated":
                phi = tuple(theta[n_shape:])
                if cache["phi"] != phi:
                    s, a, ell = np.exp(phi)
                    c = matern32_covariance(t, sigma, s, a * nominal_sigma, ell)
                    cache.update(phi=phi, cov=c, lower=cholesky(c, lower=True))
            coeff, nll = profile_linear(unpack(theta[:n_shape]), y, cache["lower"])
            return coeff, nll

        def objective(theta, evaluate=evaluate, failures=failures):
            try:
                return evaluate(theta)[1]
            except (ValueError, RuntimeError, np.linalg.LinAlgError) as exc:
                failures.append(type(exc).__name__)
                return 1e100

        candidates = []
        summaries = []
        if name == "constant" and mode != "estimated":
            candidates.append(([], evaluate([])[1], True))
            summaries.append({"success": True, "nfev": 1, "message": "exact nonnegative GLS"})
        else:
            for initial, noise_initial in zip(starts, noise_starts):
                x = list(initial) + list(noise_initial) if mode == "estimated" else initial
                all_bounds = bounds + noise_bounds if mode == "estimated" else bounds
                opt = minimize(
                    objective,
                    x,
                    method="L-BFGS-B",
                    bounds=all_bounds,
                    options={"maxiter": maxiter, "maxfun": maxfun, "ftol": 1e-10},
                )
                summaries.append(
                    {
                        "success": bool(opt.success and np.isfinite(opt.fun)),
                        "nfev": int(opt.nfev),
                        "message": str(opt.message),
                        "nll": float(opt.fun) if np.isfinite(opt.fun) else None,
                    }
                )
                if np.isfinite(opt.fun) and opt.fun < 1e50 and np.all(np.isfinite(opt.x)):
                    candidates.append((opt.x, float(opt.fun), bool(opt.success)))
        if not candidates:
            results[name] = {
                "success": False,
                "nll": None,
                "bic": None,
                "starts": summaries,
                "numerical_failures": failures,
            }
            continue
        good = [c for c in candidates if c[2]]
        theta, _, success = min(good or candidates, key=lambda c: c[1])
        coefficients, nll = evaluate(theta)
        if name == "constant":
            parameters = [float(coefficients[0])]
        elif name == "pspl":
            parameters = [
                float(np.exp(theta[0])),
                float(origin + theta[1] * span),
                float(np.exp(theta[2]) * span),
                *map(float, coefficients),
            ]
        else:
            parameters = [
                float(coefficients[1]),
                float(coefficients[0]),
                float(origin + theta[0] * span),
                float(np.exp(theta[1]) * span),
            ]
        noise = None
        if mode == "estimated":
            s, a, ell = np.exp(theta[n_shape:])
            noise = {
                "sigma_scale": float(s),
                "gp_amplitude": float(a * nominal_sigma),
                "length_days": float(ell),
            }
        results[name] = {
            "parameters": parameters,
            "noise": noise,
            "nll": nll,
            "bic": float(2 * nll + (count + (3 if mode == "estimated" else 0)) * np.log(len(t))),
            "success": bool(success),
            "starts": summaries,
            "numerical_failures": failures,
            "covariance_condition": float(np.linalg.cond(cache["cov"])),
        }
    available = all(results[n]["bic"] is not None for n in results)
    score = (
        min(results["constant"]["bic"], results["gaussian"]["bic"]) - results["pspl"]["bic"]
        if available
        else None
    )
    return {
        "mode": mode,
        "oracle_only": mode == "oracle",
        "fits": results,
        "score": score,
        "valid": available and all(r["success"] for r in results.values()),
        "runtime_seconds": time.perf_counter() - started,
    }
