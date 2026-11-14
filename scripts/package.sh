#!/bin/zsh
# Build, sign, notarize and package GoreeCloud Rich Text Editor as a .dmg for distribution.
#
#   scripts/package.sh [version]
#
# Needs a "Developer ID Application" certificate in the keychain and a
# notarytool keychain profile. Create the profile once:
#
#   xcrun notarytool store-credentials goreecloud-rich-text-editor \
#     --apple-id <你的 Apple ID> --team-id <Team ID> --password <App 专用密码>
#
# Environment:
#   CODESIGN_ID          Explicit Developer ID Application identity (required)
#   NOTARY_PROFILE       Existing notarytool keychain profile (required)
#   GOREECLOUD_APPLE_TEAM_ID  Expected 10-character Apple Developer team ID
#   GOREECLOUD_RELEASE_ENABLED=yes  Explicit production release gate
# App bundle identifier is fixed: com.goreecloud.richtexteditor
set -e
cd "$(dirname "$0")/.."
version=${1:-$(sed -n 's/^version = "\(.*\)"/\1/p' Cargo.toml | head -1)}
# This alternate DMG flow is production-only and must never auto-select
# a different team's signing certificate from the keychain.
[ "${GOREECLOUD_RELEASE_ENABLED:-}" = yes ] || { echo "Set GOREECLOUD_RELEASE_ENABLED=yes for signed releases" >&2; exit 2; }
: "${CODESIGN_ID:?Set CODESIGN_ID explicitly to your Developer ID signing identity}"
: "${NOTARY_PROFILE:?Set NOTARY_PROFILE to the notarytool keychain profile}"
: "${GOREECLOUD_APPLE_TEAM_ID:?Set GOREECLOUD_APPLE_TEAM_ID to the expected Apple team ID}"
[[ "$GOREECLOUD_APPLE_TEAM_ID" =~ ^[A-Z0-9]{10}$ ]] || { echo "Invalid GOREECLOUD_APPLE_TEAM_ID" >&2; exit 2; }
expected=$(sed -n 's/^version = "\(.*\)"/\1/p' Cargo.toml | head -1)
[ "$version" = "$expected" ] || { echo "Requested version differs from Cargo.toml" >&2; exit 2; }
bundle_id=com.goreecloud.richtexteditor
profile=$NOTARY_PROFILE
sign_id=$CODESIGN_ID

out=$(mktemp -d "$PWD/dist-dmg.XXXXXX")
app="$out/GoreeCloud Rich Text Editor.app"
dmg="$out/goreecloud-rich-text-editor-$version.dmg"

echo "== 编译 $version"
cargo build --release --locked

echo "== 组装 $app"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
cp LICENSE THIRD_PARTY.md "$app/Contents/Resources/"
cp target/release/goreecloud_rich_text_editor "$app/Contents/MacOS/goreecloud_rich_text_editor"
# .icns：Finder 和 Dock 用图标文件，不是裸 PNG。
iconset=$(mktemp -d)/icon.iconset
mkdir -p "$iconset"
for s in 16 32 128 256 512; do
  sips -z $s $s assets/branding/app-icon.png --out "$iconset/icon_${s}x${s}.png" >/dev/null
  sips -z $((s * 2)) $((s * 2)) assets/branding/app-icon.png --out "$iconset/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$iconset" -o "$app/Contents/Resources/app-icon.icns"
cat > "$app/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>GoreeCloud Rich Text Editor</string>
  <key>CFBundleDisplayName</key><string>GoreeCloud Rich Text Editor</string>
  <key>CFBundleIdentifier</key><string>$bundle_id</string>
  <key>CFBundleExecutable</key><string>goreecloud_rich_text_editor</string>
  <key>CFBundleIconFile</key><string>app-icon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>$version</string>
  <key>CFBundleVersion</key><string>$version</string>
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

echo "== 签名（hardened runtime + 时间戳）"
codesign --force --options runtime --timestamp --sign "$sign_id" "$app"
codesign --verify --deep --strict --verbose=2 "$app"
codesign -dv --verbose=4 "$app" 2>&1 | grep -Fx "TeamIdentifier=$GOREECLOUD_APPLE_TEAM_ID" >/dev/null || {
  echo "Wrong Apple Developer ID team for this signed application" >&2
  exit 1
}

echo "== 打包 $dmg"
rm -rf "$out/dmg-root"
mkdir -p "$out/dmg-root"
cp -R "$app" "$out/dmg-root/"
ln -s /Applications "$out/dmg-root/Applications"
hdiutil create -quiet -volname "GoreeCloud Rich Text Editor" -srcfolder "$out/dmg-root" -ov -format UDZO "$dmg"
rm -rf "$out/dmg-root"
codesign --force --timestamp --sign "$sign_id" "$dmg"

echo "== 公证（需要网络，通常几分钟）"
xcrun notarytool submit "$dmg" --keychain-profile "$profile" --wait --output-format json > "$out/notarization.json"
python3 - "$out/notarization.json" <<'PYTHON'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    result = json.load(f)
if result.get("status") != "Accepted":
    raise SystemExit("DMG notarization was not accepted; see " + sys.argv[1])
print("DMG notarized:", result.get("id", "(submission ID not returned)"))
PYTHON
xcrun stapler staple "$dmg"
xcrun stapler validate "$dmg"

echo "== 验收"
spctl -a -vvv -t install "$dmg"
codesign -dv --verbose=4 "$app" 2>&1 | grep -E "Identifier|Authority|TeamIdentifier|flags"
echo
echo "好了：$dmg（$(du -h "$dmg" | cut -f1)）"
