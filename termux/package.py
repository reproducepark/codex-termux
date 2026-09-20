#!/usr/bin/env python3
"""Record inputs and package the Android executable without private host data."""

import gzip
import hashlib
import io
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tarfile

repo, out = map(Path, sys.argv[1:])


def capture(*args):
    return subprocess.check_output(args, cwd=repo, text=True).strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


existing_info = os.environ.get("CODEX_REPACKAGE_BUILD_INFO")
if existing_info:
    # Preserve the real compilation provenance when adding installer/docs to CI output.
    metadata = json.loads(Path(existing_info).read_text())
    assert not metadata["dirty"], "Cannot repackage an uncommitted build"
    assert metadata["binary_sha256"] == sha(out / "codex")
    assert metadata["cargo_lock_sha256"] == sha(repo / "codex-rs/Cargo.lock")
    built_tree = capture("git", "rev-parse", metadata["fork_commit"] + ":codex-rs")
    assert built_tree == capture("git", "rev-parse", "HEAD:codex-rs")
    metadata["packaging_commit"] = capture("git", "rev-parse", "HEAD")
    metadata["packaging_dirty"] = bool(
        capture("git", "status", "--porcelain", "--untracked-files=no")
    )
else:
    metadata = {
        "upstream_tag": "rust-v0.155.1",
        "upstream_commit": "be2951ea34f0d295ed0becf97079f92fa5f6950e",
        "fork_commit": capture("git", "rev-parse", "HEAD"),
        "dirty": bool(capture("git", "status", "--porcelain", "--untracked-files=no")),
        "target": "aarch64-linux-android",
        "android_api": 28,
        "ndk": "29.0.14206865",
        "build_std": True,
        "std_file_lock_patch_sha256": sha(
            repo / "termux/rust-1.95.0-android-file-lock.patch"
        ),
        "rustc": capture("rustc", "+1.95.0", "-Vv"),
        "build_host": capture("uname", "-sm"),
        "cmake": capture("cmake", "--version").splitlines()[0],
        "ninja": capture("ninja", "--version"),
        "cargo_lock_sha256": sha(repo / "codex-rs/Cargo.lock"),
        "binary_sha256": sha(out / "codex"),
    }

(out / "build-info.json").write_text(json.dumps(metadata, indent=2) + "\n")
shutil.copyfile(repo / "termux/install.sh", out / "install.sh")
for name in ("LICENSE", "NOTICE"):
    shutil.copyfile(repo / name, out / name)
archive = out / "codex-0.155.1-termux.1-aarch64.tar.gz"
epoch = int(os.environ["SOURCE_DATE_EPOCH"])
with (
    archive.open("wb") as stream,
    gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=epoch) as gz,
):
    with tarfile.open(fileobj=gz, mode="w") as tar:
        for name in (
            "codex",
            "install.sh",
            "build-info.json",
            "elf.txt",
            "LICENSE",
            "NOTICE",
            "termux-file-lock-probe",
        ):
            data = (out / name).read_bytes()
            entry = tarfile.TarInfo(name)
            entry.size = len(data)
            entry.mtime = epoch
            entry.mode = (
                0o755
                if name in ("codex", "install.sh", "termux-file-lock-probe")
                else 0o644
            )
            tar.addfile(entry, io.BytesIO(data))
(out / "SHA256SUMS").write_text(
    "".join(
        f"{sha(p)}  {p.name}\n" for p in [out / "codex", archive, out / "install.sh"]
    )
)
