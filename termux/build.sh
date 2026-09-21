#!/usr/bin/env bash
# Cross-compile the pinned Codex release for Termux F-Droid (Android ARM64).
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
: "${ANDROID_NDK_HOME:?Set ANDROID_NDK_HOME to Android NDK r29 (29.0.14206865)}"
grep -q '^Pkg.Revision = 29.0.14206865$' "$ANDROID_NDK_HOME/source.properties" || {
  echo 'Expected Android NDK r29 / 29.0.14206865' >&2; exit 1;
}
case "$(uname -s)" in
  Linux) host=linux-x86_64 ;;
  *) echo 'The complete V8/Android bundle requires a Linux x86_64 build host (use GitHub Actions).' >&2; exit 1 ;;
esac
ndk_bin="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/$host/bin"
export PATH="$ndk_bin:$PATH"
export ANDROID_NDK_ROOT="$ANDROID_NDK_HOME"
export CODEX_ANDROID_CLANG="$ndk_bin/aarch64-linux-android28-clang"
export CODEX_ANDROID_BUILTINS="$("$CODEX_ANDROID_CLANG" --print-libgcc-file-name)"
[[ -f $CODEX_ANDROID_BUILTINS ]] || { echo 'Missing NDK compiler runtime' >&2; exit 1; }
export CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER="$repo/termux/linker.sh"
export CC_aarch64_linux_android="$CODEX_ANDROID_CLANG"
export CXX_aarch64_linux_android="$ndk_bin/aarch64-linux-android28-clang++"
export AR_aarch64_linux_android="$ndk_bin/llvm-ar"
export CARGO_TARGET_AARCH64_LINUX_ANDROID_RUSTFLAGS='-C link-arg=-Wl,-z,max-page-size=16384'
export CARGO_INCREMENTAL=0
# Release artifacts are stripped; omit unused debug tables during compilation.
export CARGO_PROFILE_RELEASE_DEBUG=0
# Keep peak memory bounded on 16 GiB build hosts.
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-2}"
export SOURCE_DATE_EPOCH="$(git -C "$repo" show -s --format=%ct HEAD)"
for command in cargo rustup cmake ninja perl make python3 patch; do
  command -v "$command" >/dev/null || { echo "Missing tool: $command" >&2; exit 1; }
done
rustup toolchain install 1.95.0 --profile minimal --component rust-src
rustup target add --toolchain 1.95.0 aarch64-linux-android
sysroot=$(rustc +1.95.0 --print sysroot)
python3 "$repo/termux/prepare-toolchain.py" "$sysroot" "$repo/termux/.toolchain"
export RUSTC="$repo/termux/.toolchain/bin/rustc-termux"
export RUSTDOC="$repo/termux/.toolchain/bin/rustdoc-termux"
# Stable compiler, using Cargo's unstable build-std plumbing with pinned rust-src.
export RUSTC_BOOTSTRAP=1
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$repo/termux/target}"
cd "$repo/codex-rs"
export V8_FROM_SOURCE=1
export LIBCLANG_PATH="${LIBCLANG_PATH:-/usr/lib/llvm-19/lib}"
export EXTRA_GN_ARGS='default_min_sdk_version=28 android_ndk_api_level=28 symbol_level=0'
cargo +1.95.0 fetch --locked --target aarch64-linux-android
python3 "$repo/termux/prepare-v8.py"
# Catch std/NDK linkage issues before the large CLI build.
cargo +1.95.0 build --locked -Z build-std --release --target aarch64-linux-android \
  --manifest-path "$repo/termux/file-lock-probe/Cargo.toml"
cargo +1.95.0 build --locked -Z build-std --release --target aarch64-linux-android \
  -p codex-code-mode-host --bin codex-code-mode-host \
  -p codex-responses-api-proxy --bin codex-responses-api-proxy \
  -p codex-cli --bin codex "$@"
out="$repo/termux/dist"
mkdir -p "$out"
: > "$out/elf.txt"
for name in codex codex-code-mode-host codex-responses-api-proxy; do
  cp "$CARGO_TARGET_DIR/aarch64-linux-android/release/$name" "$out/$name"
  "$ndk_bin/llvm-strip" "$out/$name"
  "$ndk_bin/llvm-readelf" -h -l -d "$out/$name" >> "$out/elf.txt"
done
cp "$CARGO_TARGET_DIR/aarch64-linux-android/release/termux-file-lock-probe" "$out/"
"$ndk_bin/llvm-strip" "$out/termux-file-lock-probe"
python3 "$repo/termux/package.py" "$repo" "$out"
echo "Build and checksums: $out"
