"""Corrupt development copies with refreshed hashes; no fits or classification."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import multivariate_normal


def main():
    positive = json.loads(Path("reports/checks/cov06_numerical_verifier.json").read_text())
    assert positive["status"] == "PASS"
    root, original = Path("artifacts/cov06-negative-controls"), Path("artifacts/cov06-dev-v1")
    assert not root.exists(), "Preserve existing controls"
    manifest = json.loads((original / "manifest.json").read_text())
    assert manifest["scientific_fingerprint"] == positive["source_fingerprint"]
    started = time.perf_counter()
    results = []
    for case in [
        "wrong_bic",
        "wrong_incumbent_certificate",
        "negative_coefficient",
        "counterfactual_flux",
        "oracle_flag",
    ]:
        destination = root / case
        shutil.copytree(original, destination)
        path = destination / "source-000.json"
        record = json.loads(path.read_text())
        row = record["views"][0]
        method = row["results"]["diagonal"]
        if case == "wrong_bic":
            method["fits"]["constant"]["bic"] += 1
        elif case == "wrong_incumbent_certificate":
            row["results"]["estimated"]["fits"]["constant"]["best_saved_feasible_nll"] += 1
        elif case == "negative_coefficient":
            fit = method["fits"]["constant"]
            fit["parameters"][0] = -0.1
            residual, sigma = np.asarray(row["flux"]) + 0.1, np.asarray(row["sigma"])
            fit["nll"] = float(-multivariate_normal.logpdf(residual, cov=np.diag(sigma**2)))
            fit["quadratic"] = float(np.sum((residual / sigma) ** 2))
            fit["bic"] = 2 * fit["nll"] + np.log(len(residual))
            method["score"] = (
                min(fit["bic"], method["fits"]["gaussian"]["bic"]) - method["fits"]["pspl"]["bic"]
            )
        elif case == "counterfactual_flux":
            changed = next(
                v
                for v in record["views"]
                if v["family"] == "gaussian"
                and v["noise"] == "white"
                and v["condition"] == "complete"
            )
            changed["flux"][0] += 0.01
        else:
            method["oracle_only"] = True
        path.write_text(json.dumps(record, indent=2) + "\n")
        manifest_path = destination / "manifest.json"
        corrupted_manifest = json.loads(manifest_path.read_text())
        corrupted_manifest["sha256"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(corrupted_manifest, indent=2) + "\n")
        output = destination / "unexpected_success.json"
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/verify_covariance06_development.py",
                str(destination),
                "--output",
                str(output),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
            env=dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1"),
        )
        detected = (
            completed.returncode != 0
            and "AssertionError" in completed.stderr
            and not output.exists()
        )
        assert detected, f"{case} was not detected"
        results.append(
            {
                "case": case,
                "checksum_refreshed": True,
                "detected": True,
                "returncode": completed.returncode,
                "diagnostic_tail": completed.stderr[-900:],
            }
        )
    index = json.loads(Path("reports/covariance06/development/artifacts.json").read_text())
    index["artifacts"][0]["sha256"] = "0" * 64
    corrupt_index = root / "corrupt_index.json"
    corrupt_index.write_text(json.dumps(index))
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/restore_research_shards.py",
            "--index",
            str(corrupt_index),
            "--output",
            str(root / "bad_restore"),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode != 0 and "AssertionError" in completed.stderr
    results.append(
        {"case": "archive_checksum", "detected": True, "returncode": completed.returncode}
    )
    result = {
        "status": "PASS",
        "controls": results,
        "runtime_seconds": time.perf_counter() - started,
        "new_sources": 0,
        "new_fits": 0,
        "scope": "fresh development copies only; scientific checks beyond byte integrity",
    }
    Path("reports/checks/cov06_negative_controls.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "detected_controls": len(results),
                "runtime_seconds": result["runtime_seconds"],
            }
        )
    )


if __name__ == "__main__":
    main()
