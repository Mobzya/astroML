"""Generate one synthetic illustration; not an evaluation of detector performance."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from microlens.inference import Observations, fit_models
from microlens.physics import pspl_flux


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261101)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output already exists; choose a new directory to preserve prior runs.")
    args.output.mkdir(parents=True)
    started = time.perf_counter()
    rng = np.random.default_rng(args.seed)
    t = np.sort(np.arange(96) * 2.5 + rng.uniform(0, 2.5, 96))
    truth = {"u0": 0.4, "t0": 120.0, "t_e": 20.0, "f_s": 0.7, "f_b": 0.3}
    mean = pspl_flux(t, **truth)
    sigma = 0.04 * rng.uniform(0.8, 1.2, len(t))
    flux = mean + rng.normal(size=len(t)) * sigma
    keep = 58
    masks = {
        "complete": np.ones(96, dtype=bool),
        "random40": np.zeros(96, dtype=bool),
        "peak40": np.ones(96, dtype=bool),
    }
    masks["random40"][rng.choice(96, keep, replace=False)] = True
    # Hidden t0 is allowed ONLY for generating this synthetic intervention.
    masks["peak40"][np.argsort(np.abs(t - truth["t0"]))[: 96 - keep]] = False
    np.savetxt(
        args.output / "observations.csv",
        np.column_stack([t, flux, sigma]),
        delimiter=",",
        header="time_days,flux,sigma",
        comments="",
    )
    (args.output / "truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    np.savetxt(
        args.output / "masks.csv",
        np.column_stack(list(masks.values())).astype(int),
        fmt="%d",
        delimiter=",",
        header=",".join(masks),
        comments="",
    )
    figure, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=True)
    results = {}
    for ax, (name, mask) in zip(axes, masks.items()):
        obs = Observations(t[mask], flux[mask], sigma[mask])
        results[name] = fit_models(obs)
        ax.errorbar(obs.t, obs.flux, yerr=obs.sigma, fmt=".", ms=4, alpha=0.7)
        grid = np.linspace(0, 240, 400)
        ax.plot(grid, pspl_flux(grid, **truth), "--", label="Generator truth (illustration)")
        fit = results[name]["pspl"]
        ax.plot(grid, pspl_flux(grid, *fit["parameters"]), label="PSPL diagonal fit")
        ax.set(title=f"{name}: n={sum(mask)}", xlabel="Time [days]")
    axes[0].set_ylabel("Normalized linear flux")
    axes[-1].legend(fontsize=7)
    figure.suptitle("Synthetic illustration: one source, shared noise; NOT a benchmark")
    figure.tight_layout()
    figure.savefig(args.output / "illustration.png", dpi=150)
    plt.close(figure)
    (args.output / "fits.json").write_text(json.dumps(results, indent=2, allow_nan=False) + "\n")

    def git(*command):
        return subprocess.check_output(["git", *command], text=True).strip()

    manifest = {
        "run_id": args.output.name,
        "purpose": "synthetic_smoke_not_evaluation",
        "independent_sources": 1,
        "seed": args.seed,
        "truth_available_to_inference": False,
        "git_sha": git("rev-parse", "HEAD"),
        "git_dirty": bool(git("status", "--porcelain")),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "versions": {p: importlib.metadata.version(p) for p in ["numpy", "scipy", "matplotlib"]},
        "runtime_seconds": time.perf_counter() - started,
    }
    manifest["sha256"] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(args.output.iterdir())
        if p.is_file()
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
