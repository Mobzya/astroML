"""Recover checksum-valid completed/partial outputs without fitting or timer invention."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_LZMA, ZipFile

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--owner", required=True)
    a = p.parse_args()
    session = json.loads(Path("research/session_state.json").read_text())["active_session"]
    assert session["owner_id"] == a.owner and session["work_mode"] == "RECOVERY_ONLY_NO_NEW_FITS"
    run = Path("artifacts/cov06-evaluation-v1")
    backup = Path("artifacts/recovery-20261103-1915")
    m = json.loads((run / "manifest.json").read_text())
    ledger = json.loads((backup / "research/cov06/runner_evaluation_ledger.json").read_text())
    assert ledger["invocation_in_progress"]
    for path, h in m["scientific_file_sha256"].items():
        assert sha(path) == h, path
    prior = json.loads(
        Path("reports/covariance06/evaluation/checkpoint-0176/run_manifest.json").read_text()
    )
    for name, h in prior["sha256"].items():
        assert sha(run / name) == h, name
    complete = []
    partial = []
    hashes = {}
    fit_records = 0
    grid = {
        (n, f, c)
        for n in m["config"]["evaluation_noise"]
        for f in m["config"]["evaluation_families"]
        for c in m["config"]["evaluation_conditions"]
    }
    for receipt in sorted((run / "receipts").glob("source-*.json")):
        note = json.loads(receipt.read_text())
        i = note["index"]
        expected = m["source_manifest"][i]
        assert (
            note["fingerprint"] == m["scientific_fingerprint"]
            and note["source_id"] == expected["source_id"]
        )
        for file, key in [
            (note["source_file"], "source_sha256"),
            (note["truth_file"], "truth_sha256"),
        ]:
            assert sha(run / file) == note[key]
        record = json.loads((run / note["source_file"]).read_text())
        assert (
            record["source_id"] == expected["source_id"]
            and record["seed"] == expected["seed"]
            and record["split"] == "evaluation"
        )
        for row in record["views"]:
            h = hashlib.sha256()
            for field in ["t", "flux", "sigma"]:
                h.update(np.asarray(row[field], dtype="<f8").tobytes())
            assert h.hexdigest() == row["input_hash"]
            for mode, method in row["results"].items():
                assert method["input_hash"] == row["input_hash"] and method["oracle_only"] == (
                    mode == "oracle"
                )
                fit_records += len(method["fits"])
        if note["complete"]:
            assert (
                len(record["views"]) == 18
                and {(r["noise"], r["family"], r["condition"]) for r in record["views"]} == grid
            )
            assert all(set(r["results"]) == set(m["config"]["methods"]) for r in record["views"])
            complete.append(i)
            hashes[note["source_file"]] = note["source_sha256"]
            hashes[note["truth_file"]] = note["truth_sha256"]
        else:
            partial.append(
                {
                    "index": i,
                    "source_id": record["source_id"],
                    "views_saved": len(record["views"]),
                    "saved_modes_per_view": {r["key"]: list(r["results"]) for r in record["views"]},
                    "source_file": note["source_file"],
                    "truth_file": note["truth_file"],
                    "receipt": str(receipt),
                }
            )
    assert complete == list(range(195)) and len(partial) == 1 and partial[0]["index"] == 195
    dest = Path("reports/covariance06/recovery-20261103-1915")
    assert not dest.exists()
    dest.mkdir(parents=True)
    snapshot = backup / "complete195"
    snapshot.mkdir()
    (snapshot / "truth").mkdir()
    for name in hashes:
        os.link(run / name, snapshot / name)
    original_sha = sha(run / "manifest.json")
    m.update(
        status="INTERRUPTED",
        completed_sources=len(complete),
        sha256=hashes,
        recovery={
            "original_manifest_sha256": original_sha,
            "original_manifest_completed_sources": 192,
            "completed_source_receipts_recovered": 195,
            "partial_source_index": 195,
            "original_invocation_final_duration_seconds": None,
            "cumulative_fit_wall_seconds_is_only_observed_lower_bound": True,
            "known_closed_invocations_fit_wall_seconds": sum(
                x["elapsed_seconds"] for x in ledger["invocations"][:-1]
            ),
            "resource_budget_reconciled": False,
            "fitting_resume_forbidden": True,
            "no_inference_or_nonlinear_refit": True,
        },
    )
    save(snapshot / "manifest.json", m)
    index = Path("reports/covariance06/evaluation/recovered-0195")
    subprocess.run(
        [
            sys.executable,
            "scripts/archive_covariance06.py",
            str(snapshot),
            "--label",
            "cov06-evaluation-v1",
            "--destination",
            str(index),
            "--shard-root",
            "reports/covariance06/evaluation-shards",
        ],
        check=True,
    )
    with Path("reports/checks/cov06_recovered_0195_restore.json").open("w") as stream:
        subprocess.run(
            [
                sys.executable,
                "scripts/restore_research_shards.py",
                "--index",
                str(index / "artifacts.json"),
                "--output",
                "artifacts/cov06-recovered-0195-restored",
                "--allow-partial",
            ],
            check=True,
            stdout=stream,
        )
    files = {
        "original/session_state.json": backup / "research/session_state.json",
        "original/runner_evaluation_ledger.json": backup
        / "research/cov06/runner_evaluation_ledger.json",
        "original/run_manifest.json": backup / "artifacts/cov06-evaluation-v1/manifest.json",
        "original/file_inventory.json": backup / "inventory.json",
        "original/system_at_recovery.json": backup / "system.json",
        "partial/source-0195.json": run / "source-0195.json",
        "partial/truth/source-0195.json": run / "truth/source-0195.json",
    }
    files.update({"receipts/" + p.name: p for p in (backup / "receipts").glob("*.json")})
    bundle = dest / "partial_and_original_state.zip"
    with ZipFile(bundle, "w", ZIP_LZMA) as z:
        for name, path in sorted(files.items()):
            z.writestr(name, path.read_bytes())
    with ZipFile(bundle) as z:
        assert len(z.namelist()) == len(files)
        for name, path in files.items():
            assert hashlib.sha256(z.read(name)).hexdigest() == sha(path)
    record = {
        "status": "RECOVERED_DATA_INTEGRITY_ONLY",
        "full_evaluation_complete": False,
        "complete_source_units": 195,
        "complete_curves": 195 * 18,
        "partial_source_units": partial,
        "saved_mean_fit_records_including_partial": fit_records,
        "completed_index": str(index / "artifacts.json"),
        "completed_index_sha256": sha(index / "artifacts.json"),
        "recovery_bundle": str(bundle),
        "recovery_bundle_sha256": sha(bundle),
        "recovery_bundle_files_sha256": {n: sha(path) for n, path in files.items()},
        "observed_cumulative_fit_wall_lower_bound_seconds": ledger["budget_used_seconds"],
        "known_closed_call_fit_wall_seconds": sum(
            x["elapsed_seconds"] for x in ledger["invocations"][:-1]
        ),
        "interrupted_call_final_duration_seconds": None,
        "resource_budget_reconciled": False,
        "original_ledger_in_progress_marker_preserved": True,
        "no_new_fits": True,
        "classification_metrics_computed": False,
    }
    save(dest / "artifacts.json", record)
    print(
        json.dumps(
            {
                k: v
                for k, v in record.items()
                if k not in ["recovery_bundle_files_sha256", "partial_source_units"]
            }
        )
    )


if __name__ == "__main__":
    main()
