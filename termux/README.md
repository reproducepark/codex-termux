# Codex CLI for Termux F-Droid (ARM64)

This community build targets the **native Android/Bionic** environment used by
Termux F-Droid, without proot or a Linux distribution. It is based on OpenAI's
stable **0.155.1** release (`rust-v0.155.1`), checked on 2026-09-21.

- Upstream commit: `be2951ea34f0d295ed0becf97079f92fa5f6950e`
- Rust: **1.95.0**, target `aarch64-linux-android`
- Android NDK: **r29 / 29.0.14206865**, API level **28**
- ELF: Android PIE, `/system/bin/linker64`, 16 KiB page alignment
- Cargo dependencies: committed `codex-rs/Cargo.lock`; builds use `--locked`

## Install on the phone

Use Termux F-Droid on an ARM64 device running Android 9 or newer. Android 17 with
Termux 0.118.3 (`TERMUX_APK_RELEASE=F_DROID`) is the validation target.

```bash
pkg install ca-certificates git ripgrep curl
```

Download the archive, `SHA256SUMS`, and `install.sh` from this fork's GitHub
release. In their download directory:

```bash
sha256sum --ignore-missing -c SHA256SUMS
mkdir -p codex-termux-release
tar -xzf codex-0.155.1-termux.1-aarch64.tar.gz -C codex-termux-release
bash install.sh "$PWD/codex-termux-release"
codex --version
codex login --device-auth
codex
```

The installer places the native binary at `$PREFIX/libexec/codex-termux/codex`
and a launcher at `$PREFIX/bin/codex`. It backs up an existing unrelated launcher.
The launcher supplies Termux certificate, shell, and temporary-directory defaults;
it does not write your Codex configuration or change permission policies.

Android is not an upstream supported OS sandbox. Do not assume the desktop
Linux sandbox operates here. If a command requires execution without Codex's OS
sandbox, select it explicitly (for example `codex --sandbox danger-full-access`)
and work inside a dedicated project directory. Android app isolation still applies;
this setting grants access to the Termux app's accessible files, not Android root.

## Rebuild on macOS or Linux x86_64

Install Git, Rustup, CMake, Ninja, Perl, Make and Python 3. Obtain the exact NDK
revision above via the Android SDK manager or Google's NDK archive. Then:

```bash
git clone --branch termux/0.155.1 https://github.com/reproducepark/codex-termux.git
cd codex-termux
# For a release rebuild, check out its immutable tag:
git checkout v0.155.1-termux.1
export ANDROID_NDK_HOME=/absolute/path/to/android-ndk-r29
bash termux/build.sh
```

The output is `termux/dist/`, containing the stripped native executable, a
compressed release archive, `SHA256SUMS`, ELF metadata, and `build-info.json`.
The latter records the exact fork commit, toolchain, lockfile digest, dirty-tree
state and binary digest. The source is built on a host and the executable runs
natively on the phone; this is not an on-phone source compilation recipe.

The **Termux ARM64** GitHub Actions workflow runs the same script from a fresh
Ubuntu host with the pinned NDK. This is a reproducible source/build procedure;
byte-for-byte equality across macOS and Linux hosts is **not claimed**. Host tool
versions and absolute debug paths can differ. Archive timestamps and ownership
are normalized.

## Patch scope

The Android-only `openssl-sys` dependency enables vendored OpenSSL so the binary
does not depend on a host OpenSSL installation or a matching Termux libssl ABI.
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
command with SSH to a connected phone. See `VALIDATION.md` for release evidence
and remaining limitations.
