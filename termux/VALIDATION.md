# Validation of 0.155.1-termux.1

Date: 2026-09-21 (Asia/Seoul).

## Pinned source and build

- Upstream stable release: `rust-v0.155.1`, published 2026-09-18.
- Upstream commit: `be2951ea34f0d295ed0becf97079f92fa5f6950e`.
- Rust 1.95.0 with the checked-in Android `std::fs::File` locking patch.
- Android NDK r29 / 29.0.14206865, Android API 28, ARM64/Bionic.
- All 1,333 external Cargo package versions, sources and checksums match the upstream
  stable lockfile. Workspace package versions are synchronized to 0.155.1.
- `just fmt`, `git diff --check`, shell/Python syntax and workflow lint pass.
- `just bazel-lock-update` completes with no generated lockfile changes.
- Host validation: `just test -p codex-cli --lib`, **17 passed, 0 failed**.

## Physical device

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

## Release binary checks

The complete [GitHub Actions build](https://github.com/reproducepark/codex-termux/actions/runs/35533927192)
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

## Scope and limitations

The build and tests do not contain or transfer account credentials. Real OpenAI
inference and authenticated account flows require the user's own login and are
not included in these account-free tests. Optional integrations such as MCP
servers, audio, browser authentication and image clipboard are not certified by
this validation. Android is not a supported Codex OS-sandbox target; execution
checks explicitly use an unsandboxed policy inside disposable test directories.

The repository provides a pinned, repeatable source/build recipe and build
provenance. Bit-for-bit equality between different host operating systems or
independent rebuilds has not been verified.
