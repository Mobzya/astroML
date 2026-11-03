"""Read-only resume audit: frozen files, Python/libraries, hashes, owner and liveness."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
from datetime import UTC, datetime
from pathlib import Path

from run_covariance06 import fingerprint


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    p.add_argument("--owner", required=True)
    a = p.parse_args()
    s = json.loads(Path("research/session_state.json").read_text())
    lease = s["active_session"]
    assert (
        lease
        and lease["owner_id"] == a.owner
        and datetime.fromisoformat(lease["expires_utc"]) > datetime.now(UTC)
    )
    pid = lease.get("fitting_pid")
    if pid:
        proc = Path(f"/proc/{pid}")
        assert not proc.exists(), "Known process present; do not launch another fitting process"
        raise AssertionError(
            "Non-null fitting PID is unresolved; expiry/absence alone does not close an invocation"
        )
    m = json.loads((a.run / "manifest.json").read_text())
    assert m["status"] in ["PARTIAL_CHECKPOINT", "INTERRUPTED"]
    ledger = json.loads(Path(f"research/cov06/runner_{m['phase']}_ledger.json").read_text())
    assert not ledger["invocation_in_progress"], (
        "Unclosed invocation/liveness/runtime requires evidence, not reset"
    )
    assert m["scientific_fingerprint"] == fingerprint()[0]
    assert m["python"] == platform.python_version(), (
        "Python version differs; use recorded interpreter or record BLOCKED"
    )
    assert m["versions"] == {p: importlib.metadata.version(p) for p in ["numpy", "scipy"]}
    assert all(
        os.environ.get(k) == "1"
        for k in ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"]
    )
    for name, h in m["sha256"].items():
        assert hashlib.sha256((a.run / name).read_bytes()).hexdigest() == h
    print(
        json.dumps(
            {
                "status": "PASS",
                "phase": m["phase"],
                "completed_sources": m["completed_sources"],
                "scientific_fingerprint": m["scientific_fingerprint"],
                "python": m["python"],
                "versions": m["versions"],
                "observation_data_generated": False,
                "mutations": False,
            }
        )
    )


if __name__ == "__main__":
    main()
