#!/usr/bin/env python3
"""Reject incomplete or non-Android bundles before publishing an artifact."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile

out, readelf = Path(sys.argv[1]), sys.argv[2]
names = (
    "codex",
    "codex-code-mode-host",
    "codex-responses-api-proxy",
    "termux-file-lock-probe",
)
metadata = json.loads((out / "build-info.json").read_text())
for name in names:
    binary = out / name
    assert binary.is_file() and binary.stat().st_mode & 0o111, name
    elf = subprocess.check_output(
        [readelf, "-W", "-h", "-l", "-d", str(binary)], text=True
    )
    assert "AArch64" in elf and re.search(r"Type:\s+DYN", elf), name
    assert "/system/bin/linker64" in elf, name
    dependencies = set(re.findall(r"Shared library: \[(.*?)\]", elf))
    assert dependencies <= {"libc.so", "libm.so", "libdl.so", "liblog.so"}, (
        name,
        dependencies,
    )
    loads = [
        line.split()[-1]
        for line in elf.splitlines()
        if line.lstrip().startswith("LOAD ")
    ]
    assert loads and all(int(value, 16) >= 16384 for value in loads), (name, loads)
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    if name != "termux-file-lock-probe":
        assert metadata["binaries_sha256"][name] == digest, name
    print(f"PASS Android PIE, system dependencies, 16 KiB alignment: {name}")
with tarfile.open(out / "codex-0.155.1-termux.2-aarch64.tar.gz") as archive:
    expected = {
        *names,
        "install.sh",
        "build-info.json",
        "BINARY_SHA256SUMS",
        "elf.txt",
        "LICENSE",
        "NOTICE",
    }
    assert set(archive.getnames()) == expected, archive.getnames()
    for entry in archive.getmembers():
        assert entry.isfile(), entry.name
        assert archive.extractfile(entry).read() == (out / entry.name).read_bytes(), (
            entry.name
        )
subprocess.run(
    ["sha256sum", "--strict", "-c", "BINARY_SHA256SUMS"], cwd=out, check=True
)
print("PASS complete archive, build provenance and binary checksums")
