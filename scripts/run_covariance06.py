"""COV06 source-resumable runner. Pilot namespace is separate from main data.

One repository-wide nonblocking process lock plus owner lease. Per-source atomic
receipts preserve completed work across calls. Stale unclosed invocations block
rather than assuming expiry proves process death. No classifier selection here.
"""

import argparse
import copy
import fcntl
import hashlib
import importlib.metadata
import json
import multiprocessing
import os
import platform
import resource
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

import microlens.covariance as legacy_module
from microlens.cov_simulation import source_views
from microlens.covariance06 import fit_all_practical, fit_covariance06, input_hash
from microlens.simulation import source_manifest


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, allow_nan=False, separators=(",", ":")) + "\n")
    tmp.replace(path)


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def specification(phase):
    cfg = json.loads(Path("configs/experiment_06.json").read_text())
    if phase == "pilot":
        cfg.update(json.loads(Path("configs/cov06_pilot.json").read_text()))
    counts = cfg["source_counts_per_seed"]
    # Main split assignment always includes BOTH phases before any views.
    sources = [
        (s, seed)
        for seed in cfg["seeds"]
        for s in source_manifest(cfg["namespace"], seed, counts)
        if s.split == phase
    ]
    return cfg, sources


def fingerprint():
    files = sorted(Path("src").rglob("*.py")) + [
        Path("scripts/run_covariance06.py"),
        Path("configs/experiment_06.json"),
        Path("configs/cov06_pilot.json"),
        Path("configs/cov06_stress.json"),
        Path("research/experiment_06_protocol.md"),
        Path("research/cov06_stress_protocol.md"),
        Path("research/cov06/optimizer_design.md"),
        Path("requirements-lock.txt"),
    ]
    hashes = {str(f): sha(f) for f in files}
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(), hashes


def compact(method):
    result = copy.deepcopy(method)
    for fit in result["fits"].values():
        if "incumbent_trace" not in fit:
            continue
        points = fit.pop("incumbent_trace")
        fit.update(
            full_step_parameters_archived=False,
            incumbent_point_count=len(points),
            incumbent_nll_history=[p["nll"] for p in points],
            incumbent_witnesses=points[:1] + (points[-1:] if len(points) > 1 else []),
        )
    return result


def legacy_logged(obs, maxiter, maxfun):
    """Logging-only delegation; never add/reorder objective/solver requests."""
    original = legacy_module.minimize
    starts = []

    def logged(fun, x0, *args, **kwargs):
        record = {
            "initial_theta": list(map(float, x0)),
            "initial_nll": None,
            "actual_objective_calls": 0,
        }

        def observed(x):
            value = fun(x)
            record["actual_objective_calls"] += 1
            if record["initial_nll"] is None and np.array_equal(x, x0):
                record["initial_nll"] = float(value) if np.isfinite(value) else None
            return value

        result = original(observed, x0, *args, **kwargs)
        record.update(
            final_theta=result.x.tolist(),
            final_nll=float(result.fun) if np.isfinite(result.fun) else None,
            nit=int(result.nit),
        )
        starts.append(record)
        return result

    try:
        legacy_module.minimize = logged
        result = legacy_module.fit_covariance_models(
            obs, mode="estimated", maxiter=maxiter, maxfun=maxfun
        )
    finally:
        legacy_module.minimize = original
    assert len(starts) == 9
    for i, family in enumerate(["constant", "pspl", "gaussian"]):
        for j, start in enumerate(result["fits"][family]["starts"]):
            start.update(starts[3 * i + j])
    result["logging_only_solver_delegation"] = True
    result["input_hash"] = input_hash(obs)
    return result


