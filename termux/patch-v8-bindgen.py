#!/usr/bin/env python3
"""Keep Cargo's Android binding options out of GN's per-target bindgen calls."""

import hashlib
from pathlib import Path
import sys

ORIGINAL_SHA256 = "fa59f9937748ac83e4a23b619edb3be54efcbb0f3f37edce78b17cd8aafa9f34"
BEFORE = "    env = os.environ\n"
AFTER = """    # Termux: GN supplies a target and sysroot for each host/Android action.
    # Cargo's outer Android bindgen options must not override those GN flags.
    env = {
        key: value for key, value in os.environ.items()
        if key not in ("TARGET", "CLANG_PATH")
        and not key.startswith("BINDGEN_EXTRA_CLANG_ARGS")
    }
"""


def patch(path):
    original = path.read_text()
    if AFTER in original:
        original = original.replace(AFTER, BEFORE)
    assert hashlib.sha256(original.encode()).hexdigest() == ORIGINAL_SHA256
    assert original.count(BEFORE) == 1
    updated = original.replace(BEFORE, AFTER)
    compile(updated, str(path), "exec")
    if path.read_text() != updated:
        path.write_text(updated)


if __name__ == "__main__":
    patch(Path(sys.argv[1]))
