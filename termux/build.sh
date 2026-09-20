#!/usr/bin/env bash
# Cross-compile the pinned Codex release for Termux F-Droid (Android ARM64).
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
: "${ANDROID_NDK_HOME:?Set ANDROID_NDK_HOME to Android NDK r29 (29.0.14206865)}"
grep -q '^Pkg.Revision = 29.0.14206865$' "$ANDROID_NDK_HOME/source.properties" || {
  echo 'Expected Android NDK r29 / 29.0.14206865' >&2; exit 1;
}
case "$(uname -s)" in
  Darwin) host=darwin-x86_64 ;;
  Linux) host=linux-x86_64 ;;
  *) echo 'Use a Linux x86_64 or macOS build host' >&2; exit 1 ;;
esac
ndk_bin="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/$host/bin"
export PATH="$ndk_bin:$PATH"
export ANDROID_NDK_ROOT="$ANDROID_NDK_HOME"
export CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER="$ndk_bin/aarch64-linux-android28-clang"
export CC_aarch64_linux_android="$CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER"
export CXX_aarch64_linux_android="$ndk_bin/aarch64-linux-android28-clang++"
export AR_aarch64_linux_android="$ndk_bin/llvm-ar"
export CARGO_TARGET_AARCH64_LINUX_ANDROID_RUSTFLAGS='-C link-arg=-Wl,-z,max-page-size=16384'
export CARGO_INCREMENTAL=0
export SOURCE_DATE_EPOCH="$(git -C "$repo" show -s --format=%ct HEAD)"
for command in cargo rustup cmake ninja perl make python3; do
  command -v "$command" >/dev/null || { echo "Missing tool: $command" >&2; exit 1; }
done
rustup toolchain install 1.95.0 --profile minimal
rustup target add --toolchain 1.95.0 aarch64-linux-android
cd "$repo/codex-rs"
cargo +1.95.0 build --locked --release --target aarch64-linux-android -p codex-cli --bin codex "$@"
binary="${CARGO_TARGET_DIR:-target}/aarch64-linux-android/release/codex"
out="$repo/termux/dist"
mkdir -p "$out"
cp "$binary" "$out/codex"
"$ndk_bin/llvm-strip" "$out/codex"
"$ndk_bin/llvm-readelf" -h -l -d "$out/codex" > "$out/elf.txt"
python3 "$repo/termux/package.py" "$repo" "$out"
echo "Build and checksums: $out"
