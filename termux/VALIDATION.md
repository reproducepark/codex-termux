# Validation of 0.155.1-termux.1

Date: 2026-09-21 (Asia/Seoul).

## Pinned source and build

- Upstream stable release: `rust-v0.155.1`, published 2026-09-18.
- Upstream commit: `be2951ea34f0d295ed0becf97079f92fa5f6950e`.
- Rust 1.95.0 with the checked-in Android `std::fs::File` locking patch.
- Android NDK r29 / 29.0.14206865, Android API 28, ARM64/Bionic.
- All external Cargo package versions, sources and checksums match the upstream
  stable lockfile. Workspace package versions are synchronized to 0.155.1.
- `just fmt`, `git diff --check`, shell/Python syntax and workflow lint pass.
- `just bazel-lock-update` completes with no generated lockfile changes.
- Host validation: `just test -p codex-cli --lib`, **17 passed, 0 failed**.

## Physical device

- Android 17, `arm64-v8a` / `aarch64`.
- Termux 0.118.3; the running app reports `TERMUX_APK_RELEASE=F_DROID`.
- Installed prefix: `/data/data/com.termux/files/usr`.
- Native execution in Termux; no proot, container or glibc distribution.

The standalone patched-standard-library probe passes exclusive/shared contention,
blocking-method acquisition and unlock checks across real Android processes.
Stock Rust 1.95.0 returned `Unsupported` and prevented app-server startup; the
patch enables actual `flock` operations rather than bypassing the lock.

Full release-binary checks are pending the final CI artifact.

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
