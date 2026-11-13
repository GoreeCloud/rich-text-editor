#!/bin/zsh
# Replace the running hand-test build (dist-preview) with target/release. It
# runs as dist-preview/GoreeCloud Rich Text Editor.app (so the menu bar says GoreeCloud Rich Text Editor) on the
# saved preview library, or ~/Documents/GoreeCloud Rich Text Editor. The app initializes the
# bundled 开始指南 on first launch, just like an installed build.
# Only this checkout's own binaries are stopped:
# pkill matches this checkout's absolute path. Log: /tmp/goreecloud-rich-text-editor-preview.log
set -e
cd "$(dirname "$0")/.."
preview_library="${GOREECLOUD_RTE_HOME:-$(cat dist-preview/library-path 2>/dev/null || printf '%s' "$HOME/Documents/GoreeCloud Rich Text Editor")}"
# An empty path would put the library in the current directory.
[ -n "$preview_library" ] || { echo "preview.sh: no preview library" >&2; exit 1; }
export GOREECLOUD_RTE_HOME="$preview_library"
app="$PWD/dist-preview/GoreeCloud Rich Text Editor.app"
bin="$app/Contents/MacOS/goreecloud_rich_text_editor"
pkill -f "^$bin" || true
sleep 1
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
cp assets/branding/app-icon.png "$app/Contents/Resources/app-icon.png"
icon_tmp=$(mktemp -d)
iconset="$icon_tmp/app-icon.iconset"
mkdir -p "$iconset"
for s in 16 32 128 256 512; do
  sips -z $s $s assets/branding/app-icon.png --out "$iconset/icon_${s}x${s}.png" >/dev/null
  sips -z $((s * 2)) $((s * 2)) assets/branding/app-icon.png --out "$iconset/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$iconset" -o "$app/Contents/Resources/app-icon.icns"
rm -rf "$icon_tmp"
cp target/release/goreecloud_rich_text_editor "$bin.bin"
# Finder launches must use the same library as this script.
printf '#!/bin/zsh\nexport GOREECLOUD_RTE_HOME=%q\nexec "${0:A:h}/goreecloud_rich_text_editor.bin" "$@"\n' "$preview_library" > "$bin"
chmod +x "$bin"
cat > "$app/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>GoreeCloud Rich Text Editor</string>
  <key>CFBundleDisplayName</key><string>GoreeCloud Rich Text Editor</string>
  <key>CFBundleIdentifier</key><string>local.quietmd.preview</string>
  <key>CFBundleExecutable</key><string>goreecloud_rich_text_editor</string>
  <key>CFBundleIconFile</key><string>app-icon.icns</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>$(sed -n 's/^version = "\(.*\)"/\1/p' Cargo.toml | head -1)</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
  <key>NSDocumentsFolderUsageDescription</key><string>GoreeCloud Rich Text Editor 把文档库放在「文稿」里的 GoreeCloud Rich Text Editor 文件夹。</string>
  <key>CFBundleDocumentTypes</key><array><dict>
    <key>CFBundleTypeName</key><string>Markdown</string>
    <key>CFBundleTypeRole</key><string>Editor</string>
    <key>LSHandlerRank</key><string>Alternate</string>
    <key>LSItemContentTypes</key><array><string>net.daringfireball.markdown</string></array>
    <key>CFBundleTypeExtensions</key><array><string>md</string><string>markdown</string><string>mdown</string></array>
  </dict></array>
</dict></plist>
PLIST
codesign --force --sign - "$app" >/dev/null 2>&1 || true
(GOREECLOUD_RTE_HOME="$GOREECLOUD_RTE_HOME" nohup "$bin" >/tmp/goreecloud-rich-text-editor-preview.log 2>&1 &)
sleep 2; pgrep -fl "^$bin"
