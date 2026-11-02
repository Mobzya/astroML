"""Four-source development-only feasibility pilot, never main covariance evaluation."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import time
from pathlib import Path

import numpy as np
from scipy.linalg import cholesky

from microlens.covariance import fit_covariance_models, matern32_covariance
from microlens.inference import Observations
from microlens.simulation import generate_pair, source_manifest


def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Preserve existing development artifacts")
    if os.environ.get("OPENBLAS_NUM_THREADS") != "1" or os.environ.get("OMP_NUM_THREADS") != "1":
        raise SystemExit("Set BLAS and OMP threads to1")
    args.output.mkdir(parents=True)
    records, truths = [], []
    manifest = {
        "purpose": "development_only_covariance_feasibility",
        "namespace": "astroml-cov-development-20261102-v1",
        "code_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True)),
        "seed": 20261112,
        "expected_pairs": 4,
        "status": "IN_PROGRESS",
        "versions": {p: importlib.metadata.version(p) for p in ["numpy", "scipy"]},
    }
    save(args.output / "manifest.json", manifest)
    started = time.perf_counter()
    sources = source_manifest(manifest["namespace"], manifest["seed"], {"development": 4})
    for source in sources:
        pair = generate_pair(source, snr=15.0)
        complete = pair.views["pspl"]["complete"]
        times, sigma_true = complete.t, complete.sigma
        rng = np.random.default_rng(
            int.from_bytes(
                hashlib.sha256((source.source_id + ":cov-noise").encode()).digest()[:8], "big"
            )
        )
        z = rng.normal(size=len(times))
        for noise in ["white", "matern_biased"]:
            amplitude = 0.0 if noise == "white" else 0.8 * float(np.median(sigma_true))
            true_c = matern32_covariance(times, sigma_true, amplitude=amplitude, length=12.0)
            additive = cholesky(true_c, lower=True) @ z
            reported = sigma_true if noise == "white" else 0.65 * sigma_true
            for family in ["pspl", "gaussian"]:
                flux = pair.truth.clean_means[family] + additive
                for condition in ["complete", "peak40"]:
                    mask = pair.truth.masks[condition]
                    obs = Observations(times[mask], flux[mask], reported[mask])
                    row = {
                        "source_id": source.source_id,
                        "noise": noise,
                        "family": family,
                        "condition": condition,
                        "t": obs.t.tolist(),
                        "flux": obs.flux.tolist(),
                        "sigma": obs.sigma.tolist(),
                        "results": {},
                    }
                    for mode in ["diagonal", "oracle", "estimated"]:
                        if time.perf_counter() - started > 900:
                            manifest["status"] = "PARTIAL_BUDGET"
                            save(args.output / "manifest.json", manifest)
                            raise SystemExit(75)
                        known = true_c[np.ix_(mask, mask)] if mode == "oracle" else None
                        row["results"][mode] = fit_covariance_models(obs, mode, known)
                        print(
                            json.dumps(
                                {
                                    "source": source.source_id,
                                    "noise": noise,
                                    "family": family,
                                    "condition": condition,
                                    "mode": mode,
                                    "elapsed_seconds": time.perf_counter() - started,
                                }
                            ),
                            flush=True,
                        )
                    records.append(row)
                    save(args.output / "records.json", records)
            truths.append(
                {
                    "source_id": source.source_id,
                    "noise": noise,
                    "true_covariance": true_c.tolist(),
                    "t": times.tolist(),
                    "pspl_parameters": pair.truth.pspl_parameters,
                }
            )
            save(args.output / "generator_truth.json", truths)
    manifest.update(
        status="COMPLETE",
        runtime_seconds=time.perf_counter() - started,
        source_ids=[s.source_id for s in sources],
        independent_pairs=len(sources),
        observation_views=len(records),
        method_sets=sum(len(r["results"]) for r in records),
        sha256={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in args.output.iterdir()
            if p.name != "manifest.json"
        },
    )
    save(args.output / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
