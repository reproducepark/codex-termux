#!/usr/bin/env python3
"""Run a Codex tool-call round trip against an account-free loopback API.

Usage: agent-smoke.py --port 54246 -- COMMAND...
COMMAND must run codex exec in a disposable cwd and CODEX_HOME, with a custom
Responses provider whose base_url is http://127.0.0.1:54246/v1. For a phone,
forward this port with adb reverse and use ssh as the command prefix.
"""

import argparse
import http.server
import json
import subprocess
import threading

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--port", type=int, required=True)
parser.add_argument("command", nargs=argparse.REMAINDER)
args = parser.parse_args()
command = args.command[1:] if args.command[:1] == ["--"] else args.command
if not command:
    parser.error("a Codex command is required")
results = []
requests = []


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        requests.append(request)
        outputs = [
            item
            for item in request.get("input", [])
            if item.get("type") == "function_call_output"
        ]
        if outputs:
            results.extend(outputs)
            item = {
                "type": "message",
                "role": "assistant",
                "id": "message-termux",
                "content": [{"type": "output_text", "text": "TERMUX_AGENT_OK"}],
            }
        else:
            item = {
                "type": "function_call",
                "call_id": "termux-call",
                "name": "exec_command",
                "arguments": json.dumps(
                    {
                        "cmd": 'printf "AGENT_FILE_OK\\n" > agent-test.txt; cat agent-test.txt',
                        "max_output_tokens": 1000,
                    }
                ),
            }
        events = [
            {"type": "response.created", "response": {"id": "response-termux"}},
            {"type": "response.output_item.done", "item": item},
            {
                "type": "response.completed",
                "response": {
                    "id": "response-termux",
                    "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                },
            },
        ]
        data = "".join(
            "data: " + json.dumps(event) + "\n\n" for event in events
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    process = subprocess.run(command, capture_output=True, text=True, timeout=120)
    print(process.stdout)
    print(process.stderr)
    assert process.returncode == 0, process.returncode
    assert len(requests) >= 2, "No second model request after the tool call"
    assert "AGENT_FILE_OK" in json.dumps(results), results
    assert "TERMUX_AGENT_OK" in process.stdout, "Missing final model response"
    print(
        "PASS actual Codex exec: HTTP/SSE, tool dispatch, shell, file I/O, tool result"
    )
finally:
    server.shutdown()
    server.server_close()
