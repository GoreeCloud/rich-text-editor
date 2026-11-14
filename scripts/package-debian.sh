#!/usr/bin/env bash
# Produce a disposable, unsigned Debian development package from the validated
# Linux tarball. Keep the existing dpkg package ID for safe in-place upgrades.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v dpkg-deb >/dev/null || { echo 'dpkg-deb required' >&2; exit 1; }
command -v sha256sum >/dev/null || { echo 'sha256sum required' >&2; exit 1; }
[[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]] || { echo 'Requires Linux x86_64' >&2; exit 1; }
version="$(sed -n 's/^version = "\([^"]*\)"/\1/p' Cargo.toml | head -1)"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo 'Unexpected Cargo version' >&2; exit 1; }
run_id="${GITHUB_RUN_ID:-local}"
[[ "$run_id" =~ ^[A-Za-z0-9]+$ ]] || { echo 'Invalid CI ID' >&2; exit 1; }
pkgver="$version~ci$run_id-2"
tarball="dist/linux/goreecloud-rich-text-editor-$version-linux-x86_64.tar.gz"
[[ -f "$tarball" ]] || { echo "Build the Linux tarball first: $tarball" >&2; exit 1; }
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
tar -xzf "$tarball" -C "$stage"
source="$stage/goreecloud-rich-text-editor-$version-linux-x86_64"
binary="$source/bin/goreecloud_rich_text_editor"
desktop="$source/share/applications/com.goreecloud.richtexteditor.desktop"
icon="$source/share/icons/hicolor/512x512/apps/com.goreecloud.richtexteditor.png"
for path in "$binary" "$desktop" "$icon" "$source/LICENSE" "$source/THIRD_PARTY.md"; do
    [[ -f "$path" ]] || { echo "Missing package source: $path" >&2; exit 1; }
done
root="$stage/pkg"
install -D -m755 "$binary" "$root/usr/bin/goreecloud_rich_text_editor"
install -D -m644 "$desktop" "$root/usr/share/applications/com.goreecloud.richtexteditor.desktop"
install -D -m644 "$icon" "$root/usr/share/icons/hicolor/512x512/apps/com.goreecloud.richtexteditor.png"
install -D -m644 "$source/LICENSE" "$root/usr/share/doc/goreecloud-rich-text-editor/LICENSE"
install -D -m644 "$source/THIRD_PARTY.md" "$root/usr/share/doc/goreecloud-rich-text-editor/THIRD_PARTY.md"
mkdir -p "$root/DEBIAN"
cat > "$root/DEBIAN/control" <<EOF
Package: goreecloud-rich-text-editor
Version: $pkgver
Section: editors
Priority: optional
Architecture: amd64
Maintainer: GoreeCloud <admin@goreecloud.com>
Homepage: https://github.com/GoreeCloud/notes
Depends: libc6 (>= 2.35), libfontconfig1, libfreetype6, libxcb1, libxkbcommon0, libxkbcommon-x11-0, libvulkan1
Description: GoreeCloud Notes local-first Markdown and rich-text editor
 Unsigned CI development candidate. The legacy Debian package ID and
 binary/desktop IDs remain stable to avoid disrupting existing installs.
EOF
chmod 0755 "$root" "$root/DEBIAN"
out="dist/linux/goreecloud-notes_$pkgver""_amd64.deb"
dpkg-deb --build --root-owner-group "$root" "$out"
(cd dist/linux && sha256sum "$(basename "$out")" > "$(basename "$out").sha256")
printf 'unsigned development package: %s\n' "$out"
