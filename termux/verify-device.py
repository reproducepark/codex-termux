#!/usr/bin/env python3
"""Account-free runtime checks; run inside Termux after installing the bundle."""

import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import tempfile

scripts = Path(__file__).resolve().parent
codex = shutil.which("codex")
assert codex, "Install the bundle first"
assert (
    platform.machine() == "aarch64" and Path("/data/data/com.termux/files/usr").is_dir()
), "Run in ARM64 Termux"
with tempfile.TemporaryDirectory(
    prefix=".codex-termux-verify-", dir=Path.home()
) as temporary:
    root = Path(temporary)
    env = {**os.environ}
    env.pop("OPENAI_API_KEY", None)
    for mode in ("app-server", "direct", "code-mode"):
        home, cwd = root / (mode + "-home"), root / (mode + "-work")
        home.mkdir()
        cwd.mkdir()
        env["CODEX_HOME"] = str(home)
        if mode == "app-server":
            subprocess.run(
                [sys.executable, str(scripts / "smoke.py"), "--", codex, "app-server"],
                cwd=cwd,
                env=env,
                check=True,
            )
            continue
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        command = [
            codex,
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            "danger-full-access",
            "-m",
            "termux-smoke",
        ]
        for setting in (
            'model_provider="termux_test"',
            'model_providers.termux_test.name="Termux smoke"',
            f'model_providers.termux_test.base_url="http://127.0.0.1:{port}/v1"',
            'model_providers.termux_test.wire_api="responses"',
            "model_providers.termux_test.requires_openai_auth=false",
            "model_providers.termux_test.supports_websockets=false",
        ):
            command.extend(["-c", setting])
        harness = [sys.executable, str(scripts / "agent-smoke.py"), "--port", str(port)]
        if mode == "code-mode":
            command.extend(["--enable", "code_mode_only"])
            harness.append("--code-mode")
        command.append("Run the controlled smoke test")
        subprocess.run(harness + ["--"] + command, cwd=cwd, env=env, check=True)
        assert (cwd / "agent-test.txt").read_text().strip() == "AGENT_FILE_OK"
print(
    "PASS app-server, shell/PTY, direct tools, Code Mode JS and nested tools on this device"
)
