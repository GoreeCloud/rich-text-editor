#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ $(uname -s) == Linux ]] || { echo 'Build this package on Linux.' >&2; exit 1; }
cargo build --release --locked
version=$(sed -n 's/^version = "\([^"]*\)"/\1/p' Cargo.toml | head -1)
name="goreecloud-rich-text-editor-$version-linux-$(uname -m)"
mkdir -p dist/linux
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
mkdir -p "$stage/$name/bin" "$stage/$name/share/applications" "$stage/$name/share/icons/hicolor/512x512/apps"
install -m755 "${CARGO_TARGET_DIR:-target}/release/goreecloud_rich_text_editor" "$stage/$name/bin/goreecloud_rich_text_editor"
install -m644 packaging/linux/com.goreecloud.richtexteditor.desktop "$stage/$name/share/applications/"
install -m644 assets/branding/app-icon.png "$stage/$name/share/icons/hicolor/512x512/apps/com.goreecloud.richtexteditor.png"
install -m644 LICENSE "$stage/$name/"
install -m644 THIRD_PARTY.md "$stage/$name/"
ldd "$stage/$name/bin/goreecloud_rich_text_editor" > "$stage/$name/runtime-libraries.txt"
if grep -q 'not found' "$stage/$name/runtime-libraries.txt"; then cat "$stage/$name/runtime-libraries.txt" >&2; exit 1; fi
tar -C "$stage" -czf "dist/linux/$name.tar.gz" "$name"
# Verify shipped legal notices, not just the build inputs.
tar -tf "dist/linux/$name.tar.gz" | grep -Fx "$name/LICENSE" >/dev/null
tar -tf "dist/linux/$name.tar.gz" | grep -Fx "$name/THIRD_PARTY.md" >/dev/null
(cd dist/linux && sha256sum "$name.tar.gz" > "$name.tar.gz.sha256")
printf '%s\n' "dist/linux/$name.tar.gz"
