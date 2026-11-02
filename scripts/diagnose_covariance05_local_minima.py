"""Post-freeze oracle diagnostic of missed feasible likelihood points; no refitting.

For the correct PSPL/Gaussian mean only, generator parameters define a feasible
point. A selected NLL above its NLL proves a missed feasible improvement, not the
size of the gap to the global optimum. Truth is used only by this diagnostic.
Estimated mode uses a feasible Matérn C even on OU data, never OU C as its model.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from analyze_reconstruction02 import load_records
from scipy.stats import multivariate_normal
from verify_covariance05 import clean_flux


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    manifest, records = load_records(args.run)
    truths = {
        r["source_id"]: r
        for f in sorted((args.run / "truth").glob("batch-*.json"))
        for r in json.loads(f.read_text())
    }
    config = json.loads(Path("configs/experiment_05.json").read_text())
    groups = defaultdict(list)
    unavailable = defaultdict(int)
    worst = {}
    for record in records:
        truth = truths[record["source_id"]]
        for row in record["views"]:
            family = row["family"]
            if family == "double_bump":
                continue  # No matching fitted mean family: no feasible-point claim.
            t, y, sigma = map(np.asarray, [row["t"], row["flux"], row["sigma"]])
            idx = [truth["t"].index(v) for v in t]
            true_sigma = np.array(truth["sigma_true"])[idx]
            spec = truth["noise_specs"][row["noise"]]
            pars = truth["pspl_parameters"] if family == "pspl" else truth["gaussian_parameters"]
            center = pars["t0"] if family == "pspl" else pars["center"]
            duration = pars["t_e"] if family == "pspl" else pars["width"]
            assert -1 <= (center - t.min()) / np.ptp(t) <= 2
            assert 0.001 <= duration / np.ptp(t) <= 2
            if family == "pspl":
                assert 0.01 <= pars["u0"] <= 3 and min(pars["f_s"], pars["f_b"]) >= 0
            else:
                assert min(pars["baseline"], pars["amplitude"]) >= 0
            residual = y - clean_flux(t, family, truth)
            d = abs(t[:, None] - t[None, :]) / spec["length_days"]
            matern = (1 + np.sqrt(3) * d) * np.exp(-np.sqrt(3) * d)
            oracle = np.diag(true_sigma**2) + spec["amplitude"] ** 2 * (
                np.exp(-d) if row["noise"] == "ou_biased" else matern
            )
            # s=1 or1/.65, ell12; a_rel>=1e-4 meets the frozen floor for white.
            scale = float(np.median(true_sigma / sigma))
            relative_a = max(1e-4, spec["amplitude"] / np.median(sigma))
            assert 0.5 <= scale <= 3 and 1e-4 <= relative_a <= 4
            assert 1 <= spec["length_days"] <= 120
            estimated = (
                np.diag((scale * sigma) ** 2) + (relative_a * np.median(sigma)) ** 2 * matern
            )
            for mode, c in [
                ("diagonal", np.diag(sigma**2)),
                ("oracle", oracle),
                ("estimated", estimated),
            ]:
                key = "/".join([row["noise"], row["condition"], family, mode])
                selected = row["results"][mode]["fits"][family]
                if selected["nll"] is None:
                    unavailable[key] += 1
                    continue
                candidate = float(-multivariate_normal.logpdf(residual, cov=c))
                gap = selected["nll"] - candidate
                groups[key].append(gap)
                if key not in worst or gap > worst[key]["nll_gap"]:
                    worst[key] = {
                        "source_id": record["source_id"],
                        "nll_gap": gap,
                        "selected_nll": selected["nll"],
                        "feasible_nll": candidate,
                        "selected_success": selected["success"],
                    }
    result = {
        "phase": manifest["phase"],
        "independent_sources": len(records),
        "scientific_fingerprint": manifest["scientific_fingerprint"],
        "scope": __doc__,
        "gap_tolerance": 1e-5,
        "groups": {},
    }
    for key, gaps in groups.items():
        positive = np.array(gaps)[np.array(gaps) > 1e-5]
        result["groups"][key] = {
            "available_fits": len(gaps),
            "unavailable_fits": unavailable[key],
            "missed_feasible_improvement": len(positive),
            "fraction_available": len(positive) / len(gaps),
            "median_positive_nll_gap": float(np.median(positive)) if len(positive) else None,
            "worst": worst[key],
        }
    result["candidate_specification"] = {
        "mean": "generator truth, correct family only; all bounds mechanically checked",
        "covariance": "fixed report diagonal / true oracle / feasible nominal Matérn with floor",
        "no_fit_or_detector_modification": True,
        "ou_truth_not_practical_candidate": True,
        "target_calibration_fpr": config["target_calibration_fpr"],
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {k: v["missed_feasible_improvement"] for k, v in result["groups"].items()}, indent=2
        )
    )


if __name__ == "__main__":
    main()
