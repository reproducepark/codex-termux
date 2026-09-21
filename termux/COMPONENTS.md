# Runtime component audit for 0.155.1-termux.2

Audited against upstream `rust-v0.155.1` at
`be2951ea34f0d295ed0becf97079f92fa5f6950e`:
`.github/workflows/rust-release.yml`, `scripts/codex_package/layout.py`, and
`codex-rs/install-context/src/lib.rs`.

| Component | Android package decision |
| --- | --- |
| `codex` | Build the native Android CLI; includes `codex app-server`, MCP server, exec and TUI entrypoints. |
| `codex-code-mode-host` | Required companion, built for Android and installed beside the actual CLI. Missing in termux.1. |
| `codex-responses-api-proxy` | Additional upstream release executable, built and installed beside the CLI. Missing in termux.1; not needed for an ordinary direct OpenAI connection. |
| V8 + ICU data | V8 150.4.0 built from source with the upstream sandbox feature enabled. ICU data is embedded by `deno_core_icudata`; there is no external `icudtl.dat` to install. |
| `rg` | Use native Termux `ripgrep` via PATH; installer checks it. Desktop prebuilt binaries are not Android/Bionic binaries. |
| Git, curl, certificates, shell | Native Termux packages; Bash, certificate paths and TMPDIR are supplied by the launcher. |
| `libtermux-exec.so` | Termux package, used in shell-tool subprocesses for `/usr/bin/env` shebang compatibility. |
| Patched `codex-zsh` | Optional `shell_zsh_fork` backend (disabled by default). Not provided for Android. Ordinary Termux Bash execution is the supported shell path; ordinary zsh is not a substitute for this patched helper. |
| `bwrap` | Linux-only sandbox implementation is compiled out on Android. Not packaged; adding its executable would not enable Android OS sandbox support. |
| Windows command runner / sandbox setup | Windows only, not applicable. |
| Standalone `codex-app-server` | Separate upstream product bundle; CLI already exposes `codex app-server`. |
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

The termux.1 device tests did **not** exercise Code Mode. A real user session
exposed the omitted helper. Those older tests must not be interpreted as full
runtime validation. Physical-device validation of termux.2 is deferred at the
user's request; successful CI compilation/packaging does not establish Android
V8 runtime, JIT, or authenticated model behavior.
