"""Archive completed COV06 development in compact immutable source shards."""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    args = p.parse_args()
    manifest_raw = (args.run / "manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    assert manifest["status"] == "COMPLETE" and manifest["completed_sources"] == 24
    for name, expected in manifest["sha256"].items():
        assert sha((args.run / name).read_bytes()) == expected
    root = Path("reports/covariance06/development")
    root.mkdir(parents=True, exist_ok=True)
    assert not (root / "artifacts.json").exists(), "Preserve previous archive index"
    sources = sorted(args.run.glob("source-*.json"))
    records = [json.loads(p.read_text()) for p in sources]
    assert len(records) == len({r["source_id"] for r in records}) == 24
    assert all(len(r["views"]) == 8 for r in records)
    index = {
        "purpose": manifest["purpose"],
        "scientific_fingerprint": manifest["scientific_fingerprint"],
        "code_sha": manifest["code_sha"],
        "independent_sources": 24,
        "manifest_path": str(root / "run_manifest.json"),
        "manifest_sha256": sha(manifest_raw),
        "artifacts": [],
    }
    for offset in range(0, len(sources), 4):
        selected = sources[offset : offset + 4]
        path = Path(
            f"reports/examples/cov06-dev-v1-shard-{offset:03d}-{offset + len(selected) - 1:03d}.zip"
        )
        assert not path.exists(), path
        with ZipFile(path, "w", ZIP_DEFLATED) as z:
            for file in selected:
                for name in [file.name, "truth/" + file.name]:
                    z.writestr(name, (args.run / name).read_bytes())
        index["artifacts"].append(
            {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": sha(path.read_bytes()),
                "source_files": [p.name for p in selected],
                "independent_sources": len(selected),
            }
        )
    (root / "run_manifest.json").write_bytes(manifest_raw)
    (root / "artifacts.json").write_text(json.dumps(index, indent=2) + "\n")
    views = [v for r in records for v in r["views"]]
    assert len(views) == 192 and all(len(v["results"]) == 4 for v in views)
    summary = {
        "purpose": manifest["purpose"],
        "independent_sources": 24,
        "views": len(views),
        "fit_rows": sum(len(m["fits"]) for v in views for m in v["results"].values()),
        "logical_pilot_runtime_seconds": manifest["logical_budget_used_seconds"],
        "code_sha": manifest["code_sha"],
        "git_dirty_at_start": manifest["git_dirty"],
        "maximum_rss_kib": manifest["maximum_rss_kib"],
        "methods": {},
        "independent_numerical_verifier": "PENDING_NEXT_TASK",
        "classification_metrics_computed": False,
    }
    for mode in ["diagonal", "scale", "estimated", "legacy_estimated"]:
        methods = [v["results"][mode] for v in views]
        fits = [f for m in methods for f in m["fits"].values()]
        summary["methods"][mode] = {
            "method_sets": len(methods),
            "available_valid_sets": sum(m["valid"] for m in methods),
            "unavailable_fits": sum(f["nll"] is None for f in fits),
            "nonconverged_selected_fits": sum(not f["success"] for f in fits),
            "sum_incremental_elapsed_seconds": sum(m["runtime_seconds"] for m in methods),
        }
    (root / "development_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    lines = [
        "# COV06-A development pilot — 03.11.2026",
        "",
        (
            "Это новый development-only numerical feasibility run, не calibration/evaluation. "
            "Old event-level evaluation закрыта; candidate selection по AUC/FPR не выполнялась."
        ),
        "",
        (
            f"Scientific code `{manifest['code_sha']}`, clean at start={not manifest['git_dirty']}. "
            f"24 независимых source units,3seeds,192 dependent views,2304 selected mean fit rows. "
            f"Runtime {manifest['logical_budget_used_seconds']:.2f}s на1worker/1BLASthread, "
            f"RSS{manifest['maximum_rss_kib']}KiB. Logical pilot cap900s preserved in tracked ledger."
        ),
        "",
        "| Method | Sets | Valid sets | Unavailable means | Nonconverged selected means | Incremental elapsed sum (s) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for mode, s in summary["methods"].items():
        lines.append(
            f"| {mode} | {s['method_sets']} | {s['available_valid_sets']} | {s['unavailable_fits']} | "
            f"{s['nonconverged_selected_fits']} | {s['sum_incremental_elapsed_seconds']:.2f} |"
        )
    lines += [
        "",
        (
            "Scale/estimated share the observed diagonal initializer; their timers are incremental, "
            "not isolated end-to-end cost. Views/classes/masks are not independent repetitions. "
            "Convergence/availability here are implementation diagnostics, not classification performance."
        ),
        "",
        (
            "**Independent numerical verification still PENDING**: next task W1-OPT-VERIFY must "
            "recompute density/KKT/bounds/incumbents/analytic scale/input isolation/corruption controls "
            "before numerical correctness or main readiness is claimed."
        ),
        "",
        (
            "[Raw shards/checksums](covariance06/development/artifacts.json), "
            "[manifest](covariance06/development/run_manifest.json), "
            "[summary](covariance06/development/development_summary.json), "
            "[design](../research/cov06/optimizer_design.md), "
            "[logical budget ledger](../research/cov06/development_manifest.json)."
        ),
        "",
    ]
    Path("reports/cov06_development.md").write_text("\n".join(lines))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
