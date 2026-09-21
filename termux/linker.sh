#!/usr/bin/env bash
set -euo pipefail
# build-std's Rust-only compiler-builtins omits the outlined AArch64 atomics
# used by NDK-compiled C dependencies. Resolve them from the pinned NDK runtime.
# V8's Android platform implementation writes diagnostics through liblog.
exec "${CODEX_ANDROID_CLANG:?}" "$@" "${CODEX_ANDROID_BUILTINS:?}" -llog
