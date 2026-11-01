"""Verify PSPL geometry and known blending limits; not a detection benchmark.

References: Paczynski 1986 eqs. 1-5; Wozniak & Paczynski 1997
arXiv:astro-ph/9702194v1 eqs. 8-13. All inputs are deterministic diagnostics.
"""

import argparse
import importlib.metadata
import json
import subprocess
from pathlib import Path

import numpy as np

from microlens.physics import magnification, pspl_flux


def check():
    # Independent computation from the two image positions and radial Jacobians.
    u = np.geomspace(1e-3, 100, 301)
    x_plus = (u + np.sqrt(u * u + 4)) / 2
    x_minus = -1 / x_plus
    dx_plus = (1 + u / np.sqrt(u * u + 4)) / 2
    dx_minus = dx_plus / x_plus**2
    from_images = np.abs(x_plus * dx_plus / u) + np.abs(x_minus * dx_minus / u)
    direct = magnification(u)
    error = float(np.max(np.abs(from_images - direct)))
    np.testing.assert_allclose(from_images, direct, rtol=2e-12)

    cases = []
    scale = 1.5
    t_e = 20.0
    x = np.linspace(-2, 2, 401)
    # Far-wing controls intentionally extend outside the current generator prior.
    for regime, u_values in [
        ("large_u", [3.0, 6.0, 12.0, 24.0]),
        ("small_u_strong_blend", [0.02, 0.01, 0.005, 0.0025]),
    ]:
        discrepancies = []
        for u0 in u_values:
            f_s = 0.1 if regime == "large_u" else u0
            power = 4 if regime == "large_u" else 1
            f_s_new = f_s * scale**power
            t = x * u0 * t_e
            old = pspl_flux(t, u0, 0, t_e, f_s, 1 - f_s)
            new = pspl_flux(t, u0 * scale, 0, t_e / scale, f_s_new, 1 - f_s_new)
            sep = np.sqrt(u0**2 + (t / t_e) ** 2)
            sep_new = np.sqrt((u0 * scale) ** 2 + (t / (t_e / scale)) ** 2)
            if regime == "large_u":
                approx_old, approx_new = 2 * f_s / sep**4, 2 * f_s_new / sep_new**4
            else:
                approx_old, approx_new = f_s / sep, f_s_new / sep_new
            invariance_error = float(np.max(np.abs(approx_old - approx_new)))
            np.testing.assert_allclose(approx_old, approx_new, rtol=2e-12)
            relative = float(np.max(np.abs(old - new)) / np.max(old - 1))
            discrepancies.append(relative)
            cases.append(
                {
                    "regime": regime,
                    "u0": u0,
                    "t_e_days": t_e,
                    "f_s": f_s,
                    "scale": scale,
                    "approx_excess_max_absolute_difference": invariance_error,
                    "exact_flux_max_difference_over_original_peak_excess": relative,
                    "grid_points": len(t),
                }
            )
        if not np.all(np.diff(discrepancies) < 0):
            raise ValueError(f"Expected approach to asymptotic degeneracy failed: {regime}")

    return {
        "status": "PASS",
        "purpose": "deterministic_physics_diagnostics_not_evaluation",
        "independent_simulated_sources": 0,
        "random_data_generated": False,
        "image_jacobian_grid_points": len(u),
        "image_jacobian_max_abs_error": error,
        "scaling_controls": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output exists; preserve it and choose a new file.")
    result = check()
    result["code_sha"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    result["git_dirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True))
    result["numpy_version"] = importlib.metadata.version("numpy")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
