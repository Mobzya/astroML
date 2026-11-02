"""Independent Gaussian-density and fixed-C linear KKT checks for development fits."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.linalg import cholesky, solve_triangular
from scipy.stats import multivariate_normal


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    args = p.parse_args()
    m = json.loads((args.run / "manifest.json").read_text())
    assert m["status"] == "COMPLETE"
    for name, sha in m["sha256"].items():
        assert hashlib.sha256((args.run / name).read_bytes()).hexdigest() == sha
    records = json.loads((args.run / "records.json").read_text())
    truths = {
        (r["source_id"], r["noise"]): r
        for r in json.loads((args.run / "generator_truth.json").read_text())
    }
    maximum, checked, kkt_max = 0.0, 0, 0.0
    for r in records:
        t, y, sigma = map(np.asarray, [r["t"], r["flux"], r["sigma"]])
        truth = truths[r["source_id"], r["noise"]]
        idx = [truth["t"].index(v) for v in t]
        true_c = np.asarray(truth["true_covariance"])[np.ix_(idx, idx)]
        for mode, method in r["results"].items():
            assert method["oracle_only"] == (mode == "oracle")
            for name, fit in method["fits"].items():
                if fit["bic"] is None:
                    continue
                pars = fit["parameters"]
                if mode == "diagonal":
                    c = np.diag(sigma * sigma)
                elif mode == "oracle":
                    c = true_c
                else:
                    noise = fit["noise"]
                    z = np.sqrt(3) * np.abs(t[:, None] - t[None, :]) / noise["length_days"]
                    c = np.diag((noise["sigma_scale"] * sigma) ** 2) + noise[
                        "gp_amplitude"
                    ] ** 2 * (1 + z) * np.exp(-z)
                if name == "constant":
                    design, coeff = np.ones((len(t), 1)), np.array(pars)
                elif name == "gaussian":
                    b, a, center, width = pars
                    design = np.column_stack(
                        [np.exp(-((t - center) ** 2) / (2 * width**2)), np.ones(len(t))]
                    )
                    coeff = np.array([a, b])
                else:
                    u0, peak, te, fs, fb = pars
                    u2 = u0**2 + ((t - peak) / te) ** 2
                    design = np.column_stack([(u2 + 2) / np.sqrt(u2 * (u2 + 4)), np.ones(len(t))])
                    coeff = np.array([fs, fb])
                residual = y - design @ coeff
                ref = -multivariate_normal.logpdf(residual, cov=c)
                np.testing.assert_allclose(ref, fit["nll"], rtol=1e-8, atol=1e-7)
                k = {"constant": 1, "pspl": 5, "gaussian": 4}[name] + (
                    3 if mode == "estimated" else 0
                )
                np.testing.assert_allclose(
                    2 * ref + k * np.log(len(t)), fit["bic"], rtol=1e-8, atol=1e-7
                )
                lower = cholesky(c, lower=True)
                x = solve_triangular(lower, design, lower=True)
                wr = solve_triangular(lower, -residual, lower=True)
                gradient = x.T @ wr
                tolerances = 1e-6 * (1 + np.linalg.norm(x, axis=0) * np.linalg.norm(wr))
                assert np.all(gradient[coeff <= 1e-8] >= -tolerances[coeff <= 1e-8])
                assert np.all(abs(gradient[coeff > 1e-8]) <= tolerances[coeff > 1e-8])
                maximum = max(maximum, abs(ref - fit["nll"]))
                kkt_max = max(
                    kkt_max,
                    float(
                        np.max(
                            np.where(coeff > 1e-8, abs(gradient), np.maximum(-gradient, 0))
                            / (1 + np.linalg.norm(x, axis=0) * np.linalg.norm(wr))
                        )
                    ),
                )
                checked += 1
        if r["noise"] == "white":
            for name in ["constant", "pspl", "gaussian"]:
                np.testing.assert_allclose(
                    r["results"]["diagonal"]["fits"][name]["nll"],
                    r["results"]["oracle"]["fits"][name]["nll"],
                    atol=1e-9,
                )
    print(
        json.dumps(
            {
                "status": "PASS",
                "independent_pairs": m["independent_pairs"],
                "checked_fits": checked,
                "max_absolute_nll_difference": maximum,
                "max_scaled_kkt_violation": kkt_max,
            }
        )
    )


if __name__ == "__main__":
    main()
