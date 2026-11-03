"""Immutable bounded COV06 completed-source checkpoint shards, including partial runs."""

import argparse
import hashlib
import json
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    p.add_argument("--label", required=True)
    p.add_argument("--destination", type=Path, required=True)
    a = p.parse_args()
    assert a.label.replace("-", "").isalnum()
    raw = (a.run / "manifest.json").read_bytes()
    m = json.loads(raw)
    assert m["status"] in ["COMPLETE", "PARTIAL_CHECKPOINT", "INTERRUPTED"]
    assert len(m["sha256"]) == 2 * m["completed_sources"]
    for name, h in m["sha256"].items():
        assert digest((a.run / name).read_bytes()) == h
    sources = sorted(n for n in m["sha256"] if n.startswith("source-"))
    groups = []
    for offset in range(0, len(sources), 4):
        data = BytesIO()
        with ZipFile(data, "w", ZIP_DEFLATED, compresslevel=9) as z:
            for name in sources[offset : offset + 4]:
                for file in [name, "truth/" + name]:
                    z.writestr(file, (a.run / file).read_bytes())
        assert len(data.getvalue()) <= m["config"]["compressed_shard_cap_bytes"]
        groups.append((offset, data.getvalue(), sources[offset : offset + 4]))
    total = sum(len(g[1]) for g in groups)
    assert total <= m["config"]["compressed_phase_cap_bytes"]
    assert not a.destination.exists(), "Never overwrite previous checkpoint evidence"
    a.destination.mkdir(parents=True)
    index = {
        "scientific_fingerprint": m["scientific_fingerprint"],
        "code_sha": m["code_sha"],
        "independent_sources": m["completed_sources"],
        "manifest_path": str(a.destination / "run_manifest.json"),
        "manifest_sha256": digest(raw),
        "artifacts": [],
        "total_compressed_bytes": total,
    }
    for offset, data, names in groups:
        path = a.destination / f"{a.label}-{offset:04d}-{offset + len(names) - 1:04d}.zip"
        path.write_bytes(data)
        index["artifacts"].append(
            {
                "path": str(path),
                "sha256": digest(data),
                "bytes": len(data),
                "source_files": names,
                "independent_sources": len(names),
            }
        )
    (a.destination / "run_manifest.json").write_bytes(raw)
    (a.destination / "artifacts.json").write_text(json.dumps(index, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": "ARCHIVED",
                "sources": len(sources),
                "compressed_bytes": total,
                "destination": str(a.destination),
            }
        )
    )


if __name__ == "__main__":
    main()
