"""Restore only manifest-authorized JSON files from checksum-verified local shards."""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    assert not args.output.exists(), "Never overwrite existing output"
    index = json.loads(args.index.read_text())
    manifest_raw = Path(index["manifest_path"]).read_bytes()
    assert sha(manifest_raw) == index["manifest_sha256"]
    manifest = json.loads(manifest_raw)
    assert manifest["status"] == "COMPLETE"
    restored = set()
    args.output.mkdir(parents=True)
    for part in index["artifacts"]:
        assert sha(Path(part["path"]).read_bytes()) == part["sha256"], part["path"]
        with ZipFile(part["path"]) as z:
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
