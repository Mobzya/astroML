"""Bounded resumable COV05 generation/fitting; calibration and evaluation are separate."""

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

from microlens.cov_simulation import source_views
from microlens.covariance import fit_covariance_models
from microlens.simulation import source_manifest


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(config):
    files = sorted(Path("src").rglob("*.py")) + [
        Path(__file__),
        Path(config),
        Path("research/experiment_05_protocol.md"),
    ]
    return hashlib.sha256("".join(digest(p) for p in files).encode()).hexdigest()


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def compute(args):
    source, seed, config, phase = args
    started = time.perf_counter()
    generated, truth = source_views(source, config, phase)
    views = []
    for noise, family, condition, obs, true_c in generated:
        results = {}
        for mode in config["methods"]:
            known = true_c if mode == "oracle" else None
            results[mode] = fit_covariance_models(
                obs, mode, known, config["maxiter"], config["maxfun"]
            )
        views.append(
            {
                "noise": noise,
                "family": family,
                "condition": condition,
                "t": obs.t.tolist(),
                "flux": obs.flux.tolist(),
                "sigma": obs.sigma.tolist(),
                "results": results,
            }
        )
    return (
        {
            "source_id": source.source_id,
            "seed": seed,
            "split": source.split,
            "views": views,
            "runtime_seconds": time.perf_counter() - started,
            "worker_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        },
        truth,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/experiment_05.json")
    parser.add_argument("--phase", choices=["calibration", "evaluation"], required=True)
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
    for seed in config["seeds"]:
        sources += [
            (source, seed, config, args.phase)
            for source in source_manifest(
                config["namespace"], seed, config["source_counts_per_seed"]
            )
            if source.split == args.phase
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
        for offset in range(0, len(sources), config["batch_sources"]):
            name = f"batch-{offset:05d}.json"
            if name in manifest["sha256"]:
                continue
            if time.perf_counter() - started > config["wall_time_limit_seconds"]:
                manifest["status"] = "PARTIAL"
                atomic_json(manifest_path, manifest)
                raise SystemExit(75)
            batch = list(pool.map(compute, sources[offset : offset + config["batch_sources"]]))
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
