"""Illustrate first source-ID error in each primary method/class, without refitting.

Selection is deterministic and illustrative. It estimates neither frequency nor
causal mechanism. Only observation data and saved mean fits are plotted; no GP
conditional signal is added to the physical mean.
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from analyze_reconstruction02 import load_records


def prediction(t, family, parameters):
    if family == "constant":
        return np.full(len(t), parameters[0])
    if family == "gaussian":
        baseline, amplitude, center, width = parameters
        return baseline + amplitude * np.exp(-0.5 * ((t - center) / width) ** 2)
    u0, center, te, fs, fb = parameters
    u2 = u0**2 + ((t - center) / te) ** 2
    return fs * (u2 + 2) / np.sqrt(u2 * (u2 + 4)) + fb


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    args = p.parse_args()
    _, records = load_records(args.run)
    policy = json.loads(Path("reports/covariance05/frozen_policy.json").read_text())
    selections = []
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    for ax, (mode, family) in zip(
        axes.flat,
        [
            ("diagonal", "gaussian"),
            ("estimated", "gaussian"),
            ("diagonal", "pspl"),
            ("estimated", "pspl"),
        ],
    ):
        candidates = []
        for record in sorted(records, key=lambda r: r["source_id"]):
            row = next(
                v
                for v in record["views"]
                if (v["noise"], v["condition"], v["family"]) == ("ou_biased", "complete", family)
            )
            result = row["results"][mode]
            threshold = policy["thresholds"][mode]
            positive = bool(
                result["valid"] and threshold is not None and result["score"] >= threshold
            )
            if positive == (family == "gaussian"):
                candidates.append((record, row, result))
        error = "FP" if family == "gaussian" else "miss/reject"
        if not candidates:
            ax.set_title(f"{mode}: {family}; no {error}")
            ax.axis("off")
            selections.append({"mode": mode, "family": family, "error": error, "source_id": None})
            continue
        record, row, result = candidates[0]
        selections.append(
            {
                "mode": mode,
                "family": family,
                "error": error,
                "source_id": record["source_id"],
                "qualifying_sources": len(candidates),
                "score": result["score"],
                "valid": result["valid"],
            }
        )
        t, y, sigma = map(np.asarray, [row["t"], row["flux"], row["sigma"]])
        grid = np.linspace(t.min(), t.max(), 500)
        ax.errorbar(
            t,
            y,
            yerr=sigma,
            fmt=".",
            color="#444444",
            alpha=0.6,
            markersize=3,
            linewidth=0.6,
            label="data / reported sigma",
        )
        for mean, color in [("pspl", "#3266ad"), ("gaussian", "#c76328")]:
            fit = result["fits"][mean]
            if fit["bic"] is not None:
                ax.plot(
                    grid,
                    prediction(grid, mean, fit["parameters"]),
                    color=color,
                    label=f"{mean}, BIC={fit['bic']:.1f}",
                )
        ax.set_title(
            f"{mode}: true {family}, {error}; score={result['score']:.2f}\n"
            f"{record['source_id'].split(':', 1)[1]}"
        )
        ax.set_xlabel("Time [day]")
        ax.set_ylabel("Normalized flux")
        ax.grid(alpha=0.2)
        ax.legend(fontsize=8)
    fig.suptitle(
        "COV05: lexicographically first source error in each category\n"
        "OU / complete; saved mean fits, no GP conditional correction"
    )
    fig.savefig("reports/figures/covariance05_cases.png", dpi=160)
    Path("reports/covariance05/illustrative_cases.json").write_text(
        json.dumps({"selection_rule": __doc__, "cases": selections}, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
