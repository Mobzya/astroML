"""Bounded source-disjoint COV06 development only, with persistent total budget.

No main/calibration/evaluation data or classification metrics are generated.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import resource
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from microlens.cov_simulation import source_views
from microlens.covariance import fit_covariance_models
from microlens.covariance06 import fit_all_practical, input_hash
from microlens.simulation import source_manifest


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    temp.replace(path)


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, default=Path("configs/cov06_development.json"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--check-only", action="store_true")
    p.add_argument(
        "--new-attempt",
        action="store_true",
        help="Explicit recorded new directory after a known-duration failed attempt",
    )
    args = p.parse_args()
    cfg = json.loads(args.config.read_text())
    sources = [
        (s, seed)
        for seed in cfg["seeds"]
        for s in source_manifest(cfg["namespace"], seed, cfg["source_counts_per_seed"])
    ]
    assert all(s.split == "development" for s, _ in sources)
    assert 0 < len(sources) <= cfg["logical_pilot_source_cap"] <= 50
    assert cfg["workers"] == 1 and cfg["logical_pilot_wall_time_cap_seconds"] <= 900
    assert set(cfg["methods"]) == {"diagonal", "scale", "estimated", "legacy_estimated"}
    for variable in ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS"]:
        assert os.environ.get(variable) == "1", f"{variable}=1 required"
    owner_path = Path("artifacts/nov03_session_owner.json")
    owner = json.loads(owner_path.read_text())["owner_id"]
    lease_path = Path("research/session_state.json")

    def assert_lease():
        lease = json.loads(lease_path.read_text())["active_session"]
        assert lease["owner_id"] == owner and lease["task_id"] == "W1-OPT-DEV"
        assert datetime.fromisoformat(lease["expires_utc"]) > datetime.now(UTC)

    assert_lease()
    scientific_files = sorted(Path("src").rglob("*.py")) + [
        Path(__file__),
        args.config,
        Path("research/cov06/optimizer_design.md"),
        Path("requirements-lock.txt"),
    ]
    hashes = {str(f): digest(f) for f in scientific_files}
    fp = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    versions = {p: importlib.metadata.version(p) for p in ["numpy", "scipy"]}
    if args.check_only:
        print(
            json.dumps(
                {
                    "status": "CHECK_ONLY_PASS",
                    "sources": len(sources),
                    "views": len(sources) * 8,
                    "scientific_fingerprint": fp,
                    "created_observation_data": False,
                    "versions": versions,
                }
            )
        )
        return
    ledger_path = Path("research/cov06/development_manifest.json")
    ledger = (
        json.loads(ledger_path.read_text())
        if ledger_path.exists()
        else {
            "logical_pilot_id": cfg["experiment_id"],
            "namespace": cfg["namespace"],
            "budget_used_seconds": 0.0,
            "source_ids_used": [],
            "attempts": [],
        }
    )
    assert ledger["namespace"] == cfg["namespace"]
    assert not ledger.get("invocation_in_progress"), (
        "Previous invocation duration/liveness unresolved; do not reset budget"
    )
    used = float(ledger["budget_used_seconds"])
    remaining = cfg["logical_pilot_wall_time_cap_seconds"] - used
    assert remaining > 30, "Logical pilot budget exhausted"
    manifest_path = args.output / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        assert manifest["scientific_fingerprint"] == fp and manifest["versions"] == versions
        assert manifest["status"] != "COMPLETE", "Do not rerun a completed development pilot"
    else:
        assert not args.output.exists(), "Preserve existing non-run directory"
        assert not ledger["attempts"] or args.new_attempt, "Record explicit new-attempt intent"
        manifest = {
            "purpose": "development_only_no_classification_selection",
            "namespace": cfg["namespace"],
            "scientific_fingerprint": fp,
            "scientific_file_sha256": hashes,
            "versions": versions,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "code_sha": git("rev-parse", "HEAD"),
            "git_dirty": bool(git("status", "--porcelain")),
            "config_sha256": digest(args.config),
            "owner_id": owner,
            "expected_sources": len(sources),
            "views_per_source": 8,
            "workers": 1,
            "blas_threads": 1,
            "completed_sources": 0,
            "status": "IN_PROGRESS",
            "sha256": {},
            "created_utc": datetime.now(UTC).isoformat(),
        }
        assert not manifest["git_dirty"], (
            "Commit/push clean scientific implementation before development data"
        )
    for name, expected in manifest["sha256"].items():
        assert digest(args.output / name) == expected, name
    if manifest_path.exists():
        manifest["completed_sources"] = sum(
            len(record["views"]) == 8 and all(len(v["results"]) == 4 for v in record["views"])
            for file in sorted(args.output.glob("source-*.json"))
            for record in [json.loads(file.read_text())]
        )
    args.output.mkdir(parents=True, exist_ok=True)
    args.output.joinpath("truth").mkdir(exist_ok=True)
    attempt = {
        "output": str(args.output),
        "code_sha": manifest["code_sha"],
        "scientific_fingerprint": fp,
        "started_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": 0.0,
        "status": "IN_PROGRESS",
    }
    ledger["attempts"].append(attempt)
    ledger["invocation_in_progress"] = True
    save(ledger_path, ledger)
    lease = json.loads(lease_path.read_text())
    lease["active_session"]["fitting_pid"] = os.getpid()
    lease["active_session"]["fitting_process_start_ticks"] = (
        Path("/proc/self/stat").read_text().split()[21]
    )
    save(lease_path, lease)
    started = time.perf_counter()
    deadline = started + min(remaining - 15, cfg["supervisor_timeout_seconds"] - 10)

    def progress():
        elapsed = time.perf_counter() - started
        attempt["elapsed_seconds"] = elapsed
        ledger["budget_used_seconds"] = used + elapsed
        manifest["logical_budget_used_seconds"] = ledger["budget_used_seconds"]
        save(manifest_path, manifest)
        save(ledger_path, ledger)

    try:
        save(manifest_path, manifest)
        for index, (source, seed) in enumerate(sources):
            assert_lease()
            name, truth_name = f"source-{index:03d}.json", f"truth/source-{index:03d}.json"
            record = (
                json.loads((args.output / name).read_text())
                if (args.output / name).exists()
                else {
                    "source_id": source.source_id,
                    "seed": seed,
                    "split": "development",
                    "views": [],
                }
            )
            assert record["source_id"] == source.source_id and record["seed"] == seed
            if len(record["views"]) == 8 and all(len(v["results"]) == 4 for v in record["views"]):
                continue
            if time.perf_counter() >= deadline - 30:
                manifest["status"] = "PARTIAL_BUDGET"
                break
            generated, truth = source_views(source, cfg, "development")
            save(args.output / truth_name, truth)
            manifest["sha256"][truth_name] = digest(args.output / truth_name)
            ledger["source_ids_used"] = sorted(set(ledger["source_ids_used"]) | {source.source_id})
            assert len(ledger["source_ids_used"]) <= cfg["logical_pilot_source_cap"]
            for noise, family, condition, obs, _oracle_covariance_not_passed in generated:
                assert_lease()
                key = f"{noise}/{family}/{condition}"
                row = next((v for v in record["views"] if v["key"] == key), None)
                if row is None:
                    row = {
                        "key": key,
                        "noise": noise,
                        "family": family,
                        "condition": condition,
                        "t": obs.t.tolist(),
                        "flux": obs.flux.tolist(),
                        "sigma": obs.sigma.tolist(),
                        "input_hash": input_hash(obs),
                        "results": {},
                    }
                    record["views"].append(row)
                assert row["input_hash"] == input_hash(obs)
                if not all(m in row["results"] for m in ["diagonal", "scale", "estimated"]):
                    row["results"].update(
                        fit_all_practical(obs, cfg["maxiter"], cfg["maxfun"], deadline)
                    )
                    save(args.output / name, record)
                    manifest["sha256"][name] = digest(args.output / name)
                    progress()
                if "legacy_estimated" not in row["results"]:
                    if time.perf_counter() >= deadline - 30:
                        raise TimeoutError("No safe remaining budget for legacy comparator")
                    row["results"]["legacy_estimated"] = fit_covariance_models(
                        obs, mode="estimated", maxiter=cfg["maxiter"], maxfun=cfg["maxfun"]
                    )
                save(args.output / name, record)
                manifest["sha256"][name] = digest(args.output / name)
                progress()
            manifest["completed_sources"] += 1
            progress()
            print(
                json.dumps(
                    {
                        "completed_sources": manifest["completed_sources"],
                        "logical_budget_used_seconds": ledger["budget_used_seconds"],
                    }
                ),
                flush=True,
            )
        if manifest["completed_sources"] == len(sources):
            manifest["status"] = "COMPLETE"
        attempt["status"] = manifest["status"]
    except BaseException as exc:
        manifest["status"] = attempt["status"] = "FAILED"
        attempt["error"] = f"{type(exc).__name__}:{exc}"
        raise
    finally:
        manifest["maximum_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        attempt["ended_utc"] = datetime.now(UTC).isoformat()
        ledger["invocation_in_progress"] = False
        progress()
        lease = json.loads(lease_path.read_text())
        if lease["active_session"] and lease["active_session"]["owner_id"] == owner:
            lease["active_session"]["fitting_pid"] = None
            save(lease_path, lease)
    if manifest["status"] != "COMPLETE":
        raise SystemExit(75)
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "sources": manifest["completed_sources"],
                "budget_used_seconds": ledger["budget_used_seconds"],
            }
        )
    )


if __name__ == "__main__":
    main()
