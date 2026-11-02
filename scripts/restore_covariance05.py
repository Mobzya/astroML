"""Restore COV05 files exclusively from checksum-verified committed artifacts.

Does not fit models, resume workers or change source IDs. A partial checkpoint
retains its partial status. Existing output directories are never overwritten.
"""

import argparse
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--phase", choices=["calibration", "evaluation"], required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    index = json.loads(Path("reports/covariance05/artifacts.json").read_text())
    artifacts = [a for a in index["artifacts"] if a["phase"] == args.phase]
    raw_archives = []
    for artifact in artifacts:
        raw = Path(artifact["path"]).read_bytes()
        assert sha(raw) == artifact["sha256"], artifact["path"]
        raw_archives.append(raw)
    if args.phase == "evaluation":
        snapshot = index["evaluation_snapshot"]
        manifest_raw = Path(snapshot["path"]).read_bytes()
        assert sha(manifest_raw) == snapshot["sha256"]
    else:
        assert len(raw_archives) == 1
        with ZipFile(io.BytesIO(raw_archives[0])) as archive:
            manifest_raw = archive.read("run_manifest.json")
    manifest = json.loads(manifest_raw)
    assert manifest["phase"] == args.phase
    args.output.mkdir(parents=True)
    restored = set()
    for raw in raw_archives:
        with ZipFile(io.BytesIO(raw)) as archive:
            for name in archive.namelist():
                if name == "run_manifest.json":
                    continue
                assert name in manifest["sha256"], name
                assert name not in restored, name
                # Restrict writes to the two known batch namespaces; never extract arbitrary paths.
                relative = Path(name)
                assert not relative.is_absolute() and ".." not in relative.parts
                assert relative.parent == Path(".") or relative.parent == Path("truth")
                assert relative.name.startswith("batch-") and relative.suffix == ".json"
                content = archive.read(name)
                assert sha(content) == manifest["sha256"][name], name
                target = args.output / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                restored.add(name)
    assert restored == set(manifest["sha256"])
    (args.output / "run_manifest.json").write_bytes(manifest_raw)
    print(
        json.dumps(
            {
                "status": "RESTORED",
                "run_status": manifest["status"],
                "completed_sources": manifest["completed_pairs"],
                "expected_sources": manifest["expected_pairs"],
                "verified_data_files": len(restored),
                "scientific_fingerprint": manifest["scientific_fingerprint"],
            }
        )
    )


if __name__ == "__main__":
    main()
