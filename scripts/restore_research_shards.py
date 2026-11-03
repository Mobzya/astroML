"""Restore only manifest-authorized JSON files from checksum-verified local shards."""

import argparse
import hashlib
import json
from contextlib import ExitStack
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument(
        "--allow-partial",
        action="store_true",
        help="Explicitly restore a completed-source partial checkpoint",
    )
    args = p.parse_args()
    assert not args.output.exists(), "Never overwrite existing output"
    index = json.loads(args.index.read_text())
    manifest_raw = Path(index["manifest_path"]).read_bytes()
    assert sha(manifest_raw) == index["manifest_sha256"]
    manifest = json.loads(manifest_raw)
    assert manifest["status"] == "COMPLETE" or (
        args.allow_partial and manifest["status"] in ["PARTIAL_CHECKPOINT", "INTERRUPTED"]
    )
    assert len(manifest["sha256"]) == 2 * manifest["completed_sources"]
    restored = set()
    args.output.mkdir(parents=True)
    for part in index["artifacts"]:
        assert sha(Path(part["path"]).read_bytes()) == part["sha256"], part["path"]
        with ExitStack() as stack:
            z = stack.enter_context(ZipFile(part["path"]))
            if index.get("shard_container") == "solid-zip-v1":
                assert z.namelist() == ["payload.zip"]
                assert z.getinfo("payload.zip").file_size <= 64 * 1024 * 1024
                z = stack.enter_context(ZipFile(BytesIO(z.read("payload.zip"))))
            for name in z.namelist():
                path = Path(name)
                assert not path.is_absolute() and ".." not in path.parts
                assert path.parent in [Path("."), Path("truth")]
                assert (
                    path.suffix == ".json" and name in manifest["sha256"] and name not in restored
                )
                raw = z.read(name)
                assert sha(raw) == manifest["sha256"][name], name
                target = args.output / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                restored.add(name)
    assert restored == set(manifest["sha256"])
    (args.output / "manifest.json").write_bytes(manifest_raw)
    print(
        json.dumps(
            {
                "status": "RESTORED",
                "data_files": len(restored),
                "independent_sources": manifest["completed_sources"],
                "scientific_fingerprint": manifest["scientific_fingerprint"],
            }
        )
    )


if __name__ == "__main__":
    main()
