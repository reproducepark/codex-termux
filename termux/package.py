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
binaries = ("codex", "codex-code-mode-host", "codex-responses-api-proxy")


def capture(*args):
    return subprocess.check_output(args, cwd=repo, text=True).strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


existing_info = os.environ.get("CODEX_REPACKAGE_BUILD_INFO")
if existing_info:
    # Preserve the real compilation provenance when adding installer/docs to CI output.
    metadata = json.loads(Path(existing_info).read_text())
    assert not metadata["dirty"], "Cannot repackage an uncommitted build"
    assert metadata.get("build_std") is True
    assert metadata["std_file_lock_patch_sha256"] == sha(
        repo / "termux/rust-1.95.0-android-file-lock.patch"
    )
    assert metadata["binaries_sha256"] == {name: sha(out / name) for name in binaries}
    assert metadata["cargo_lock_sha256"] == sha(repo / "codex-rs/Cargo.lock")
    for path in (
        "codex-rs",
        "termux/file-lock-probe",
        "termux/build.sh",
        "termux/linker.sh",
        "termux/prepare-toolchain.py",
        "termux/prepare-v8.py",
    ):
        built_tree = capture("git", "rev-parse", metadata["fork_commit"] + ":" + path)
        assert built_tree == capture("git", "rev-parse", "HEAD:" + path), path
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
        "ndk_builtins_sha256": sha(Path(os.environ["CODEX_ANDROID_BUILTINS"])),
        "release_debug": 0,
        "release_lto": "thin",
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
        "binaries_sha256": {name: sha(out / name) for name in binaries},
        "v8": {"version": "150.4.0", "from_source": True, "sandbox": True,
               "prepare_sha256": sha(repo / "termux/prepare-v8.py"),
               "gn_args": os.environ["EXTRA_GN_ARGS"]},
    }

(out / "build-info.json").write_text(json.dumps(metadata, indent=2) + "\n")
shutil.copyfile(repo / "termux/install.sh", out / "install.sh")
for name in ("LICENSE", "NOTICE"):
    shutil.copyfile(repo / name, out / name)
archive = out / "codex-0.155.1-termux.2-aarch64.tar.gz"
epoch = int(os.environ["SOURCE_DATE_EPOCH"])
with (
    archive.open("wb") as stream,
    gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=epoch) as gz,
):
    with tarfile.open(fileobj=gz, mode="w") as tar:
        for name in (
            *binaries,
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
                if name in (*binaries, "install.sh", "termux-file-lock-probe")
                else 0o644
            )
            tar.addfile(entry, io.BytesIO(data))
(out / "SHA256SUMS").write_text(
    "".join(
        f"{sha(p)}  {p.name}\n" for p in [*(out / name for name in binaries), archive, out / "install.sh"]
    )
)
