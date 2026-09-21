#!/usr/bin/env python3
"""Prepare pinned Android inputs for rusty_v8's source build on Linux."""

import os
from pathlib import Path
import subprocess

cargo_home = Path(os.environ.get("CARGO_HOME", Path.home() / ".cargo"))
roots = list((cargo_home / "registry/src").glob("*/v8-150.4.0"))
assert len(roots) == 1, "Run cargo fetch --locked before preparing V8"
root = roots[0]
ndk = Path(os.environ["ANDROID_NDK_HOME"]).resolve()
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

# V8's cross-compiled snapshot generator runs on the Linux build machine.
subprocess.run(
    ["python3", "build/linux/sysroot_scripts/install-sysroot.py", "--arch=amd64"],
    cwd=root,
    check=True,
)
print("Prepared rusty_v8 150.4.0 with pinned Android dependencies")
