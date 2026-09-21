# Codex CLI for Termux F-Droid (ARM64)

This community build targets the **native Android/Bionic** environment used by
Termux F-Droid, without proot or a Linux distribution. It is based on OpenAI's
stable **0.155.1** release (`rust-v0.155.1`), checked on 2026-09-21.

- Upstream commit: `be2951ea34f0d295ed0becf97079f92fa5f6950e`
- Rust: **1.95.0**, target `aarch64-linux-android`, with the checked-in Android file-lock patch to `std`
- Android NDK: **r29 / 29.0.14206865**, API level **28**
- ELF: Android PIE, `/system/bin/linker64`, 16 KiB page alignment
- Cargo dependencies: committed `codex-rs/Cargo.lock`; builds use `--locked`

## Install on the phone

Use Termux F-Droid on an ARM64 device running Android 9 or newer. Android 17 with
Termux 0.118.3 (`TERMUX_APK_RELEASE=F_DROID`) is the validation target.

```bash
pkg install ca-certificates git ripgrep curl termux-exec
```

Download the archive, `SHA256SUMS`, and `install.sh` from this fork's GitHub
release. In their download directory:

```bash
sha256sum --ignore-missing -c SHA256SUMS
mkdir -p codex-termux-release
tar -xzf codex-0.155.1-termux.2-aarch64.tar.gz -C codex-termux-release
bash install.sh "$PWD/codex-termux-release"
codex --version
codex login --device-auth
codex
```

The installer stages all three native executables in a versioned directory under
`$PREFIX/libexec/codex-termux/releases/`, switches `current` as one set,
and installs a launcher at `$PREFIX/bin/codex`. It backs up an existing unrelated launcher.
The launcher supplies Termux certificate, shell, and temporary-directory defaults.
It also sets the known Termux `libtermux-exec.so` path for shell tool subprocesses
using a command-line environment policy override: Codex's startup hardening clears
`LD_PRELOAD`, which otherwise breaks common `#!/usr/bin/env` scripts on Android.
No arbitrary inherited preload value is restored. It does not write your Codex
configuration or change sandbox/approval policies.

Android is not an upstream supported OS sandbox. Do not assume the desktop
Linux sandbox operates here. If a command requires execution without Codex's OS
sandbox, select it explicitly (for example `codex --sandbox danger-full-access`)
and work inside a dedicated project directory. Android app isolation still applies;
this setting grants access to the Termux app's accessible files, not Android root.

## Rebuild on Linux x86_64 or GitHub Actions

Install Git, Rustup, CMake, Ninja, Perl, Make, patch, Python 3.12+.
Bindgen uses Clang/libclang 21 and Android headers from the pinned NDK.
The complete bundle builds V8 from source and requires Linux x86_64. Use the
GitHub Actions workflow to avoid compiling on a laptop. Obtain the exact NDK
revision above via the Android SDK manager or Google's NDK archive. Then:

```bash
git clone --branch termux/0.155.1 https://github.com/reproducepark/codex-termux.git
cd codex-termux
# For a release rebuild, check out its immutable tag:
git checkout v0.155.1-termux.2
export ANDROID_NDK_HOME=/absolute/path/to/android-ndk-r29
bash termux/build.sh
```

The first optimized build, including V8, is substantial. V8 and its Chromium
compiler inputs are pinned by the locked crate; Android auxiliary repositories
are checked out at the revisions in its `v8/DEPS`, and NDK r29 is reused. The
published V8 crate omits Android build scripts, ICU build data and Chromium Rust
sources; `prepare-v8.py` restores these from the exact upstream submodule
revisions. The script defaults to two concurrent
Cargo jobs to limit peak memory; set `CARGO_BUILD_JOBS` explicitly to override.
Release optimization and thin LTO are retained; unused debug tables are disabled
because the distributed executable is stripped.

The output is `termux/dist/`, containing all three stripped native executables, a
compressed release archive, `SHA256SUMS`, per-binary checksums, ELF metadata, and `build-info.json`.
The latter records the exact fork commit, toolchain, std patch hash, lockfile digest,
dirty-tree state and each binary digest. The source is built on a host and the executables run
natively on the phone; this is not an on-phone source compilation recipe.

