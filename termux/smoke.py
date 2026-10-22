#!/usr/bin/env python3
"""Exercise the real app-server process/shell/PTY path without an API account.

Usage: python3 termux/smoke.py -- codex app-server
The command may be prefixed with ssh; it must start the installed phone binary.
Use a disposable CODEX_HOME and cwd in the command wrapper.
"""

import base64
import json
import queue
import subprocess
import sys
import tempfile
import threading
import time

argv = sys.argv[1:]
if argv[:1] == ["--"]:
    argv = argv[1:]
if not argv:
    raise SystemExit(__doc__)
messages = queue.Queue()
with tempfile.TemporaryFile(mode="w+") as errors:
    proc = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=errors,
        text=True,
        bufsize=1,
    )

    def reader():
        for line in proc.stdout:
            try:
                messages.put(json.loads(line))
            except json.JSONDecodeError:
                messages.put({"invalid": line})
        messages.put({"eof": True})

    threading.Thread(target=reader, daemon=True).start()

    def send(method, params, request_id=None):
        message = {"method": method, "params": params}
        if request_id is not None:
            message["id"] = request_id
        proc.stdin.write(json.dumps(message) + "\n")
        proc.stdin.flush()

    def result(request_id, timeout=60):
        deadline = time.monotonic() + timeout
        output = ""
        while True:
            message = messages.get(timeout=max(0.1, deadline - time.monotonic()))
            if message.get("eof"):
                raise RuntimeError("app-server exited before response")
            if message.get("method") == "command/exec/outputDelta":
                output += base64.b64decode(message["params"]["deltaBase64"]).decode()
            if message.get("id") == request_id:
                if "error" in message:
                    raise RuntimeError(message["error"])
                return message["result"], output

    try:
        send(
            "initialize",
            {
                "clientInfo": {"name": "termux_validation", "version": "1.0"},
                "capabilities": {"experimentalApi": True},
            },
            1,
        )
        initialized, _ = result(1)
        print("PASS initialize", initialized.get("userAgent", ""), flush=True)
        send("initialized", {})
        shell = "/data/data/com.termux/files/usr/bin/bash"
        # Restricted to the disposable cwd; explicit unsandboxed policy because
        # Android has no supported Codex OS sandbox. No user config is changed.
        command = (
            'set -e; printf "termux-한글\\n" > probe.txt; rg "termux" probe.txt; '
            'printf "PIPE_OK\\n" | cat; '
            "printf '%s\\n' '#!/usr/bin/env bash' 'printf SHEBANG_OK' > shebang.sh; "
            "chmod +x shebang.sh; ./shebang.sh; rm probe.txt shebang.sh"
        )
        send(
            "command/exec",
            {
                "command": [shell, "-c", command],
                "sandboxPolicy": {"type": "dangerFullAccess"},
                "timeoutMs": 15000,
            },
            2,
        )
        response, _ = result(2)
        assert response["exitCode"] == 0, response
        assert (
            "termux-한글" in response["stdout"] and "PIPE_OK" in response["stdout"]
        ), response
        assert "SHEBANG_OK" in response["stdout"], response
        print("PASS shell, write/read, ripgrep, pipes, UTF-8, env shebang", flush=True)
        send(
            "command/exec",
            {
                "command": [
                    shell,
                    "-c",
                    'read -r line; printf "PTY_%s\\n" "$line"; stty size',
                ],
                "processId": "termux-pty",
                "tty": True,
                "size": {"rows": 24, "cols": 80},
                "sandboxPolicy": {"type": "dangerFullAccess"},
                "timeoutMs": 15000,
            },
            3,
        )
        time.sleep(1)
        send(
            "command/exec/resize",
            {"processId": "termux-pty", "size": {"rows": 32, "cols": 100}},
            4,
        )
        result(4)
        send(
            "command/exec/write",
            {
                "processId": "termux-pty",
                "deltaBase64": base64.b64encode(b"ROUNDTRIP\n").decode(),
            },
            5,
        )
        # Responses can interleave, so wait for both write and process completion.
        output = ""
        completed = {}
        deadline = time.monotonic() + 30
        while not {3, 5}.issubset(completed):
            message = messages.get(timeout=max(0.1, deadline - time.monotonic()))
            if "error" in message or message.get("eof"):
                raise RuntimeError(message)
            if message.get("method") == "command/exec/outputDelta":
                output += base64.b64decode(message["params"]["deltaBase64"]).decode()
            if message.get("id") in (3, 5):
                completed[message["id"]] = message["result"]
        assert completed[3]["exitCode"] == 0, completed
        assert "PTY_ROUNDTRIP" in output and "32 100" in output, output
        print("PASS PTY input/output and resize (32 x 100)", flush=True)
    except BaseException:
        errors.seek(0)
        print(errors.read()[-12000:], file=sys.stderr)
        raise
    finally:
        proc.stdin.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=10)
print("All Termux smoke checks passed.")
