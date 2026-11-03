"""Read-only evidence/queue audit; never start or authorize a scientific runner."""

import argparse
import hashlib
import json
import re
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-paused", action="store_true")
    args = parser.parse_args()
    started = time.perf_counter()
    q = load("research/task_queue.json")
    tasks = {t["id"]: t for t in q["tasks"]}
    baseline = load("research/campaigns/baseline_2026-11-02_queue.json")
    require(all(tasks[t["id"]] == t for t in baseline["tasks"]), "baseline changed")
    ordinary = [
        t
        for t in q["tasks"]
        if t.get("campaign_id") == q["active_campaign"]
        and t.get("kind") != "campaign_finalization"
    ]
    require(not any(t["status"] == "IN_PROGRESS" for t in ordinary), "ordinary task running")
    ready = [
        t["id"]
        for t in ordinary
        if t["status"] == "TODO" and all(tasks[d]["status"] == "DONE" for d in t["depends_on"])
    ]
    require(not ready, "useful ordinary task remains ready")
    require(tasks["W1-COV06-EVAL"]["block_code"] == "BLOCKED_RUNTIME_ACCOUNTING", "wrong gate")
    require(tasks["W1-REAL-AUDIT"]["status"] == "DONE", "independent fallback missing")
    for name in ["W1-COV06-VERIFY", "W1-STRESS-RUN", "W1-SYNTHESIS"]:
        require(tasks[name]["status"] == "TODO", "unfinished science mislabelled")

    root = load("reports/covariance06/artifacts.json")
    require(sha(root["evaluation_index_path"]) == root["evaluation_index_sha256"], "index hash")
    index = load(root["evaluation_index_path"])
    require(index["independent_sources"] == 195, "wrong recovered count")
    require(sha(index["manifest_path"]) == index["manifest_sha256"], "manifest hash")
    manifest = load(index["manifest_path"])
    frozen = manifest["scientific_file_sha256"]
    require(all(sha(p) == expected for p, expected in frozen.items()), "scientific code changed")
    require(sha(root["policy_path"]) == root["policy_sha256"], "policy changed")
    for shard in index["artifacts"]:
        require(sha(shard["path"]) == shard["sha256"], "shard corrupted")
    recovery = load(root["recovery_index_path"])
    require(sha(recovery["recovery_bundle"]) == recovery["recovery_bundle_sha256"], "bundle hash")
    with zipfile.ZipFile(recovery["recovery_bundle"]) as bundle:
        for name, expected in recovery["recovery_bundle_files_sha256"].items():
            require(hashlib.sha256(bundle.read(name)).hexdigest() == expected, "bundle member hash")
    proof = load("reports/checks/cov06_recovered_0195_restore.json")
    require(proof["data_files"] == 390 and proof["status"] == "RESTORED", "restore proof")
    numerical = load("reports/checks/cov06_recovered_0195_numerical_verifier.json")
    require(numerical["selected_fit_rows"] == 52650, "numerical count")
    require(not numerical["resource_budget_verified"], "unknown resource claimed verified")
    require(not numerical["classification_metrics_computed"], "interim metrics")
    ledger = load("research/cov06/runner_evaluation_ledger.json")
    require(ledger["invocation_in_progress"], "lost timer silently closed")

    documents = [
        Path("reports/week_2026-11-03_09_handoff.md"),
        Path("research/external_data_card.md"),
        Path("reports/external_pilot_feasibility.md"),
    ]
    checked_links = 0
    for doc in documents:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", doc.read_text()):
            if target.startswith(("https://", "http://", "#")):
                continue
            require((doc.parent / target.split("#")[0]).is_file(), f"broken link: {target}")
            checked_links += 1
    if args.require_paused:
        confirmation = load("reports/checks/week_handoff_automation_confirmation.json")
        require(confirmation["status"] == "PAUSED_UPDATE_AND_READBACK_CONFIRMED", "pause missing")
        require(confirmation["is_enabled"] is False, "job enabled")
        require(confirmation["same_own_job_and_thread"], "wrong automation")
        require(confirmation["other_automations_modified"] == 0, "other automation changed")
        state = load("research/session_state.json")
        require(state["active_session"] is None and state["status"] == "IDLE", "lease not released")
        require(tasks["W1-HANDOFF"]["status"] == "DONE", "handoff acceptance not closed")
    result = {
        "status": "PASS_EVIDENCE_AND_GATE_RECORDS_ONLY",
        "checked_utc": datetime.now(UTC).isoformat(),
        "resource_budget_certified": False,
        "full_scientific_scope_complete": False,
        "new_fits_or_metric_runs": 0,
        "ordinary_ready_tasks": ready,
        "baseline_entries_unchanged": len(baseline["tasks"]),
        "scientific_file_hashes_checked": len(frozen),
        "immutable_complete_shards_checked": len(index["artifacts"]),
        "partial_bundle_member_hashes_checked": len(recovery["recovery_bundle_files_sha256"]),
        "local_document_links_checked": checked_links,
        "document_hashes": {str(p): sha(p) for p in documents},
        "pause_and_lease_acceptance_required": args.require_paused,
        "runtime_seconds": time.perf_counter() - started,
    }
    Path("reports/checks/week_handoff_verifier.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
