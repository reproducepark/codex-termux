#!/usr/bin/env python3
"""Prepare pinned Android inputs for rusty_v8's source build on Linux."""

import hashlib
import os
from pathlib import Path
import shutil
import subprocess

cargo_home = Path(os.environ.get("CARGO_HOME", Path.home() / ".cargo"))
roots = list((cargo_home / "registry/src").glob("*/v8-150.4.0"))
assert len(roots) == 1, "Run cargo fetch --locked before preparing V8"
root = roots[0]
ndk = Path(os.environ["ANDROID_NDK_HOME"]).resolve()
# Chromium's Android compiler config still references this NDK rebuild marker,
# but the pinned config.gni no longer defines it. Restore the actual pinned NDK
# version; this does not change V8 runtime features or sandboxing.
config = root / "build/config/android/config.gni"
original = config.read_text()
marker = '  android_ndk_version = "r29"\n'
if marker not in original:
    assert (
        hashlib.sha256(config.read_bytes()).hexdigest()
        == "7f2dbf15025c7f391b8a89813690d7307d84045c38f1f1bcb5aa39071d91160f"
    )
    anchor = '  android_ndk_root = "//third_party/android_toolchain/ndk"\n'
    assert original.count(anchor) == 1
    config.write_text(original.replace(anchor, marker + anchor))
# The build script checks the old location; Chromium GN uses the newer one.
for relative in ("third_party/android_ndk", "third_party/android_toolchain/ndk"):
    link = root / relative
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink():
        link.unlink()
    assert not link.exists(), f"Unexpected existing NDK at {link}"
    link.symlink_to(ndk, target_is_directory=True)

# These exact revisions are recorded in the crate's v8/DEPS. Avoid build.rs's
# unpinned shallow clones of the moving default branches.
deps = {
    "android_platform": (
        "https://chromium.googlesource.com/chromium/src/third_party/android_platform.git",
        "e3919359f2387399042d31401817db4a02d756ec",
    ),
    "catapult": (
        "https://chromium.googlesource.com/catapult.git",
        "2852bb7e91e4995502ffb72b7ed21412ee157914",
    ),
}
manifest = (root / "v8/DEPS").read_text()
for name, (url, revision) in deps.items():
    assert revision in manifest
    destination = root / "third_party" / name
    if not destination.exists():
        subprocess.run(["git", "init", str(destination)], check=True)
        subprocess.run(
            ["git", "-C", str(destination), "fetch", "--depth=1", url, revision],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(destination), "checkout", "--detach", "FETCH_HEAD"],
            check=True,
        )
    actual = subprocess.check_output(
        ["git", "-C", str(destination), "rev-parse", "HEAD"], text=True
    ).strip()
    assert actual == revision, (name, actual)

# The published crate omits ICU's data and Chromium's vendored Rust sources.
# Restore only those absent inputs from submodules pinned by v150.4.0, without
# replacing the crate's own GN/build-script adjustments.
for name, url, revision, relative in (
    (
        "build",
        "https://github.com/denoland/chromium_build.git",
        "8acb33ac8dceef0503443109c0a92988189563ef",
        "android",
    ),
    (
        "icu",
        "https://chromium.googlesource.com/chromium/deps/icu.git",
        "ee5f27adc28bd3f15b2c293f726d14d2e336cbd5",
        "common/icudtl.dat",
    ),
    (
        "rust",
        "https://chromium.googlesource.com/chromium/src/third_party/rust",
        "26e8ff47f18a8d28d6187a04b6a16cb7332356f8",
        "chromium_crates_io",
    ),
):
    checkout = cargo_home / "git/termux-v8-inputs" / f"{name}-{revision}"
    if not (checkout / ".git").exists():
        checkout.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", str(checkout)], check=True)
        subprocess.run(
            ["git", "-C", str(checkout), "fetch", "--depth=1", url, revision],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(checkout), "checkout", "--detach", "FETCH_HEAD"],
            check=True,
        )
    actual = subprocess.check_output(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    assert actual == revision
    source = checkout / relative
    destination = (
        root / ("build" if name == "build" else f"third_party/{name}") / relative
    )
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

# V8's cross-compiled snapshot generator runs on the Linux build machine.
subprocess.run(
    ["python3", "build/linux/sysroot_scripts/install-sysroot.py", "--arch=amd64"],
    cwd=root,
    check=True,
)
print("Prepared rusty_v8 150.4.0 with pinned Android dependencies")
