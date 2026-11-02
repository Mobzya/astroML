"""Publish immutable compact shards plus a consistent COV05 recovery manifest.

Reads one atomic manifest snapshot; only files listed in that snapshot are used.
Previously archived batches are never duplicated or rewritten. Each shard holds
at most five saved batches (40 independent sources). No fit or metric changes.
"""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    args = p.parse_args()
    manifest_bytes = (args.run / "run_manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    phase = manifest["phase"]
    root = Path("reports/covariance05")
    index_path = root / "artifacts.json"
    index = json.loads(index_path.read_text())
    previous = [a for a in index["artifacts"] if a.get("phase") == phase and "batch_files" in a]
    covered = {b for a in previous for b in a["batch_files"]}
    for artifact in previous:
        assert sha(Path(artifact["path"]).read_bytes()) == artifact["sha256"]
        assert artifact["scientific_fingerprint"] == manifest["scientific_fingerprint"]
    all_batches = sorted(n for n in manifest["sha256"] if n.startswith("batch-"))
    new = [n for n in all_batches if n not in covered]
    for offset in range(0, len(new), 5):
        batches = new[offset : offset + 5]
        first, last = (
            n.removeprefix("batch-").removesuffix(".json") for n in [batches[0], batches[-1]]
        )
        destination = Path(f"reports/examples/covariance05-{phase}-batches-{first}-{last}.zip")
        if destination.exists():
            raise FileExistsError(destination)
        count = 0
        with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
            for batch in batches:
                for name in [batch, "truth/" + batch]:
                    raw = (args.run / name).read_bytes()
                    assert sha(raw) == manifest["sha256"][name], name
                    archive.writestr(name, raw)
                    if name == batch:
                        count += len(json.loads(raw))
        index["artifacts"].append(
            {
                "phase": phase,
                "path": str(destination),
                "batch_files": batches,
                "independent_sources": count,
                "bytes": destination.stat().st_size,
                "sha256": sha(destination.read_bytes()),
                "scientific_fingerprint": manifest["scientific_fingerprint"],
            }
        )
    saved = {
        b for a in index["artifacts"] if a.get("phase") == phase for b in a.get("batch_files", [])
    }
    assert saved == set(all_batches)
    snapshot = root / f"{phase}_run_manifest.json"
    snapshot.write_bytes(manifest_bytes)
    index[phase + "_snapshot"] = {
        "path": str(snapshot),
        "sha256": sha(manifest_bytes),
        "status": manifest["status"],
        "completed_sources": manifest["completed_pairs"],
        "expected_sources": manifest["expected_pairs"],
        "code_sha": manifest["code_sha"],
        "scientific_fingerprint": manifest["scientific_fingerprint"],
    }
    index["storage_note"] = (
        "GitHub Releases asset upload returned HTTP401 on2026-11-02; "
        "authorized git push works. Compact <=40-source ZIP shards are in Git; "
        "no credential changes or upload-auth bypass attempted."
    )
    index_path.write_text(json.dumps(index, indent=2) + "\n")
    print(json.dumps(index[phase + "_snapshot"], indent=2))


if __name__ == "__main__":
    main()
