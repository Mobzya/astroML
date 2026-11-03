"""Sequential bounded evaluation calls with closed-process Git checkpoints.

Operational orchestration only: never changes the frozen fitter/config/policy.
A push/ownership/preflight failure stops the chain, never retries with new data.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path


def call(*args, capture=False):
    return subprocess.run(list(args), check=True, text=True, capture_output=capture)


def save(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, default=Path("artifacts/cov06-evaluation-v1"))
    p.add_argument("--owner", required=True)
    p.add_argument("--calls", type=int, default=1)
    p.add_argument("--session-report", type=Path, required=True)
    p.add_argument("--max-batches", type=int, default=1000)
    a = p.parse_args()
    assert 1 <= a.calls <= 6 and a.max_batches > 0
    for _ in range(a.calls):
        state = json.loads(Path("research/session_state.json").read_text())
        lease = state["active_session"]
        assert (
            lease
            and lease["owner_id"] == a.owner
            and lease["task_id"] == "W1-COV06-EVAL"
            and lease["fitting_pid"] is None
        )
        before = json.loads((a.run / "manifest.json").read_text())
        if before["status"] == "COMPLETE":
            break
        call(
            sys.executable,
            "scripts/preflight_covariance06_resume.py",
            str(a.run),
            "--owner",
            a.owner,
        )
        call(
            sys.executable,
            "scripts/run_covariance06.py",
            "--phase",
            "evaluation",
            "--output",
            str(a.run),
            "--owner",
            a.owner,
            "--max-batches",
            str(a.max_batches),
        )
        m = json.loads((a.run / "manifest.json").read_text())
        n = m["completed_sources"]
        assert n > before["completed_sources"], (
            "No progress: stop and investigate, do not create duplicate data"
        )
        call(
            sys.executable,
            "scripts/checkpoint_covariance06_evaluation.py",
            str(a.run),
            "--owner",
            a.owner,
        )
        now = datetime.now(UTC)
        state = json.loads(Path("research/session_state.json").read_text())
        lease = state["active_session"]
        assert lease and lease["owner_id"] == a.owner and lease["fitting_pid"] is None
        checkpoint = f"EVAL{n}/360independent source clusters durably archived/restored({2 * n}files); cumulative fit-wall{m['cumulative_fit_wall_seconds']:.6f}s/{len(m['invocations'])}calls. Frozen code/policy/versions unchanged. No classification metrics; full scientific verifier pending. Next remaining{360 - n}sources, no completed-source refit."
        lease.update(
            last_checkpoint_utc=now.isoformat(),
            expires_utc=(now + timedelta(hours=3)).isoformat(),
            checkpoint=checkpoint,
        )
        save("research/session_state.json", state)
        q = json.loads(Path("research/task_queue.json").read_text())
        assert (
            q["active_campaign"] == "week-2026-11-03-09" and q["current_task_id"] == "W1-COV06-EVAL"
        )
        task = next(t for t in q["tasks"] if t["id"] == "W1-COV06-EVAL")
        assert task["status"] == "IN_PROGRESS"
        task["checkpoint"] = checkpoint
        save("research/task_queue.json", q)
        for path in [Path("research/decision_log.md"), a.session_report]:
            with path.open("a") as stream:
                stream.write(
                    "\n## "
                    + now.isoformat()
                    + " — sequential closed-call checkpoint\n\n"
                    + checkpoint
                    + " No acceptance/DONE claim from orchestration. Push must succeed before next call.\n"
                )
        for filename, pattern, replacement in [
            (
                "research/STATUS.md",
                r"\d+/360sources сохранены в Git shards,\d+files restored",
                f"{n}/360sources сохранены в Git shards,{2 * n}files restored",
            ),
            (
                "README.md",
                r"\d+/360sources сохранены/восстановлены",
                f"{n}/360sources сохранены/восстановлены",
            ),
        ]:
            doc = Path(filename)
            doc.write_text(re.sub(pattern, replacement, doc.read_text()))
        paths = [
            "README.md",
            "research/STATUS.md",
            "research/session_state.json",
            "research/task_queue.json",
            "research/decision_log.md",
            "research/cov06/runner_evaluation_ledger.json",
            str(a.session_report),
            "reports/covariance06/artifacts.json",
            "reports/covariance06/evaluation_manifest.json",
            f"reports/covariance06/evaluation/checkpoint-{n:04d}",
            "reports/covariance06/evaluation-shards",
            f"reports/checks/cov06_evaluation_restore_{n:04d}.json",
        ]
        call("git", "add", *paths)
        call(
            "git",
            "commit",
            "-m",
            f"research: preserve {n} frozen evaluation sources and closed-call resume checkpoint",
        )
        call("git", "push", "origin", "main")
        head = call("git", "rev-parse", "HEAD", capture=True).stdout.strip()
        remote = call("git", "ls-remote", "origin", "refs/heads/main", capture=True).stdout.split()[
            0
        ]
        assert head == remote, "Remote changed: recheck ownership before any continuation"
        print(
            json.dumps(
                {
                    "checkpoint_pushed": head,
                    "completed_sources": n,
                    "same_frozen_scientific_fingerprint": m["scientific_fingerprint"],
                    "classification_metrics_computed": False,
                }
            ),
            flush=True,
        )
        if m["status"] == "COMPLETE":
            break


if __name__ == "__main__":
    main()