def fit_source(job):
    index, source, seed, cfg, phase, out, fp, deadline = job
    out = Path(out)
    name = f"source-{index:04d}.json"
    file, truth_file, receipt = out / name, out / "truth" / name, out / "receipts" / name
    old = json.loads(receipt.read_text()) if receipt.exists() else None
    if old:
        assert old["fingerprint"] == fp
        assert sha(file) == old["source_sha256"] and sha(truth_file) == old["truth_sha256"]
        record = json.loads(file.read_text())
        if old["complete"]:
            return old
    else:
        assert not file.exists() and not truth_file.exists(), (
            "Unreceipted data: investigate, do not overwrite"
        )
        record = {"source_id": source.source_id, "seed": seed, "split": phase, "views": []}
    assert record["source_id"] == source.source_id and record["seed"] == seed
    generated, truth = source_views(source, cfg, phase)
    if old:
        assert json.loads(truth_file.read_text()) == truth
    else:
        save(truth_file, truth)

    def checkpoint(complete=False):
        save(file, record)
        note = {
            "index": index,
            "source_id": source.source_id,
            "fingerprint": fp,
            "source_file": name,
            "truth_file": "truth/" + name,
            "source_sha256": sha(file),
            "truth_sha256": sha(truth_file),
            "complete": complete,
            "views": len(record["views"]),
            "worker_pid": os.getpid(),
            "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        }
        save(receipt, note)
        return note

    for noise, family, condition, obs, oracle_cov in generated:
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
                {
                    m: compact(r)
                    for m, r in fit_all_practical(
                        obs, cfg["maxiter"], cfg["maxfun"], deadline
                    ).items()
                }
            )
            checkpoint()
        if "legacy_estimated" not in row["results"]:
            if deadline and time.perf_counter() > deadline - 30:
                raise TimeoutError(
                    "Insufficient logical pilot budget for legacy fit; preserve receipt"
                )
            row["results"]["legacy_estimated"] = legacy_logged(obs, cfg["maxiter"], cfg["maxfun"])
            checkpoint()
        if "oracle" not in row["results"]:
            # Explicit separate privileged control. Practical function above has NO truth argument.
            row["results"]["oracle"] = compact(
                fit_covariance06(
                    obs,
                    mode="oracle",
                    known_covariance=oracle_cov,
                    maxiter=cfg["maxiter"],
                    maxfun=cfg["maxfun"],
                    deadline=deadline,
                )
            )
            checkpoint()
    assert len(record["views"]) == len(generated) and all(
        set(v["results"]) == set(cfg["methods"]) for v in record["views"]
    )
    return checkpoint(complete=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--phase", required=True, choices=["pilot", "calibration", "evaluation"])
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--max-batches", type=int, default=1000)
    p.add_argument("--check-only", action="store_true")
    args = p.parse_args()
    assert args.max_batches > 0
    cfg, sources = specification(args.phase)
    fp, hashes = fingerprint()
    versions = {p: importlib.metadata.version(p) for p in ["numpy", "scipy"]}
    lease_path = Path("research/session_state.json")

    def lease_check():
        session = json.loads(lease_path.read_text())
        a = session["active_session"]
        required = {
            "pilot": "W1-COV06-PILOT",
            "calibration": "W1-COV06-CAL",
            "evaluation": "W1-COV06-EVAL",
        }[args.phase]
        assert a and a["owner_id"] == args.owner and a["task_id"] == required
        assert datetime.fromisoformat(a["expires_utc"]) > datetime.now(UTC)
        return session

    lease_check()
    if args.check_only:
        print(
            json.dumps(
                {
                    "status": "CHECK_ONLY_PASS",
                    "phase": args.phase,
                    "sources": len(sources),
                    "source_ids": [s.source_id for s, _ in sources],
                    "fingerprint": fp,
                    "observation_data_generated": False,
                }
            )
        )
        return
    assert all(
        os.environ.get(v) == "1"
        for v in ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"]
    )
    q = json.loads(Path("research/task_queue.json").read_text())
    assert q["active_campaign"] == "week-2026-11-03-09"
    tasks = {t["id"]: t for t in q["tasks"]}
    assert (
        tasks[
            {
                "pilot": "W1-STRESS-PROTOCOL",
                "calibration": "W1-COV06-PILOT",
                "evaluation": "W1-COV06-CAL",
            }[args.phase]
        ]["status"]
        == "DONE"
    )
    policy_hash = None
    if args.phase == "evaluation":
        pp = Path("reports/covariance06/frozen_policy.json")
        policy = json.loads(pp.read_text())
        assert policy["scientific_fingerprint"] == fp and policy["calibration_complete"] is True
        assert git("show", "origin/main:" + str(pp)) == pp.read_text().strip(), (
            "Policy must already be pushed"
        )
        assert not set(policy["source_ids"]) & {s.source_id for s, _ in sources}
        policy_hash = sha(pp)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    lock = Path("artifacts/cov06-fit.lock").open("a+")  # noqa: SIM115 — held for process lifetime
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    ledger_path = Path("research/cov06/runner_" + args.phase + "_ledger.json")
    ledger = (
        json.loads(ledger_path.read_text())
        if ledger_path.exists()
        else {
            "phase": args.phase,
            "namespace": cfg["namespace"],
            "budget_used_seconds": 0.0,
            "invocations": [],
        }
    )
    assert ledger["namespace"] == cfg["namespace"] and not ledger.get("invocation_in_progress"), (
        "Unclosed invocation: investigate liveness/runtime first"
    )
    used = ledger["budget_used_seconds"]
    cap = (
        cfg["logical_pilot_wall_time_cap_seconds"]
        if args.phase == "pilot"
        else cfg["cumulative_phase_fit_budget_seconds"][args.phase]
    )
    assert cap - used > 120, "Insufficient remaining cumulative budget for another source batch"
    path = args.output / "manifest.json"
    if path.exists():
        manifest = json.loads(path.read_text())
        assert manifest["status"] != "COMPLETE", "Completed run must not be repeated"
        assert (
            manifest["scientific_fingerprint"] == fp
            and manifest["versions"] == versions
            and manifest["policy_sha256"] == policy_hash
        )
        assert manifest["config"] == cfg
        assert manifest["owner_namespace"] == cfg["namespace"] and manifest["source_manifest"] == [
            {"source_id": s.source_id, "seed": seed, "split": s.split} for s, seed in sources
        ]
    else:
        assert not args.output.exists(), "Preserve unknown output directory"
        assert not git("status", "--porcelain"), (
            "Commit/push implementation before any new observations"
        )
        assert git("rev-parse", "HEAD") == git("rev-parse", "origin/main"), (
            "Successful code push required"
        )
        manifest = {
            "phase": args.phase,
            "purpose": cfg.get("purpose", "frozen_main_no_tuning"),
            "owner_namespace": cfg["namespace"],
            "scientific_fingerprint": fp,
            "scientific_file_sha256": hashes,
            "code_sha": git("rev-parse", "HEAD"),
            "git_dirty": False,
            "versions": versions,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "workers": cfg["workers"],
            "blas_threads": 1,
            "batch_sources": cfg["batch_sources"],
            "cpu_max": Path("/sys/fs/cgroup/cpu.max").read_text().strip(),
            "config": cfg,
            "policy_sha256": policy_hash,
            "expected_sources": len(sources),
            "source_manifest": [
                {"source_id": s.source_id, "seed": seed, "split": s.split} for s, seed in sources
            ],
            "sha256": {},
            "completed_sources": 0,
            "status": "IN_PROGRESS",
            "created_utc": datetime.now(UTC).isoformat(),
            "invocations": [],
        }
    for name, expected in manifest["sha256"].items():
        assert sha(args.output / name) == expected
    completed = set()
    # A Git restore has manifest-authorized completed files but no ephemeral receipts.
    for index, (source, seed) in enumerate(sources):
        name = f"source-{index:04d}.json"
        receipt = args.output / "receipts" / name
        if name in manifest["sha256"] and not receipt.exists():
            record = json.loads((args.output / name).read_text())
            expected_views = (
                len(cfg[args.phase + "_noise"])
                * len(cfg[args.phase + "_families"])
                * len(cfg[args.phase + "_conditions"])
            )
            assert record["source_id"] == source.source_id and record["seed"] == seed
            assert len(record["views"]) == expected_views and all(
                set(v["results"]) == set(cfg["methods"]) for v in record["views"]
            )
            save(
                receipt,
                {
                    "index": index,
                    "source_id": source.source_id,
                    "fingerprint": fp,
                    "source_file": name,
                    "truth_file": "truth/" + name,
                    "source_sha256": manifest["sha256"][name],
                    "truth_sha256": manifest["sha256"]["truth/" + name],
                    "complete": True,
                    "restored_from_manifest": True,
                },
            )
    for receipt in (args.output / "receipts").glob("source-*.json"):
        note = json.loads(receipt.read_text())
        index = note["index"]
        source, _seed = sources[index]
        assert note["fingerprint"] == fp and note["source_id"] == source.source_id
        assert sha(args.output / note["source_file"]) == note["source_sha256"]
        assert sha(args.output / note["truth_file"]) == note["truth_sha256"]
        if note["complete"]:
            completed.add(index)
            for name, key in [
                (note["source_file"], "source_sha256"),
                (note["truth_file"], "truth_sha256"),
            ]:
                manifest["sha256"][name] = note[key]
    if args.phase == "pilot":
        assert len(sources) <= 12 <= cfg["logical_pilot_source_cap"] <= 50
    args.output.mkdir(exist_ok=True)
    started = time.perf_counter()
    deadline = started + cap - used - 10 if args.phase == "pilot" else None
    call_cap = min(cfg["call_time_limit_seconds"], cap - used)
    invocation = {
        "started_utc": datetime.now(UTC).isoformat(),
        "owner": args.owner,
        "pid": os.getpid(),
        "process_start_ticks": Path("/proc/self/stat").read_text().split()[21],
        "git_sha": git("rev-parse", "HEAD"),
        "elapsed_seconds": 0.0,
        "status": "IN_PROGRESS",
    }
    ledger.update(invocation_in_progress=True)
    ledger["invocations"].append(invocation)
    session = lease_check()
    session["active_session"].update(
        fitting_pid=os.getpid(), fitting_process_start_ticks=invocation["process_start_ticks"]
    )
    save(lease_path, session)

    def progress():
        invocation["elapsed_seconds"] = time.perf_counter() - started
        ledger["budget_used_seconds"] = used + invocation["elapsed_seconds"]
        manifest["cumulative_fit_wall_seconds"] = ledger["budget_used_seconds"]
        manifest["completed_sources"] = len(completed)
        save(ledger_path, ledger)
        save(path, manifest)

    try:
        progress()
        pending = [i for i in range(len(sources)) if i not in completed]
        with ProcessPoolExecutor(
            max_workers=cfg["workers"], mp_context=multiprocessing.get_context("spawn")
        ) as pool:
            for batch_number, offset in enumerate(range(0, len(pending), cfg["batch_sources"])):
                lease_check()
                elapsed = time.perf_counter() - started
                # Admission uses measured preceding batch;120s conservative first-batch reserve.
                reserve = max(120.0, invocation.get("last_batch_wall_seconds", 0.0) * 1.5)
                if batch_number >= args.max_batches or elapsed > call_cap - reserve:
                    manifest["status"] = "PARTIAL_CHECKPOINT"
                    break
                indices = pending[offset : offset + cfg["batch_sources"]]
                before = time.perf_counter()
                jobs = [
                    (i, *sources[i], cfg, args.phase, str(args.output), fp, deadline)
                    for i in indices
                ]
                for result in pool.map(fit_source, jobs):
                    assert result["complete"]
                    completed.add(result["index"])
                    for name, key in [
                        (result["source_file"], "source_sha256"),
                        (result["truth_file"], "truth_sha256"),
                    ]:
                        manifest["sha256"][name] = result[key]
                    manifest["maximum_worker_rss_kib"] = max(
                        manifest.get("maximum_worker_rss_kib", 0), result["maximum_rss_kib"]
                    )
                invocation["last_batch_wall_seconds"] = time.perf_counter() - before
                progress()
                print(
                    json.dumps(
                        {
                            "phase": args.phase,
                            "completed": len(completed),
                            "total": len(sources),
                            "elapsed_seconds": invocation["elapsed_seconds"],
                        }
                    ),
                    flush=True,
                )
        manifest["status"] = "COMPLETE" if len(completed) == len(sources) else manifest["status"]
        if manifest["status"] == "IN_PROGRESS":
            manifest["status"] = "PARTIAL_CHECKPOINT"
        if used + time.perf_counter() - started >= cap:
            manifest["status"] = "PARTIAL_RESOURCE_LIMIT"
        invocation["status"] = manifest["status"]
    except BaseException as exc:
        manifest["status"] = "INTERRUPTED"
        invocation.update(status="INTERRUPTED", error=repr(exc))
        raise
    finally:
        invocation["finished_utc"] = datetime.now(UTC).isoformat()
        ledger["invocation_in_progress"] = False
        progress()
        manifest["invocations"].append(copy.deepcopy(invocation))
        save(path, manifest)
        session = lease_check()
        session["active_session"].update(fitting_pid=None, fitting_process_start_ticks=None)
        save(lease_path, session)
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "completed_sources": len(completed),
                "cumulative_fit_wall_seconds": ledger["budget_used_seconds"],
            }
        )
    )


if __name__ == "__main__":
    main()