The **Termux ARM64** GitHub Actions workflow runs the same script from a fresh
Ubuntu host with the pinned NDK. This is a pinned, repeatable source/build procedure;
byte-for-byte equality between independent builds is **not claimed**. Archive timestamps and ownership
are normalized.

## Patch scope

Rust 1.95.0's stock Android standard library returns `Unsupported` for `File::lock`,
`try_lock`, shared locks, and unlock. This prevents real Codex app-server startup,
PATH helper creation, and rollout/history locking even when `--version` works.
The checked-in patch enables the existing Unix `flock` implementation on Android
for all five methods; it does not skip locking. `prepare-toolchain.py` verifies the
original source SHA-256 and creates a private sysroot overlay. The original Rust
installation is not modified. Cargo's `-Z build-std` plumbing is enabled using
`RUSTC_BOOTSTRAP=1`, while both compiler and rust-src stay pinned to 1.95.0.
`file-lock-probe` exercises exclusive/shared contention and unlock on the phone.
It also calls NDK-compiled C atomics. The linker wrapper adds the pinned NDK's
compiler runtime archive for outlined ARM64 atomic helpers omitted by the
Rust-only `build-std` compiler-builtins. This small probe is linked before the
large CLI so runtime linkage errors fail early.

Android-only `openssl-sys` dependencies in all three executable packages enable
vendored OpenSSL, including when each helper is compiled independently. They
avoid a host OpenSSL installation or a matching Termux libssl ABI.
The release tag's lockfile still contained `0.0.0` workspace package versions;
these are synchronized to `0.155.1`. External package versions remain pinned.
Upstream sandbox defaults and process hardening are preserved.

## Validation

`smoke.py` drives the installed binary's app-server over stdin JSON-RPC. It checks
initialization, a real shell, UTF-8 file write/read, ripgrep, a pipe, and PTY input,
output and resize. It uses an explicit unsandboxed policy only for its disposable
test commands, without modifying user configuration. No OpenAI credential or
model request is involved in this test.

```bash
python3 termux/smoke.py -- codex app-server
```

Run it with a disposable `CODEX_HOME` and working directory. A host can prefix the
command with SSH to a connected phone.

For a local test, create the disposable directories explicitly:

```bash
test_root=$(mktemp -d "$HOME/codex-termux-test.XXXXXX")
mkdir "$test_root/home" "$test_root/work"
cd "$test_root/work"
export CODEX_HOME="$test_root/home"
```

`agent-smoke.py` additionally serves a loopback Responses API and verifies an
actual `codex exec` tool-call cycle. In a disposable directory, with a disposable
`CODEX_HOME` outside the system temporary directory:

```bash
python3 /path/to/repo/termux/agent-smoke.py --port 54247 -- \
  codex exec --skip-git-repo-check --sandbox danger-full-access \
  -m termux-smoke \
  -c 'model_provider="termux_test"' \
  -c 'model_providers.termux_test.name="Termux smoke"' \
  -c 'model_providers.termux_test.base_url="http://127.0.0.1:54247/v1"' \
  -c 'model_providers.termux_test.wire_api="responses"' \
  -c 'model_providers.termux_test.requires_openai_auth=false' \
  -c 'model_providers.termux_test.supports_websockets=false' \
  'Run the controlled smoke test'
```

For host-driven phone validation, forward the loopback port with `adb reverse`
and prefix the Codex command with SSH. The test writes `agent-test.txt` in its cwd.
It requires no real account or model, and validates tool execution rather than
model quality. See `VALIDATION.md` for release evidence and remaining limitations.

## Component coverage and validation

See [COMPONENTS.md](COMPONENTS.md) for the complete runtime audit and platform
exclusions. Revision 1 omitted the Code Mode host and responses proxy. Revision 2
adds both and a Code Mode-specific test. Its physical-device validation is deferred;
see [VALIDATION.md](VALIDATION.md) for the exact completed checks.

When the phone is available, run the included account-free checks from the
extracted release directory:

```bash
pkg install python
python3 verify-device.py
```

This uses a temporary Codex home and project, a local mock Responses endpoint,
and an explicit unsandboxed test policy; it does not use your OpenAI login or
change your normal configuration. It verifies app-server, shell/PTY, direct
calls, and Code Mode JavaScript plus nested shell calls. Authenticated model
behavior and optional integrations still require separate checks.
