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
install -m 755 "$source_dir/codex" "$prefix/libexec/codex-termux/codex"
launcher="$prefix/bin/codex"
if [[ -e $launcher ]] && ! grep -q 'codex-termux launcher' "$launcher"; then
  cp -p "$launcher" "$launcher.before-termux-$(date +%Y%m%d%H%M%S)"
fi
cat > "$launcher" <<'LAUNCHER'
#!/data/data/com.termux/files/usr/bin/bash
# codex-termux launcher
set -e
export PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
export TMPDIR="${TMPDIR:-$PREFIX/tmp}"
export SHELL="${SHELL:-$PREFIX/bin/bash}"
export SSL_CERT_FILE="${SSL_CERT_FILE:-$PREFIX/etc/tls/cert.pem}"
export SSL_CERT_DIR="${SSL_CERT_DIR:-$PREFIX/etc/tls/certs}"
exec "$PREFIX/libexec/codex-termux/codex" "$@"
LAUNCHER
chmod 755 "$launcher"
"$launcher" --version
