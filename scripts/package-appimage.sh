#!/usr/bin/env bash
# Build on Ubuntu 22.04 (glibc 2.35); graphics drivers remain system-provided.
set -euo pipefail
cd "$(dirname "$0")/.."
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || { echo 'Build on Linux x86_64.' >&2; exit 1; }
cargo build --release --locked
version=$(sed -n 's/^version = "\([^"]*\)"/\1/p' Cargo.toml | head -1)
out="$PWD/dist/linux"
mkdir -p "$out"
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
tool="$stage/linuxdeploy.AppImage"
curl --fail --location --retry 3 --proto '=https' --proto-redir '=https' \
  https://github.com/linuxdeploy/linuxdeploy/releases/download/1-alpha-20251107-1/linuxdeploy-x86_64.AppImage -o "$tool"
echo "c20cd71e3a4e3b80c3483cef793cda3f4e990aca14014d23c544ca3ce1270b4d  $tool" | sha256sum -c -
chmod +x "$tool"
appdir="$stage/GoreeCloud Rich Text Editor.AppDir"
mkdir -p "$appdir/usr/share/doc/goreecloud-rich-text-editor"
cp LICENSE THIRD_PARTY.md "$appdir/usr/share/doc/goreecloud-rich-text-editor/"
mkdir -p "$appdir/usr/share/X11"
cp -a /usr/share/X11/locale "$appdir/usr/share/X11/"
# License notices for bundled shared libraries and their Compose data.
for package in libxkbcommon0 libxkbcommon-x11-0 libxau6 libxdmcp6 libxcb-xkb1 libbsd0 libmd0 libx11-data; do
  install -Dm644 "/usr/share/doc/$package/copyright" "$appdir/usr/share/doc/$package/copyright"
done
convert assets/branding/app-icon.png -resize 512x512 "$stage/com.goreecloud.richtexteditor.png"
export APPIMAGE_EXTRACT_AND_RUN=1
export OUTPUT="$out/goreecloud-rich-text-editor-$version-x86_64.AppImage"
export VERSION="$version"
"$tool" --appdir "$appdir" --executable "${CARGO_TARGET_DIR:-target}/release/goreecloud_rich_text_editor" \
  --desktop-file packaging/linux/com.goreecloud.richtexteditor.desktop \
  --icon-file "$stage/com.goreecloud.richtexteditor.png" --custom-apprun packaging/linux/AppRun --output appimage
chmod +x "$OUTPUT"
# Inspect the packaged payload, not only the original executable.
(cd "$stage" && "$OUTPUT" --appimage-extract >/dev/null)
test -x "$stage/squashfs-root/AppRun"
# Smoke-test the *extracted* AppImage launcher with a stub program so the
# check exercises the shipped AppRun without starting the GUI or accessing notes.
probe="$stage/launcher-smoke"
mkdir -p "$probe/usr/bin" "$probe/usr/share/X11/locale"
cp "$stage/squashfs-root/AppRun" "$probe/AppRun"
cat > "$probe/usr/bin/goreecloud_rich_text_editor" <<'LAUNCH_PROBE'
#!/bin/sh
set -eu
[ "$#" -eq 2 ] && [ "$1" = "--goreecloud-launcher-probe" ] && [ "$2" = "argument with spaces" ] && [ "$XLOCALEDIR" = "$GOREECLOUD_EXPECTED_XLOCALEDIR" ]
LAUNCH_PROBE
chmod +x "$probe/AppRun" "$probe/usr/bin/goreecloud_rich_text_editor"
GOREECLOUD_EXPECTED_XLOCALEDIR="$probe/usr/share/X11/locale" "$probe/AppRun" --goreecloud-launcher-probe "argument with spaces"
echo "AppImage launcher smoke test passed"
payload="$stage/squashfs-root/usr/bin/goreecloud_rich_text_editor"
LD_LIBRARY_PATH="$stage/squashfs-root/usr/lib" ldd "$payload" > "$OUTPUT.libraries.txt"
if grep -q 'not found' "$OUTPUT.libraries.txt"; then cat "$OUTPUT.libraries.txt" >&2; exit 1; fi
objdump -T "$payload" | sed -n 's/.*(GLIBC_\([0-9.]*\)).*/\1/p' | sort -Vu > "$OUTPUT.glibc.txt"
max_glibc=$(tail -1 "$OUTPUT.glibc.txt")
[[ $(printf '%s\n' 2.35 "$max_glibc" | sort -V | tail -1) == 2.35 ]] \
  || { echo "Requires glibc $max_glibc, above the 2.35 baseline" >&2; exit 1; }
(cd "$out" && sha256sum "$(basename "$OUTPUT")" > "$(basename "$OUTPUT").sha256")
printf 'AppImage: %s (glibc %s)\n' "$OUTPUT" "$max_glibc"
