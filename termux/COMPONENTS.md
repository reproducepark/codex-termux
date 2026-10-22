# Runtime component audit for 0.163.0-termux.1

Audited against upstream `rust-v0.163.0` at
`129b8ec7ee6f4511557a4856279f529025c25af4`:
`.github/workflows/rust-release.yml`, `scripts/codex_package/layout.py`, and
`codex-rs/install-context/src/lib.rs`.

| Component | Android package decision |
| --- | --- |
| `codex` | Build the native Android CLI; includes `codex app-server`, MCP server, exec and TUI entrypoints. |
| `codex-code-mode-host` | Required companion, built for Android and installed beside the actual CLI. |
| `codex-responses-api-proxy` | Additional upstream release executable, built and installed beside the CLI. Not needed for an ordinary direct OpenAI connection. |
| V8 + ICU data | V8 150.4.0 built from source with the upstream sandbox feature enabled. ICU data is embedded by `deno_core_icudata`; there is no external `icudtl.dat` to install. |
| `rg` | Use native Termux `ripgrep` via PATH; installer checks it. Desktop prebuilt binaries are not Android/Bionic binaries. |
| Git, curl, certificates, shell | Native Termux packages; Bash, certificate paths and TMPDIR are supplied by the launcher. |
| `libtermux-exec.so` | Termux package, used in shell-tool subprocesses for `/usr/bin/env` shebang compatibility. |
| `bwrap` | Linux-only sandbox implementation is compiled out on Android. Not packaged; adding its executable would not enable Android OS sandbox support. |
| Windows command runner / sandbox setup | Windows only, not applicable. |
| Standalone `codex-app-server` | Separate upstream product bundle; CLI already exposes `codex app-server`. |
| `codex-voice-host` + native voice runtime | New desktop voice bundle; upstream stages desktop runtimes separately. Not supplied or supported by this Android port. Text/Code Mode operation does not require it. |
| MCP servers / Node / Python | User-selected integrations and project runtimes, not prerequisites for the built-in native Code Mode host. Not bundled or certified by this port. |

`check-bundle.py` rejects a release if a required executable is missing, its
checksum differs, its interpreter/dependencies are not Android system libraries,
its ELF LOAD alignment is below 16 KiB, or the archive omits a required file.
The installer verifies all binary checksums and checks CLI/helper startup before
switching the active complete installation directory.

`agent-smoke.py --code-mode` requires a real JavaScript result plus a nested shell
operation and a returned tool result. It cannot pass merely because direct shell
tools work. Run Codex with `--enable code_mode_only` and a disposable `CODEX_HOME`
for that check. The existing direct-tool mode remains a separate test.

## Verification boundary

0.163.0 requires fresh Android runtime validation. The previous 0.162.1 build
passed physical-device Code Mode, proxy routing and authenticated model tests;
those results do not validate this revision. Rust 1.95.0, V8 150.4.0 and the
Android NDK remain pinned. CLI, Code Mode host and responses proxy are built and
packaged together. Native voice/WebRTC is not certified for Android.
