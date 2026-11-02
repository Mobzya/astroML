"""Validate the weekly dependency graph and bounded schedule; never run research."""

import argparse
import json
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from zoneinfo import ZoneInfo

from dateutil.rrule import rrulestr


def require(condition, message):
    if not condition:
        raise ValueError(message)


def parse_time(value):
    return datetime.fromisoformat(value)


def validate(queue, at):
    rows = queue["tasks"]
    tasks = {t["id"]: t for t in rows}
    require(len(tasks) == len(rows), "duplicate task IDs")
    allowed = {"TODO", "DONE", "IN_PROGRESS", "BLOCKED"}
    visiting, visited = set(), set()

    def visit(key):
        require(key in tasks, f"unknown dependency {key}")
        require(key not in visiting, f"dependency cycle at {key}")
        if key in visited:
            return
        visiting.add(key)
        task = tasks[key]
        require(task["status"] in allowed, f"invalid status {key}")
        for parent in task["depends_on"]:
            visit(parent)
        visiting.remove(key)
        visited.add(key)

    for key in tasks:
        visit(key)
    baseline = json.loads(Path("research/campaigns/baseline_2026-11-02_queue.json").read_text())
    for old in baseline["tasks"]:
        require(tasks.get(old["id"]) == old, f"baseline task changed: {old['id']}")
    campaign = next(c for c in queue["campaigns"] if c["id"] == queue["active_campaign"])
    current = [tasks[key] for key in campaign["task_ids"]]
    require(all(t.get("campaign_id") == campaign["id"] for t in current), "campaign ID mismatch")
    require(len({t["id"] for t in current}) == len(current), "duplicate campaign members")
    running = [t for t in current if t["status"] == "IN_PROGRESS"]
    require(len(running) <= 1, "multiple tasks in progress")
    require(
        queue["current_task_id"] == (running[0]["id"] if running else None), "stale current_task_id"
    )
    for task in running:
        require(
            all(tasks[d]["status"] == "DONE" for d in task["depends_on"]),
            "running before dependencies",
        )
    for task in current:
        if task["status"] == "DONE":
            require(
                all(tasks[d]["status"] == "DONE" for d in task["depends_on"]),
                "DONE before dependencies",
            )
    ordinary = [t for t in current if t.get("kind") != "campaign_finalization"]
    finalizers = [t for t in current if t.get("kind") == "campaign_finalization"]
    require(len(finalizers) == 1, "need one final handoff task")
    final = finalizers[0]
    ready = [
        t
        for t in ordinary
        if t["status"] == "TODO" and all(tasks[d]["status"] == "DONE" for d in t["depends_on"])
    ]
    final_ready = final["status"] == "TODO" and all(
        tasks[d]["status"] == "DONE" for d in final["depends_on"]
    )
    final_due = at >= parse_time(campaign["finalization_start_utc"])
    all_done = all(t["status"] == "DONE" for t in ordinary)
    no_useful_ready = not ready and not running
    if final_ready and (final_due or all_done or no_useful_ready):
        selected = final["id"]
    elif running:
        selected = running[0]["id"]
    elif ready:
        selected = ready[0]["id"]
    elif final["status"] == "IN_PROGRESS":
        selected = final["id"]
    else:
        selected = None
    rule_text = "\n".join(
        line for line in campaign["schedule"].splitlines() if line.startswith(("DTSTART", "RRULE"))
    )
    slots = list(rrulestr(rule_text, tzids={"Europe/Moscow": ZoneInfo("Europe/Moscow")}))
    require(len(slots) == campaign["scheduled_slots"] == 21, "schedule must have21 bounded slots")
    require(all(b - a == timedelta(hours=8) for a, b in pairwise(slots)), "interval is not8h")
    require(
        slots[0].astimezone(UTC) == parse_time(campaign["planned_first_start_utc"]),
        "first slot mismatch",
    )
    require(
        slots[-1].astimezone(UTC) == parse_time(campaign["planned_last_start_utc"]),
        "last slot mismatch",
    )
    require(
        slots[-1].astimezone(UTC) + timedelta(minutes=120)
        == parse_time(campaign["completion_deadline_utc"]),
        "deadline mismatch",
    )
    require(selected is None or tasks[selected]["status"] != "DONE", "selected closed task")
    return {
        "status": "PASS",
        "checked_at_utc": at.isoformat(),
        "campaign_id": campaign["id"],
        "baseline_entries_preserved": len(baseline["tasks"]),
        "campaign_tasks": len(current),
        "current_task_id": queue["current_task_id"],
        "next_ready_task_id": selected,
        "ready_ordinary_tasks": [t["id"] for t in ready],
        "finalization_due": final_due,
        "planned_slots_local": [s.isoformat() for s in slots],
        "first_start_utc": slots[0].astimezone(UTC).isoformat(),
        "last_start_utc": slots[-1].astimezone(UTC).isoformat(),
        "new_scientific_runs_performed_by_validator": 0,
        "scope": "planning/DAG/schedule consistency only; service enablement verified separately",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=Path("research/task_queue.json"))
    parser.add_argument("--at", help="Optional UTC ISO timestamp for schedule validation")
    parser.add_argument(
        "--output", type=Path, default=Path("reports/checks/week_2026-11-03_plan.json")
    )
    args = parser.parse_args()
    result = validate(
        json.loads(args.queue.read_text()), parse_time(args.at) if args.at else datetime.now(UTC)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "planned_slots_local"}, indent=2))


if __name__ == "__main__":
    main()
