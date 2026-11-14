#!/usr/bin/env bash
# Smoke-test the executable from the portable Linux tarball without extracting
# arbitrary archive paths. Uses an isolated X11 desktop and notes directory.
set -euo pipefail
cd "$(dirname "$0")/.."
[[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]] || { echo "Linux x86_64 required" >&2; exit 2; }
[[ "$#" -eq 1 && -f "$1" ]] || { echo "Usage: $0 <goreecloud-linux-x86_64.tar.gz>" >&2; exit 2; }
archive=$(realpath "$1")
name=$(basename "$archive")
[[ "$name" =~ ^goreecloud-rich-text-editor-[0-9]+\.[0-9]+\.[0-9]+-linux-x86_64\.tar\.gz$ ]] || {
  echo "Unexpected GoreeCloud Linux tarball filename: $name" >&2; exit 2;
}
python3 -B scripts/audit-release-artifacts.py "$archive"
tmp=$(mktemp -d "${TMPDIR:-/tmp}/goreecloud-tarball-smoke.XXXXXX")
trap 'rm -rf -- "$tmp"' EXIT
bundle="${name%.tar.gz}"
# Stream only the expected application member; never expand untrusted entries.
tar -xOzf "$archive" "$bundle/bin/goreecloud_rich_text_editor" > "$tmp/goreecloud_rich_text_editor"
[[ -s "$tmp/goreecloud_rich_text_editor" ]] || { echo "Missing Linux application binary" >&2; exit 1; }
chmod 700 "$tmp/goreecloud_rich_text_editor"
scripts/smoke-linux-appimage.sh "$tmp/goreecloud_rich_text_editor"
echo "Portable Linux tarball executable GUI smoke test passed"
