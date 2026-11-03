"""Refreshed-checksum scientific corruptions and completed-run admission controls."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def write(path, value):
    path.write_text(json.dumps(value, separators=(",", ":")) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    p.add_argument("--owner", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    m = json.loads((a.run / "manifest.json").read_text())
    assert m["phase"] == "pilot" and m["status"] == "COMPLETE"
    root = Path("artifacts/cov06-smoke-controls")
    assert not root.exists()
    root.mkdir()
    started = time.perf_counter()
    results = []
    # A manifest-authorized one-source partial copy makes controls cheap, not a new fit.
    for case in [
        "wrong_bic",
        "wrong_history",
        "wrong_start_theta",
        "paired_flux",
        "oracle_flag",
        "input_hash",
    ]:
        dest = root / case
        dest.mkdir()
        (dest / "truth").mkdir()
        name = "source-0000.json"
        r = json.loads((a.run / name).read_text())
        row = r["views"][0]
        if case == "wrong_bic":
            row["results"]["diagonal"]["fits"]["constant"]["bic"] += 1
        elif case == "wrong_history":
            row["results"]["estimated"]["fits"]["constant"]["incumbent_nll_history"][-1] += 1
        elif case == "wrong_start_theta":
            row["results"]["estimated"]["fits"]["constant"]["starts"][0]["initial_theta"][0] += 0.1
        elif case == "paired_flux":
            r["views"][1]["flux"][0] += 0.01
        elif case == "oracle_flag":
            row["results"]["diagonal"]["oracle_only"] = True
        else:
            row["input_hash"] = "0" * 64
        write(dest / name, r)
        shutil.copyfile(a.run / "truth" / name, dest / "truth" / name)
        note = dict(m)
        note.update(
            status="PARTIAL_CHECKPOINT",
            completed_sources=1,
            sha256={
                f: hashlib.sha256((dest / f).read_bytes()).hexdigest()
                for f in [name, "truth/" + name]
            },
        )
        write(dest / "manifest.json", note)
        output = dest / "unexpected.json"
        done = subprocess.run(
            [
                sys.executable,
                "scripts/verify_covariance06.py",
                str(dest),
                "--allow-partial",
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            timeout=20,
            env=dict(
                os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1"
            ),
            check=False,
        )
        assert done.returncode != 0 and "AssertionError" in done.stderr and not output.exists(), (
            case
        )
        results.append(
            {
                "case": case,
                "detected": True,
                "source_checksum_refreshed": True,
                "diagnostic_tail": done.stderr[-800:],
            }
        )
    for case, owner, needle in [
        ("completed_rerun", a.owner, "Completed run must not be repeated"),
        ("foreign_owner", "deliberately-foreign-owner", "AssertionError"),
    ]:
        done = subprocess.run(
            [
                sys.executable,
                "scripts/run_covariance06.py",
                "--phase",
                "pilot",
                "--output",
                str(a.run),
                "--owner",
                owner,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            env=dict(
                os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1"
            ),
            check=False,
        )
        assert done.returncode != 0 and needle in done.stderr, case
        results.append(
            {
                "case": case,
                "detected": True,
                "no_fitting_started": True,
                "diagnostic_tail": done.stderr[-600:],
            }
        )
    proof = {
        "status": "PASS",
        "cases": results,
        "runtime_seconds": time.perf_counter() - started,
        "no_new_fits": True,
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(proof, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": "PASS",
                "controls": len(results),
                "runtime_seconds": proof["runtime_seconds"],
            }
        )
    )


if __name__ == "__main__":
    main()
