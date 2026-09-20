#!/usr/bin/env python3
"""Record inputs and package the Android executable without private host data."""

import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

repo, out = map(Path, sys.argv[1:])


def capture(*args):
    return subprocess.check_output(args, cwd=repo, text=True).strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


metadata = {
    "upstream_tag": "rust-v0.155.1",
    "upstream_commit": "be2951ea34f0d295ed0becf97079f92fa5f6950e",
    "fork_commit": capture("git", "rev-parse", "HEAD"),
    "dirty": bool(capture("git", "status", "--porcelain", "--untracked-files=no")),
    "target": "aarch64-linux-android",
    "android_api": 28,
    "ndk": "29.0.14206865",
    "rustc": capture("rustc", "+1.95.0", "-Vv"),
    "cargo_lock_sha256": sha(repo / "codex-rs/Cargo.lock"),
    "binary_sha256": sha(out / "codex"),
}
(out / "build-info.json").write_text(json.dumps(metadata, indent=2) + "\n")
archive = out / "codex-0.155.1-termux.1-aarch64.tar.gz"
epoch = int(os.environ["SOURCE_DATE_EPOCH"])
with (
    archive.open("wb") as stream,
    gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=epoch) as gz,
):
    with tarfile.open(fileobj=gz, mode="w") as tar:
        for name in ("codex", "build-info.json", "elf.txt"):
            data = (out / name).read_bytes()
            entry = tarfile.TarInfo(name)
            entry.size = len(data)
            entry.mtime = epoch
            entry.mode = 0o755 if name == "codex" else 0o644
            tar.addfile(entry, io.BytesIO(data))
(out / "SHA256SUMS").write_text(
    "".join(f"{sha(p)}  {p.name}\n" for p in [out / "codex", archive])
)
