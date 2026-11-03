"""Immutable bounded COV06 completed-source checkpoint shards, including partial runs."""

import argparse
import hashlib
import json
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_LZMA, ZipFile, ZipInfo


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    p.add_argument("--label", required=True)
    p.add_argument("--destination", type=Path, required=True)
    p.add_argument(
        "--shard-root", type=Path, help="Reuse checked immutable source shards across checkpoints"
    )
    a = p.parse_args()
    assert a.label.replace("-", "").isalnum()
    raw = (a.run / "manifest.json").read_bytes()
    m = json.loads(raw)
    assert m["status"] in ["COMPLETE", "PARTIAL_CHECKPOINT", "INTERRUPTED"]
    assert len(m["sha256"]) == 2 * m["completed_sources"]
    for name, h in m["sha256"].items():
        assert digest((a.run / name).read_bytes()) == h
    sources = sorted(n for n in m["sha256"] if n.startswith("source-"))
    assert not a.destination.exists(), "Never overwrite previous checkpoint evidence"
    shard_root = a.shard_root or a.destination
    groups = []
    for offset in range(0, len(sources), 4):
        names = sources[offset : offset + 4]
        path = shard_root / f"{a.label}-{offset:04d}-{offset + len(names) - 1:04d}.zip"
        files = [file for name in names for file in [name, "truth/" + name]]
        if path.exists():
            with ZipFile(path) as z:
                assert set(z.namelist()) == set(files)
                for file in files:
                    assert digest(z.read(file)) == m["sha256"][file]
            data = path.read_bytes()
            reused = True
        else:
            stream = BytesIO()
            with ZipFile(stream, "w", ZIP_LZMA) as z:
                for file in files:
                    info = ZipInfo(file, date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type = ZIP_LZMA
                    z.writestr(info, (a.run / file).read_bytes())
            data = stream.getvalue()
            reused = False
        assert len(data) <= m["config"]["compressed_shard_cap_bytes"]
        groups.append((path, data, names, reused))
    total = sum(len(g[1]) for g in groups)
    assert total <= m["config"]["compressed_phase_cap_bytes"]
    a.destination.mkdir(parents=True)
    shard_root.mkdir(parents=True, exist_ok=True)
    index = {
        "scientific_fingerprint": m["scientific_fingerprint"],
        "code_sha": m["code_sha"],
        "independent_sources": m["completed_sources"],
        "manifest_path": str(a.destination / "run_manifest.json"),
        "manifest_sha256": digest(raw),
        "artifacts": [],
        "total_compressed_bytes": total,
        "zip_compression": "LZMA lossless",
        "reused_existing_shards": sum(g[3] for g in groups),
    }
    for path, data, names, reused in groups:
        if not reused:
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
