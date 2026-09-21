# Validation history

## 0.155.1-termux.2 — CI and physical-device checks passed

Date: 2026-09-21 (Asia/Seoul).

The [GitHub Actions build](https://github.com/reproducepark/codex-termux/actions/runs/35582465949)
compiled this revision at `f6f7ae401d4aa6b10df387df589eab57a44cae95`.
It builds and packages `codex`, `codex-code-mode-host`, and
`codex-responses-api-proxy` together. `build-info.json` records the compilation
commit, any later packaging commit, and each executable's SHA-256.

Completed checks:

- Locked Android ARM64 release compilation of all three executables and the
  standalone file-lock/NDK-atomic probe: pass.
- Every executable: Android AArch64 PIE, `/system/bin/linker64`, at least 16 KiB
  LOAD alignment, and dependencies restricted to Android system libraries
  (`libc`, `libm`, `libdl`, and where needed `liblog`): pass.
- Required archive contents, archived bytes, per-binary hashes and build
  provenance consistency: pass.
- Installer regression tests on Linux with synthetic executables: pass. They
  cover missing helpers, non-executable download sources, symlink preservation,
  corrupt checksums and helper startup failure. Failed checks preserve the
  active installation; these fixtures do not execute the Android binaries.
- Shell/Python syntax and workflow lint: pass.
- All 1,333 external Cargo versions, sources and checksums remain identical to
  upstream stable `rust-v0.155.1`. `just bazel-lock-update` leaves its output
  unchanged. Rust formatting checks pass.
- Smoke harness sanity check against the existing macOS app CLI
  `0.155.0-alpha.9.2`: direct tools and Code Mode JS/nested tools pass. A copied
  CLI without the host reproduces the reported missing-host failure and the
  harness rejects it even if the CLI exits with status zero. This validates the
  harness only, not the new Android runtime.

The source recipe restores the NDK r29 marker and Android build scripts,
host/Android ICU build data, and Chromium Rust sources omitted by the published
V8 crate, using its exact upstream submodule revisions. Bindgen uses NDK
Clang/libclang 21 with an explicit API-28 Android sysroot. Each executable enables
vendored OpenSSL independently on Android. V8's upstream sandbox feature stays
enabled. Rust, NDK and source versions remain pinned; independent bit-for-bit
rebuild equality has not been established.

### Physical-device verification of the published revision

The user made the phone available again on 2026-09-21. The published archive
(SHA-256 `3a3f780916814d4a479a3d1668c8a958332a9bb03e596d089e9dcc93046d9375`)
was transferred to the device, verified, and installed using its bundled installer.
The installed binaries also pass their bundled `BINARY_SHA256SUMS` checks.

Device: Samsung SM-S948N, Android 17, aarch64, 4096-byte kernel pages,
Termux 0.118.3 reporting `TERMUX_APK_RELEASE=F_DROID`. Native Bionic execution;
no proot or Linux container.

- CLI, Code Mode host and responses-proxy startup checks: pass.
- Android std file locking and NDK outlined atomic probe: pass.
- App-server initialization, shell, file write/read, ripgrep, pipes, Korean UTF-8,
  `/usr/bin/env bash` shebang: pass.
- PTY stdin/stdout and resize to 32 rows by 100 columns: pass.
- Direct tool HTTP/SSE round trip through the actual Android CLI: pass.
- Code Mode HTTP/SSE round trip: pass. Actual Android V8 evaluation returned
  `JS_ENGINE_OK:42`; a nested `tools.exec_command` wrote and read `AGENT_FILE_OK`.
  The harness rejected direct-tool fallback and missing-host warnings and
  independently read back the resulting file.
- Native phone TUI restarted and rendered the configured model/input prompt: pass.
- Authenticated ChatGPT request with `gpt-5.6-sol`, low reasoning and Code Mode:
  pass. The model called `exec`, evaluated `6 * 7`, called the real shell and
  returned `LIVE_CODE_MODE_OK`. The test session's `custom_tool_call_output`
  independently contains both `LIVE_JS_OK:42` and `LIVE_SHELL_OK`.
  The CLI's human-readable output omits the top-level JS text, so the initial
  stdout-only assertion was insufficient; the exact test session record confirms it.
  The prior `host executable was not found` warning did not recur.

The account-free tests used the release's `smoke.py` and `agent-smoke.py` driven
from the host over SSH/ADB loopback forwarding, with disposable on-device Codex
homes and work directories. The authenticated check used the existing login and
a disposable work directory. No login or configuration files were copied or
changed. Test directories and temporary remote access were cleaned up.

These checks establish native V8 execution and nested tool operation on this
phone, not exhaustive JIT coverage, operation on a 16 KiB-page kernel, or all
optional integrations. The proxy was started with `--help`; a full proxy routing
integration was not tested. Android OS sandbox support remains unavailable;
execution tests explicitly selected an unsandboxed policy in temporary folders.
Independent full-source bit-for-bit rebuild equality remains unverified.

## 0.155.1-termux.1 — historical, incomplete bundle

A subsequent real model session failed to start `codex-code-mode-host`, which was
omitted from this package. The mock agent test below exercised direct tools only,
so its success did not establish Code Mode support. The responses proxy was also
absent. The original login status below is historical, not the current phone state.

Date: 2026-09-21 (Asia/Seoul).

### Pinned source and build

- Upstream stable release: `rust-v0.155.1`, published 2026-09-18.
- Upstream commit: `be2951ea34f0d295ed0becf97079f92fa5f6950e`.
- Rust 1.95.0 with the checked-in Android `std::fs::File` locking patch.
- Android NDK r29 / 29.0.14206865, Android API 28, ARM64/Bionic.
- All 1,333 external Cargo package versions, sources and checksums match the upstream
  stable lockfile. Workspace package versions are synchronized to 0.155.1.
- `just fmt`, `git diff --check`, shell/Python syntax and workflow lint pass.
- `just bazel-lock-update` completes with no generated lockfile changes.
- Host validation: `just test -p codex-cli --lib`, **17 passed, 0 failed**.

### Physical device

- Android 17, `arm64-v8a` / `aarch64`, 4096-byte kernel pages.
  ELF 16 KiB alignment is checked separately; execution on a 16 KiB kernel is
  not claimed by this device test.
- Termux 0.118.3; the running app reports `TERMUX_APK_RELEASE=F_DROID`.
- Installed prefix: `/data/data/com.termux/files/usr`.
- Native execution in Termux; no proot, container or glibc distribution.

The standalone patched-standard-library probe passes exclusive/shared contention,
blocking-method acquisition and unlock checks across real Android processes.
The NDK C atomic probe also passes on the same device, including all nine outlined
ARM64 atomic symbols that were missing from the initial build-std link. The pinned
NDK compiler runtime supplies these implementations through `termux/linker.sh`.
Stock Rust 1.95.0 returned `Unsupported` and prevented app-server startup; the
patch enables actual `flock` operations rather than bypassing the lock.

The installer was also exercised in a disposable Termux prefix with an existing
`codex` symlink. The original target retained its sentinel content, the backup
retained the symlink, and the replacement launcher was a regular executable.

### Release binary checks

The earlier CLI-only [GitHub Actions build](https://github.com/reproducepark/codex-termux/actions/runs/35533927192)
passed at source commit `e5568591ac4be8fe99ff03c6b21bf11989a5dc76`.
The release keeps this compilation provenance when installer/documentation files
are finalized in a later packaging commit.

- Archive, executable and installer SHA-256 verification: pass.
- Installed phone executable matches the CI binary SHA-256 below.
- ELF: AArch64 Android PIE, `/system/bin/linker64`; all LOAD alignments `0x4000`.
- Dynamic dependencies: only `libdl.so`, `libm.so`, and `libc.so`.
- `codex --version`: `codex-cli 0.155.1`, with no unsupported-lock warning.
- Included CI-built file-lock/NDK-atomic probe: pass on the phone.
- App-server initialization: pass.
- Real shell, file write/read, ripgrep, pipes, UTF-8 Korean text: pass.
- Executable `#!/usr/bin/env bash` script through Codex: pass.
- PTY stdin/stdout and resize to 32 rows / 100 columns: pass.
- Real `codex exec` with a loopback mock Responses service: pass. A model tool
  request executed a shell command, wrote/read `agent-test.txt`, returned its
  output in the next HTTP request, and produced `TERMUX_AGENT_OK`. The test also
  independently read back `AGENT_FILE_OK` from the phone's file.
- TUI over a real phone PTY: welcome/login screen rendered; keyboard navigation
  changed the login selection; Ctrl-C exited the application.
- `codex login status`: `Not logged in`, as expected for the user's unconfigured
  account. No authenticated inference was performed.

Binary SHA-256:

```
0451a0de85e0dd68ea70c2fb53b728865c1b1416b769746db798358bac94f0f8
```

### Scope and limitations

The build and tests do not contain or transfer account credentials. Real OpenAI
inference and authenticated account flows require the user's own login and are
not included in these account-free tests. Optional integrations such as MCP
servers, audio, browser authentication and image clipboard are not certified by
this validation. Android is not a supported Codex OS-sandbox target; execution
checks explicitly use an unsandboxed policy inside disposable test directories.

The repository provides a pinned, repeatable source/build recipe and build
provenance. Bit-for-bit equality between different host operating systems or
independent rebuilds has not been verified.
