#!/usr/bin/env python3
"""Exercise GN bindgen subprocess environments using the pinned upstream driver."""

import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

patcher = runpy.run_path(str(Path(__file__).with_name("patch-v8-bindgen.py")))
source = Path(sys.argv[1]).read_text().replace(patcher["AFTER"], patcher["BEFORE"])
with tempfile.TemporaryDirectory(prefix="termux-bindgen-") as temporary:
    root = Path(temporary)
    driver = root / "run_bindgen.py"
    driver.write_text(source)
    # No depfile is requested. Header filtering is outside this environment test.
    (root / "action_helpers.py").write_text("")
    (root / "filter_clang_args.py").write_text(
        "def filter_clang_args(args): return args\n"
    )
    child = root / "bindgen"
    child.write_text(
        "#!/usr/bin/env python3\n"
        "import json,os,pathlib,sys\n"
        "p=pathlib.Path(sys.argv[sys.argv.index('--output')+1])\n"
        "p.write_text('')\n"
        "p.with_suffix('.json').write_text(json.dumps({'args':sys.argv[1:],"
        "'env':{k:v for k,v in os.environ.items() if k in "
        "('TARGET','CLANG_PATH','LIBCLANG_PATH') or "
        "k.startswith('BINDGEN_EXTRA_CLANG_ARGS')}}))\n"
    )
    child.chmod(0o755)
    formatter = root / "rustfmt"
    formatter.write_text("#!/bin/sh\nexit 0\n")
    formatter.chmod(0o755)
    inherited = {
        "TARGET": "aarch64-linux-android",
        "CLANG_PATH": "/outer/android/clang",
        "BINDGEN_EXTRA_CLANG_ARGS": "--target=aarch64-linux-android28",
        "BINDGEN_EXTRA_CLANG_ARGS_aarch64_linux_android": "--sysroot=/android",
        "BINDGEN_EXTRA_CLANG_ARGS_aarch64-linux-android": "--sysroot=/android",
    }
    env = {**os.environ, **inherited}

    def run(target):
        output = root / "bindings.rs"
        subprocess.run(
            [
                sys.executable,
                str(driver),
                "--bindgen-exe",
                str(child),
                "--rustfmt-exe",
                str(formatter),
                "--header",
                "probe.h",
                "--output",
                str(output),
                "--libclang-path",
                "/gn/libclang",
                "--",
                "--target=" + target,
            ],
            env=env,
            check=True,
        )
        return json.loads(output.with_suffix(".json").read_text())

    assert run("x86_64-unknown-linux-gnu")["env"]["TARGET"] == inherited["TARGET"]
    patcher["patch"](driver)
    first = driver.read_bytes()
    patcher["patch"](driver)
    assert driver.read_bytes() == first
    for target in ("x86_64-unknown-linux-gnu", "aarch64-linux-android28"):
        result = run(target)
        assert result["env"] == {"LIBCLANG_PATH": "/gn/libclang"}, result
        assert "--target=" + target in result["args"], result
    assert all(env[key] == value for key, value in inherited.items())
print("PASS negative control, GN host/Android environment isolation, idempotent patch")
