#!/usr/bin/env python3
"""Create a private Rust sysroot overlay with Android std::fs file locking."""

import hashlib
from pathlib import Path
import shutil
import shlex
import subprocess
import sys

original, overlay = map(Path, sys.argv[1:])
source_file = Path("lib/rustlib/src/rust/library/std/src/sys/fs/unix.rs")
expected = "77c6419ee048c348d9ed4bef226ce6ceb735d6077d0eb9f6bcac0ef46fa7b86d"
assert hashlib.sha256((original / source_file).read_bytes()).hexdigest() == expected
if not overlay.exists():
    # Reuse immutable binaries/libraries and copy rust-src before patching.
    # Wrappers below explicitly select this overlay with --sysroot.
    for parent in (Path("."), Path("lib"), Path("lib/rustlib"), Path("bin")):
        (overlay / parent).mkdir(parents=True, exist_ok=True)
        for item in (original / parent).iterdir():
            relative = parent / item.name
            target = overlay / relative
            if relative in (Path("lib"), Path("lib/rustlib"), Path("bin")):
                continue
            if relative == Path("lib/rustlib/src"):
                shutil.copytree(item, target, symlinks=False)
            elif relative in (Path("bin/rustc"), Path("bin/rustdoc")):
                shutil.copy2(item, target)
            else:
                target.symlink_to(item.resolve(), target_is_directory=item.is_dir())
    patch = Path(__file__).with_name("rust-1.95.0-android-file-lock.patch").resolve()
    with patch.open("rb") as stream:
        subprocess.run(
            ["patch", "-p1"],
            cwd=overlay / "lib/rustlib/src/rust",
            stdin=stream,
            check=True,
        )
    (overlay / ".android-file-lock-patch").write_text(
        hashlib.sha256(patch.read_bytes()).hexdigest()
    )
else:
    patch = Path(__file__).with_name("rust-1.95.0-android-file-lock.patch")
    assert (overlay / ".android-file-lock-patch").read_text() == hashlib.sha256(
        patch.read_bytes()
    ).hexdigest()
for tool in ("rustc", "rustdoc"):
    wrapper = overlay / "bin" / (tool + "-termux")
    wrapper.write_text(
        "#!/bin/sh\nexec "
        + shlex.quote(str(original / "bin" / tool))
        + " --sysroot "
        + shlex.quote(str(overlay))
        + ' "$@"\n'
    )
    wrapper.chmod(0o755)
assert subprocess.check_output(
    [str(overlay / "bin/rustc-termux"), "--print", "sysroot"], text=True
).strip() == str(overlay)
print(overlay)
