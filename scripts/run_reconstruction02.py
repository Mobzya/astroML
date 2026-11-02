"""Bounded resumable R2 generation/fitting; calibration and evaluation are separate."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import resource
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from microlens.inference import fit_models
from microlens.simulation import generate_pair, source_manifest


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(config):
    files = sorted(Path("src").rglob("*.py")) + [
        Path(__file__),
        Path(config),
        Path("research/reconstruction_02_protocol.md"),
    ]
    return hashlib.sha256("".join(digest(p) for p in files).encode()).hexdigest()


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def compute(args):
    source, seed, config = args
    started = time.perf_counter()
    pair = generate_pair(source, snr=config["snr"], n_observations=config["n_observations"])
    views = []
    for family in ("pspl", "gaussian"):
        for condition in config["conditions"]:
            obs = pair.views[family][condition]
            error, fits, score, valid = None, None, None, False
            try:
                fits = fit_models(obs, max_nfev=config["max_nfev"])
                candidate = (
                    min(fits["constant"]["bic"], fits["gaussian"]["bic"]) - fits["pspl"]["bic"]
                )
                if np.isfinite(candidate):
                    score = float(candidate)
                    valid = fits["pspl"]["success"] and fits["gaussian"]["success"]
                else:
                    error = "nonfinite score"
            except (ValueError, RuntimeError, ArithmeticError, np.linalg.LinAlgError) as exc:
                error = f"{type(exc).__name__}: {exc}"
            views.append(
                {
                    "family": family,
                    "condition": condition,
                    "t": obs.t.tolist(),
                    "flux": obs.flux.tolist(),
                    "sigma": obs.sigma.tolist(),
                    "fits": fits,
                    "score": score,
                    "valid": valid,
                    "error": error,
                }
            )
    truth = {
        "source_id": source.source_id,
        "pspl_parameters": pair.truth.pspl_parameters,
        "gaussian_parameters": pair.truth.gaussian_parameters,
    }
    record = {
        "source_id": source.source_id,
        "seed": seed,
        "split": source.split,
        "views": views,
        "runtime_seconds": time.perf_counter() - started,
        "worker_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    return record, truth


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/reconstruction_02.json")
    parser.add_argument("--phase", choices=["pilot", "calibration", "evaluation"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--policy", type=Path)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    fp = fingerprint(args.config)
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS"):
        if os.environ.get(variable) != "1":
            raise SystemExit(f"Set {variable}=1 before launching workers.")
    policy_sha, policy_commit = None, None
    if args.phase == "evaluation":
        if not args.policy:
            raise SystemExit("Evaluation requires a committed frozen calibration policy.")
        subprocess.check_call(
            ["git", "ls-files", "--error-unmatch", str(args.policy)], stdout=subprocess.DEVNULL
        )
        if subprocess.check_output(
            ["git", "status", "--porcelain", "--", str(args.policy)], text=True
        ).strip():
            raise SystemExit("Policy must be committed, not modified.")
        policy = json.loads(args.policy.read_text())
        if policy["scientific_fingerprint"] != fp:
            raise SystemExit("Scientific code/config/protocol changed after calibration freeze.")
        policy_sha = digest(args.policy)
        policy_commit = subprocess.check_output(
            ["git", "log", "-1", "--format=%H", "--", str(args.policy)], text=True
        ).strip()
    sources = []
    if args.phase == "pilot":
        sources = [
            (s, config["pilot_seed"], config)
            for s in source_manifest(
                config["pilot_namespace"],
                config["pilot_seed"],
                {"development": config["pilot_pairs"]},
            )
        ]
    else:
        for seed in config["seeds"]:
            sources += [
                (s, seed, config)
                for s in source_manifest(
                    config["namespace"], seed, config["source_counts_per_seed"]
                )
                if s.split == args.phase
            ]
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "run_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest["scientific_fingerprint"] != fp or manifest["phase"] != args.phase:
            raise SystemExit("Cannot resume with different code/config/phase.")
        if manifest["policy_sha256"] != policy_sha:
            raise SystemExit("Frozen policy changed.")
        for name, checksum in manifest["sha256"].items():
            if digest(output / name) != checksum:
                raise SystemExit(f"Checksum mismatch before resume: {name}")
    else:
        manifest = {
            "phase": args.phase,
            "scientific_fingerprint": fp,
            "code_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True)),
            "created_utc": datetime.now(UTC).isoformat(),
            "policy_sha256": policy_sha,
            "policy_commit": policy_commit,
            "platform": platform.platform(),
            "versions": {p: importlib.metadata.version(p) for p in ["numpy", "scipy"]},
            "workers": config["workers"],
            "blas_threads": 1,
            "sha256": {},
            "runtime_seconds_accumulated": 0.0,
            "completed_pairs": 0,
            "expected_pairs": len(sources),
            "status": "IN_PROGRESS",
        }
    base_runtime = manifest["runtime_seconds_accumulated"]
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=config["workers"]) as pool:
        for offset in range(0, len(sources), config["batch_pairs"]):
            name = f"batch-{offset:05d}.json"
            if name in manifest["sha256"]:
                continue
            if time.perf_counter() - started > config["wall_time_limit_seconds"]:
                manifest["status"] = "PARTIAL"
                atomic_json(manifest_path, manifest)
                raise SystemExit(75)
            batch = list(pool.map(compute, sources[offset : offset + config["batch_pairs"]]))
            # Store privileged generator truth separately from observation-only records.
            atomic_json(output / name, [r for r, _ in batch])
            truth_name = "truth/" + name
            atomic_json(output / truth_name, [r for _, r in batch])
            for file in (name, truth_name):
                manifest["sha256"][file] = digest(output / file)
            manifest["completed_pairs"] += len(batch)
            manifest["runtime_seconds_accumulated"] = base_runtime + time.perf_counter() - started
            atomic_json(manifest_path, manifest)
            print(
                json.dumps(
                    {
                        "phase": args.phase,
                        "completed_pairs": manifest["completed_pairs"],
                        "elapsed_seconds": manifest["runtime_seconds_accumulated"],
                    }
                ),
                flush=True,
            )
    manifest["status"] = "COMPLETE"
    atomic_json(manifest_path, manifest)


if __name__ == "__main__":
    main()
