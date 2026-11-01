"""Observation-only diagonal fits. No trained classifier or calibrated threshold yet."""

from dataclasses import dataclass

import numpy as np
from scipy.linalg import cholesky, solve_triangular
from scipy.optimize import least_squares

from .physics import pspl_flux


@dataclass(frozen=True)
class Observations:
    t: np.ndarray
    flux: np.ndarray
    sigma: np.ndarray

    def __post_init__(self):
        arrays = [np.array(v, dtype=float, copy=True) for v in (self.t, self.flux, self.sigma)]
        if any(a.ndim != 1 for a in arrays) or len({len(a) for a in arrays}) != 1:
            raise ValueError("t, flux, sigma must be equal-length 1D arrays")
        if len(arrays[0]) < 6 or not all(np.all(np.isfinite(a)) for a in arrays):
            raise ValueError("at least six finite observations required")
        if np.any(arrays[2] <= 0) or np.ptp(arrays[0]) <= 0:
            raise ValueError("positive errors and nonzero time span required")
        for name, a in zip(("t", "flux", "sigma"), arrays):
            a.setflags(write=False)
            object.__setattr__(self, name, a)


def gaussian_nll(residual, covariance):
    """Full Gaussian negative log likelihood; reject non-SPD C without silent jitter."""
    r, c = np.asarray(residual, float), np.asarray(covariance, float)
    if r.ndim != 1 or c.shape != (r.size, r.size) or r.size == 0:
        raise ValueError("incompatible residual/covariance dimensions")
    if not np.all(np.isfinite(r)) or not np.all(np.isfinite(c)):
        raise ValueError("finite inputs required")
    if not np.allclose(c, c.T, rtol=1e-12, atol=1e-14):
        raise ValueError("covariance must be symmetric")
    lower = cholesky(c, lower=True)
    whitened = solve_triangular(lower, r, lower=True)
    return float(
        0.5
        * (whitened @ whitened + 2 * np.log(lower.diagonal()).sum() + r.size * np.log(2 * np.pi))
    )


def fit_models(obs, max_nfev=600):
    """Fit constant, PSPL, Gaussian. Bounds are demo defaults, not a frozen protocol.

    Nonlinear models use nine deterministic starts and the lowest-loss converged fit.
    If every start fails, return the best finite iterate with success=False.
    BIC is a heuristic score, not a probability of astrophysical origin.
    """
    t, y, sigma = obs.t, obs.flux, obs.sigma
    span = float(np.ptp(t))
    baseline = max(float(np.median(y)), 1e-6)
    amplitude = max(float(np.max(y) - baseline), 1e-6)
    centers = [float(t[np.argmax(y)]), float(np.median(t)), float(np.mean(t))]
    results = {}

    def record(name, params, prediction, success, attempts, converged):
        chi2 = float(np.sum(((y - prediction) / sigma) ** 2))
        nll = 0.5 * (chi2 + np.log(2 * np.pi * sigma**2).sum())
        results[name] = {
            "parameters": list(map(float, params)),
            "chi2": chi2,
            "bic": float(2 * nll + len(params) * np.log(len(t))),
            "success": bool(success),
            "starts": attempts,
            "converged_starts": converged,
        }

    constant = max(float(np.average(y, weights=1 / sigma**2)), 0)
    record("constant", [constant], np.full_like(y, constant), True, 1, 1)

    def gaussian(p):
        b, a, center, width = p
        return b + a * np.exp(-0.5 * ((t - center) / width) ** 2)

    for name in ("pspl", "gaussian"):
        if name == "pspl":
            model = lambda p: pspl_flux(t, *p)
            bounds = (
                [0.01, t.min() - span, span / 1000, 0, 0],
                [3, t.max() + span, span * 2, np.inf, np.inf],
            )
            starts = [
                [u, center, span / 10, baseline / 2, baseline / 2]
                for center in centers
                for u in (0.1, 0.4, 1)
            ]
        else:
            model = gaussian
            bounds = (
                [0, 0, t.min() - span, span / 1000],
                [np.inf, np.inf, t.max() + span, span * 2],
            )
            starts = [
                [baseline, amplitude, center, span * width]
                for center in centers
                for width in (0.03, 0.1, 0.3)
            ]
        fits = [
            least_squares(
                lambda p, model=model: (model(p) - y) / sigma,
                start,
                bounds=bounds,
                max_nfev=max_nfev,
                x_scale="jac",
            )
            for start in starts
        ]
        converged = [f for f in fits if f.success and np.isfinite(f.cost)]
        best = min(converged or fits, key=lambda f: f.cost)
        record(name, best.x, model(best.x), bool(converged), len(fits), len(converged))
    return results
