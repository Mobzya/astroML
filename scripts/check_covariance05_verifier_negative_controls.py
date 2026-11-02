"""Deliberately corrupt copies of calibration data and update their byte checksums.

These controls check scientific verification beyond SHA256 integrity. No fitting,
new sources, evaluation access, or detector changes occur.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    original = Path("artifacts/cov05-calibration-v1a")
    root = Path("artifacts/cov05-verifier-negative-controls")
    if root.exists():
        raise SystemExit("Preserve existing negative controls")
    results = []
    for case in ["wrong_bic", "counterfactual_flux", "oracle_flag"]:
        destination = root / case
        shutil.copytree(original, destination)
        first = destination / "batch-00000.json"
        rows = json.loads(first.read_text())
        if case == "wrong_bic":
            rows[0]["views"][0]["results"]["diagonal"]["fits"]["constant"]["bic"] += 1
        elif case == "counterfactual_flux":
            row = next(
                v for v in rows[0]["views"] if v["family"] == "gaussian" and v["noise"] == "white"
            )
            row["flux"][0] += 0.01
        else:
            rows[0]["views"][0]["results"]["estimated"]["oracle_only"] = True
        first.write_text(json.dumps(rows, indent=2) + "\n")
        manifest_path = destination / "run_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["sha256"][first.name] = hashlib.sha256(first.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
        command = [sys.executable, "scripts/verify_covariance05.py", str(destination)]
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True, env=environment, timeout=60
        )
        detected = completed.returncode != 0 and "AssertionError" in completed.stderr
        results.append(
            {
                "case": case,
                "checksum_refreshed": True,
                "detected": detected,
                "returncode": completed.returncode,
                "verifier_diagnostic_tail": completed.stderr[-1200:],
            }
        )
        if not detected:
            raise RuntimeError(f"Corruption was not detected: {case}")
    output = {
        "status": "PASS",
        "cases": results,
        "new_sources_or_fits": 0,
        "scope": "calibration copies only; positive full verification recorded separately",
    }
    Path("reports/checks/cov05_verifier_negative_controls.json").write_text(
        json.dumps(output, indent=2) + "\n"
    )
    print(json.dumps({"status": "PASS", "detected_cases": len(results)}))


if __name__ == "__main__":
    main()
