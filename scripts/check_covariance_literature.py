"""Deterministic Gaussian likelihood diagnostics; no classifier evaluation.

Checks GPML equations 2.30/4.17 by an independent SciPy density, a noise-scale
normalization counterexample and a fixed GP signal-absorption illustration.
"""

import argparse
import importlib.metadata
import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.stats import multivariate_normal

from microlens.inference import gaussian_nll
from microlens.physics import pspl_flux


def matern32(t, length):
    distance = np.abs(t[:, None] - t[None, :])
    z = np.sqrt(3) * distance / length
    return (1 + z) * np.exp(-z)


def check():
    t = np.array([0.0, 0.0, 0.2, 1.0, 3.0, 8.0])
    sigma = np.array([0.03, 0.07, 0.1, 0.04, 0.08, 0.02])
    residual = np.array([0.02, -0.04, 0.11, -0.02, 0.05, -0.03])
    references = []
    for length in (0.01, 1.0, 100.0):
        for amplitude in (0.0, 0.1, 1.0):
            c = np.diag(sigma**2) + amplitude**2 * matern32(t, length)
            ours = gaussian_nll(residual, c)
            reference = -multivariate_normal.logpdf(residual, mean=np.zeros(len(t)), cov=c)
            np.testing.assert_allclose(ours, reference, rtol=2e-9, atol=1e-9)
            references.append(
                {
                    "length_days": length,
                    "amplitude": amplitude,
                    "condition_number": float(np.linalg.cond(c)),
                    "abs_nll_error": float(abs(ours - reference)),
                }
            )

    # Analytic scale MLE is v = mean(r^2) = 1, not v -> infinity.
    r = np.array([-1.0, 1.0, -1.0, 1.0])
    scale_control = []
    for v in (0.1, 1.0, 10.0, 100.0):
        scale_control.append(
            {
                "variance": v,
                "full_nll": gaussian_nll(r, v * np.eye(4)),
                "quadratic_only": float(0.5 * np.sum(r * r) / v),
            }
        )
    assert min(scale_control, key=lambda a: a["full_nll"])["variance"] == 1.0
    assert np.all(np.diff([a["quadratic_only"] for a in scale_control]) < 0)

    # A flexible GP can explain a known deterministic event when omitted from the mean.
    # This is a conditional-prediction identity, not evidence of real detector failures.
    time = np.linspace(-40, 40, 64)
    excess = pspl_flux(time, 0.4, 0, 12, 0.7, 0.3) - 1
    k = matern32(time, 8.0)
    absorption = []
    for amplitude in (0.0, 0.1, 0.3, 1.0, 3.0):
        covariance = 0.04**2 * np.eye(len(time)) + amplitude**2 * k
        posterior = amplitude**2 * k @ cho_solve(cho_factor(covariance, lower=True), excess)
        absorption.append(
            {
                "amplitude": amplitude,
                "remaining_mean_norm_fraction": float(
                    np.linalg.norm(excess - posterior) / np.linalg.norm(excess)
                ),
                "full_nll_constant_mean": gaussian_nll(excess, covariance),
            }
        )
    assert (
        absorption[-1]["remaining_mean_norm_fraction"]
        < absorption[0]["remaining_mean_norm_fraction"]
    )
    return {
        "status": "PASS",
        "purpose": "deterministic_likelihood_controls_not_evaluation",
        "independent_random_sources": 0,
        "density_reference_cases": references,
        "scale_normalization_control": scale_control,
        "fixed_signal_absorption_illustration": absorption,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output exists; preserve it and choose a new path.")
    result = check()
    result["code_sha"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    result["git_dirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True))
    result["versions"] = {p: importlib.metadata.version(p) for p in ("numpy", "scipy")}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
