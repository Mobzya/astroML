"""Check final evidence/link/artifact consistency without new fits or network calls."""

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile


def read(path):
    return json.loads(Path(path).read_text())


def main():
    queue = read("research/task_queue.json")
    # Audit the delivered baseline, independently of later authorized campaigns.
    snapshot = read("research/campaigns/baseline_2026-11-02_queue.json")
    all_tasks = {t["id"]: t for t in queue["tasks"]}
    tasks = {t["id"]: all_tasks[t["id"]] for t in snapshot["tasks"]}
    for historical in snapshot["tasks"]:
        assert tasks[historical["id"]] == historical
    for key, task in tasks.items():
        if key != "SYNTHESIS":
            assert task["status"] == "DONE", key
        assert all(tasks[d]["status"] == "DONE" for d in task["depends_on"])
    r2 = read("reports/reconstruction02/evaluation_summary.json")
    cov = read("reports/covariance05/evaluation_summary.json")
    assert r2["pairs"] == cov["independent_sources"] == 360
    assert not cov["primary"]["full_success_criterion_supported"]
    checks = [
        "cov05_evaluation_verifier",
        "cov05_freeze_audit",
        "reconstruction02_evaluation_verifier",
    ]
    for name in checks:
        assert read(f"reports/checks/{name}.json")["status"] == "PASS"
    assert read("reports/checks/cov05_evaluation_verifier.json")["fit_rows"] == 87480
    assert read("reports/checks/reconstruction02_evaluation_verifier.json")["fit_rows"] == 6480
    restored = read("reports/checks/cov05_complete_restore.json")
    assert restored["completed_sources"] == 360 and restored["verified_data_files"] == 90
    indices = [
        read("reports/reconstruction02/artifacts.json"),
        read("reports/covariance05/artifacts.json"),
    ]
    artifact_count = 0
    for index in indices:
        for artifact in index["artifacts"]:
            assert (
                hashlib.sha256(Path(artifact["path"]).read_bytes()).hexdigest()
                == artifact["sha256"]
            )
            artifact_count += 1
    index = indices[1]
    snapshot = index["evaluation_snapshot"]
    raw = Path(snapshot["path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == snapshot["sha256"]
    manifest = json.loads(raw)
    assert manifest["status"] == "COMPLETE" and manifest["completed_pairs"] == 360
    archived_names = []
    for artifact in index["artifacts"]:
        if artifact["phase"] == "evaluation":
            with ZipFile(artifact["path"]) as archive:
                archived_names += archive.namelist()
    assert len(archived_names) == len(set(archived_names)) == 90
    assert set(archived_names) == set(manifest["sha256"])
    provenance = read("reports/checks/cov05_verification_provenance.json")
    for path, expected in provenance["helper_sha256"].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected, path
    checked = 0
    authoritative = [
        "README.md",
        "defense/manuscript.md",
        "reports/research_handoff.md",
        "research/STATUS.md",
        "research/research_plan.md",
        "research/contributions.md",
        "reports/session_2026-11-02.md",
        "reports/experiment_05.md",
        "reports/reconstruction_02.md",
        "reports/covariance05/REPRODUCE.md",
    ]
    for name in authoritative:
        path = Path(name)
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text()):
            if link.startswith(("http:", "https:", "#")):
                continue
            target = link.split("#", 1)[0]
            assert (path.parent / target).exists(), f"{name}: {link}"
            checked += 1
    output = {
        "status": "PASS",
        "recorded_utc": datetime.now(UTC).isoformat(),
        "local_links_checked": checked,
        "archives_checked": artifact_count,
        "evaluation_data_files": len(archived_names),
        "closed_scientific_tasks": len(tasks) - 1,
        "new_fits": 0,
        "network_calls": 0,
        "scope": "artifact/link/queue/provenance consistency; not a new scientific experiment",
    }
    Path("reports/checks/research_handoff_audit.json").write_text(
        json.dumps(output, indent=2) + "\n"
    )
    print(json.dumps(output))


if __name__ == "__main__":
    main()
