#!/usr/bin/env python3
"""Exercise installer failure/upgrade behavior with synthetic executables on Linux.

This checks installation mechanics, not Android binary execution.
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

installer = Path(__file__).with_name("install.sh").resolve()
with tempfile.TemporaryDirectory(prefix="codex-installer-") as temporary:
    root = Path(temporary).resolve()
    prefix, release, commands = (
        root / name for name in ("prefix", "release", "commands")
    )
    for directory in (prefix / "bin", prefix / "tmp", release, commands):
        directory.mkdir(parents=True)
    (prefix / "bin/bash").symlink_to(shutil.which("bash"))
    for relative in ("etc/tls/cert.pem", "lib/libtermux-exec.so"):
        fixture = prefix / relative
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.touch()
    for name, body in {"uname": "echo aarch64", "rg": "exit 0"}.items():
        (commands / name).write_text("#!/bin/sh\n" + body + "\n")
        (commands / name).chmod(0o755)
    binaries = (
        "codex",
        "codex-code-mode-host",
        "codex-responses-api-proxy",
        "termux-file-lock-probe",
    )
    for name in binaries:
        body = (
            'test "$#" = 1 && test -f "$1"'
            if name == "termux-file-lock-probe"
            else "echo synthetic-executable"
        )
        (release / name).write_text("#!/bin/sh\n" + body + "\n")
        (release / name).chmod(0o755)
    (release / "build-info.json").write_text(json.dumps({"test_fixture": True}))
    (release / "BINARY_SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256((release / name).read_bytes()).hexdigest()}  {name}\n"
            for name in binaries
        )
    )
    old_target = root / "previous-codex"
    old_target.write_text("previous-installation\n")
    launcher = prefix / "bin/codex"
    launcher.symlink_to(old_target)
    environment = {
        **os.environ,
        "PREFIX": str(prefix),
        "PATH": str(commands) + os.pathsep + os.environ["PATH"],
    }

    def install(success):
        result = subprocess.run(
            ["bash", str(installer), str(release)],
            env=environment,
            text=True,
            capture_output=True,
        )
        assert (result.returncode == 0) == success, result.stdout + result.stderr

    # Missing host must fail before replacing the original installation.
    host = release / "codex-code-mode-host"
    host.rename(release / "saved-host")
    install(False)
    assert launcher.is_symlink() and launcher.resolve() == old_target
    (release / "saved-host").rename(host)
    # Source executability is unnecessary: installation stages files internally.
    for name in binaries:
        (release / name).chmod(0o644)
    install(True)
    current = prefix / "libexec/codex-termux/current"
    installed = current.resolve()
    assert all((installed / name).is_file() for name in binaries[:-1])
    assert not launcher.is_symlink()
    assert old_target.read_text() == "previous-installation\n"
    assert any(
        path.is_symlink() and path.resolve() == old_target
        for path in (prefix / "bin").glob("codex.before-termux-*")
    )
    # Corruption must not switch away from the complete installed generation.
    host.write_text("#!/bin/sh\necho corrupt\n")
    install(False)
    assert current.resolve() == installed
    # Even a checksum-consistent helper that cannot start must not be activated.
    host.write_text("#!/bin/sh\nexit 42\n")
    (release / "BINARY_SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256((release / name).read_bytes()).hexdigest()}  {name}\n"
            for name in binaries
        )
    )
    generations = set(installed.parent.iterdir())
    install(False)
    assert current.resolve() == installed
    assert set(installed.parent.iterdir()) == generations
    print(
        "PASS missing host, non-executable source, complete install, symlink backup, checksum/startup failure preserves active install"
    )
