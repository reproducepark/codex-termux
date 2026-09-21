#!/data/data/com.termux/files/usr/bin/bash
# Install a locally downloaded and checksum-verified release directory.
set -euo pipefail
prefix=${PREFIX:-/data/data/com.termux/files/usr}
source_dir=${1:?Usage: bash install.sh /path/to/extracted-release}
[[ $(uname -m) == aarch64 ]] || { echo 'This package requires ARM64/aarch64.' >&2; exit 1; }
[[ -d $prefix && -x $prefix/bin/bash ]] || { echo 'Run this inside Termux.' >&2; exit 1; }
for name in codex codex-code-mode-host codex-responses-api-proxy termux-file-lock-probe; do
  [[ -f $source_dir/$name ]] || { echo "Missing executable: $name" >&2; exit 1; }
done
for name in git rg curl; do
  command -v "$name" >/dev/null || { echo 'Install dependencies: pkg install ca-certificates git ripgrep curl termux-exec' >&2; exit 1; }
done
for dependency in "$prefix/etc/tls/cert.pem" "$prefix/lib/libtermux-exec.so"; do
  [[ -r $dependency ]] || { echo "Missing $dependency; run: pkg install ca-certificates termux-exec" >&2; exit 1; }
done
(cd "$source_dir" && sha256sum --strict -c BINARY_SHA256SUMS)
base="$prefix/libexec/codex-termux"
mkdir -p "$base/releases" "$prefix/bin"
release_dir=$(mktemp -d "$base/releases/0.155.1-termux.2.XXXXXX")
launcher_tmp=$(mktemp "$prefix/bin/.codex-termux.XXXXXX")
current_tmp="$base/.current.$$"
probe_file=$(mktemp "$prefix/tmp/codex-install-lock.XXXXXX")
keep_release=0
cleanup() {
  [[ ! -f $launcher_tmp ]] || unlink "$launcher_tmp"
  [[ ! -L $current_tmp ]] || unlink "$current_tmp"
  [[ ! -f $probe_file ]] || unlink "$probe_file"
  if [[ $keep_release == 0 ]]; then rm -rf -- "$release_dir"; fi
}
trap cleanup EXIT
# Stage inside Termux before execution: Android shared Downloads may be noexec.
for name in codex codex-code-mode-host codex-responses-api-proxy termux-file-lock-probe; do
  install -m 755 "$source_dir/$name" "$release_dir/$name"
done
for name in build-info.json BINARY_SHA256SUMS; do
  install -m 644 "$source_dir/$name" "$release_dir/$name"
done
(cd "$release_dir" && sha256sum --strict -c BINARY_SHA256SUMS)
"$release_dir/codex" --version
"$release_dir/codex-code-mode-host" --help >/dev/null
"$release_dir/codex-responses-api-proxy" --help >/dev/null
"$release_dir/termux-file-lock-probe" "$probe_file"
# Switch the whole set together; the host resolves alongside the real CLI path.
ln -s "$release_dir" "$current_tmp"
mv -fT "$current_tmp" "$base/current"
keep_release=1
launcher="$prefix/bin/codex"
if [[ -e $launcher || -L $launcher ]] && ! grep -q 'codex-termux launcher' "$launcher"; then
  cp -Pp "$launcher" "$launcher.before-termux-$(date +%Y%m%d%H%M%S)"
fi
cat > "$launcher_tmp" <<'LAUNCHER'
#!/data/data/com.termux/files/usr/bin/bash
# codex-termux launcher
set -e
export PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
export TMPDIR="${TMPDIR:-$PREFIX/tmp}"
export SHELL="${SHELL:-$PREFIX/bin/bash}"
export SSL_CERT_FILE="${SSL_CERT_FILE:-$PREFIX/etc/tls/cert.pem}"
export SSL_CERT_DIR="${SSL_CERT_DIR:-$PREFIX/etc/tls/certs}"
# Codex clears inherited LD_* variables during process hardening. Restore only
# Termux's own exec shim in tool subprocesses so /usr/bin/env shebangs work.
termux_exec="$PREFIX/lib/libtermux-exec.so"
if [[ -f $termux_exec ]]; then
    exec "$PREFIX/libexec/codex-termux/current/codex" \
        -c "shell_environment_policy.set.LD_PRELOAD=\"$termux_exec\"" "$@"
fi
exec "$PREFIX/libexec/codex-termux/current/codex" "$@"
LAUNCHER
chmod 755 "$launcher_tmp"
mv -f "$launcher_tmp" "$launcher"
# Explicit bash also lets the packaging test exercise this on a Linux runner.
"$prefix/bin/bash" "$launcher" --version
