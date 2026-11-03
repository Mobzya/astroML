"""Solid-container restore and path/checksum rejection, using non-scientific bytes."""

import hashlib
import json
import subprocess
import sys
from io import BytesIO
from zipfile import ZIP_LZMA, ZIP_STORED, ZipFile


def test_solid_restore_and_reject_controls(tmp_path):
    files = {"source-0000.json": b'{"fixture":true}\n', "truth/source-0000.json": b"{}\n"}
    sha = lambda b: hashlib.sha256(b).hexdigest()
    manifest = {
        "status": "PARTIAL_CHECKPOINT",
        "completed_sources": 1,
        "scientific_fingerprint": "unit-no-observations",
        "sha256": {n: sha(b) for n, b in files.items()},
    }
    mp = tmp_path / "manifest.json"
    mp.write_text(json.dumps(manifest))
    inner = BytesIO()
    with ZipFile(inner, "w", ZIP_STORED) as z:
        for n, b in files.items():
            z.writestr(n, b)
    part = tmp_path / "solid.zip"
    with ZipFile(part, "w", ZIP_LZMA) as z:
        z.writestr("payload.zip", inner.getvalue())
    index = {
        "manifest_path": str(mp),
        "manifest_sha256": sha(mp.read_bytes()),
        "shard_container": "solid-zip-v1",
        "artifacts": [{"path": str(part), "sha256": sha(part.read_bytes())}],
    }
    ip = tmp_path / "index.json"
    ip.write_text(json.dumps(index))

    def run(output):
        return subprocess.run(
            [
                sys.executable,
                "scripts/restore_research_shards.py",
                "--index",
                str(ip),
                "--output",
                str(output),
                "--allow-partial",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    restored = tmp_path / "ok"
    assert run(restored).returncode == 0
    for n, b in files.items():
        assert (restored / n).read_bytes() == b
    index["artifacts"][0]["sha256"] = "0" * 64
    ip.write_text(json.dumps(index))
    assert "AssertionError" in run(tmp_path / "bad-sha").stderr
    files = {"../escape.json": b"{}\n", "truth/source-0000.json": b"{}\n"}
    manifest["sha256"] = {n: sha(b) for n, b in files.items()}
    mp.write_text(json.dumps(manifest))
    inner = BytesIO()
    with ZipFile(inner, "w", ZIP_STORED) as z:
        for n, b in files.items():
            z.writestr(n, b)
    with ZipFile(part, "w", ZIP_LZMA) as z:
        z.writestr("payload.zip", inner.getvalue())
    index["manifest_sha256"] = sha(mp.read_bytes())
    index["artifacts"][0]["sha256"] = sha(part.read_bytes())
    ip.write_text(json.dumps(index))
    assert "AssertionError" in run(tmp_path / "bad-path").stderr
    assert not (tmp_path / "escape.json").exists()
