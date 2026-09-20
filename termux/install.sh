#!/data/data/com.termux/files/usr/bin/bash
# Install a locally downloaded and checksum-verified release directory.
set -euo pipefail
prefix=${PREFIX:-/data/data/com.termux/files/usr}
source_dir=${1:?Usage: bash install.sh /path/to/extracted-release}
[[ $(uname -m) == aarch64 ]] || { echo 'This package requires ARM64/aarch64.' >&2; exit 1; }
[[ -d $prefix && -x $prefix/bin/bash ]] || { echo 'Run this inside Termux.' >&2; exit 1; }
[[ -f $source_dir/codex ]] || { echo 'Missing codex executable.' >&2; exit 1; }
"$source_dir/codex" --version
mkdir -p "$prefix/libexec/codex-termux" "$prefix/bin"
binary_tmp=$(mktemp "$prefix/libexec/codex-termux/.codex.XXXXXX")
launcher_tmp=$(mktemp "$prefix/bin/.codex-termux.XXXXXX")
trap 'for temporary_file in "$binary_tmp" "$launcher_tmp"; do if [[ -f $temporary_file ]]; then unlink "$temporary_file"; fi; done' EXIT
install -m 755 "$source_dir/codex" "$binary_tmp"
mv -f "$binary_tmp" "$prefix/libexec/codex-termux/codex"
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
    exec "$PREFIX/libexec/codex-termux/codex" \
        -c "shell_environment_policy.set.LD_PRELOAD=\"$termux_exec\"" "$@"
fi
exec "$PREFIX/libexec/codex-termux/codex" "$@"
LAUNCHER
chmod 755 "$launcher_tmp"
mv -f "$launcher_tmp" "$launcher"
"$launcher" --version
