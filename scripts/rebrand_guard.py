#!/usr/bin/env python3
"""Protect the identity, attribution, and safety of the GoreeCloud rebranded import.

Run with: python3 scripts/rebrand_guard.py
This is a lightweight check: it never opens user libraries or contacts a server.
"""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

GUIDE = "goreecloud-rich-text-editor-cheatsheet.pdf"
GUIDE_SOURCE = ROOT / "shared-mock/guides/assets" / GUIDE
GUIDE_BUNDLED = ROOT / "shared-mock/library/assets/guides" / GUIDE

checks = {
    "application identifier": 'com.goreecloud.richtexteditor' in read("src/main.rs"),
    "binary name": 'name = "goreecloud_rich_text_editor"' in read("Cargo.toml"),
    "independent notes directory": '.join("GoreeCloud Rich Text Editor")' in read("crates/core/src/store.rs"),
    "upstream auto-updates disabled": 'const UPDATES_CONFIGURED: bool = false;' in read("src/update.rs"),
    "no upstream update endpoints": "download.quiet.md" not in read("src/update.rs").split("#[cfg(test)]")[0],
    "safe update placeholder": 'const BASE: &str = "https://updates.invalid/latest";' in read("src/update.rs"),
    "GoreeCloud package naming": 'goreecloud-rich-text-editor-{version}' in read("src/update.rs"),
    "release key remains unconfigured": "public key not configured" in read("packaging/update-key.pub"),
    "upstream copyright preserved": "Copyright (c) 2026 s1dashu" in read("LICENSE"),
    "upstream attribution": "s1dashu/quiet-md" in read("UPSTREAM.md"),
    "third-party notices": "assets/icons/LICENSE-lucide" in read("THIRD_PARTY.md"),
    "Nucleo assets not bundled": not (ROOT / "assets/icons/LICENSE-nucleo").exists(),
    "original mascot not bundled": not (ROOT / "assets/branding/hamster-source.png").exists(),
    "old monogram not bundled": not (ROOT / "assets/branding/quiet-q").exists(),
    "Windows app identity": "AppName=GoreeCloud Rich Text Editor" in read("packaging/windows/goreecloud-rich-text-editor.iss"),
    "Windows signing tool matches installer": "SignTool=goreecloudrte" in read("packaging/windows/goreecloud-rich-text-editor.iss") and "/Sgoreecloudrte=" in read("scripts/package-windows.ps1"),
    "Linux app identity": "Name=GoreeCloud Rich Text Editor" in read("packaging/linux/com.goreecloud.richtexteditor.desktop"),
    "AppImage launcher calls renamed binary": 'exec "$appdir/usr/bin/goreecloud_rich_text_editor" "$@"' in read("packaging/linux/AppRun"),
    "AppImage launcher is smoke-tested": "AppImage launcher smoke test passed" in read("scripts/package-appimage.sh"),
    "release publishing gated": "GOREECLOUD_RELEASE_ENABLED" in read("scripts/publish-downloads.sh"),
    "analytics deployment neutralized": not (ROOT / "services/stats/wrangler.jsonc").exists(),
    "macOS preview app identifier": "com.goreecloud.richtexteditor.preview" in read("scripts/preview.sh"),
    "static site identifies beta source import": "GoreeCloud Rich Text Editor" in read("site/public/index.html") and "download.quiet.md" not in read("site/public/index.html"),
    "GoreeCloud guide PDF bundled": GUIDE_SOURCE.is_file() and GUIDE_BUNDLED.is_file() and GUIDE_SOURCE.read_bytes() == GUIDE_BUNDLED.read_bytes(),
    "first-launch guide links GoreeCloud PDF": all(GUIDE in read(path) and "quiet-md-cheatsheet.pdf" not in read(path) for path in ["shared-mock/guides/src/06-media.xml", "shared-mock/library/docs/0c7532c1-edcc-534d-8efe-7bf6da8718ba.xml"]),
    "macOS CI package patterns": "dist-release.*/goreecloud-rich-text-editor-" in read(".github/workflows/ci.yml"),
    "Windows CI package patterns": "dist/windows/unsigned/goreecloud-rich-text-editor-" in read(".github/workflows/ci.yml"),
}

icons = sorted((ROOT / "assets/icons").glob("*.svg"))
for icon in icons:
    try:
        if "Nucleo" in icon.read_text(encoding="utf-8"):
            checks["Nucleo icon removed: " + icon.name] = False
        ET.parse(icon)
    except (ET.ParseError, UnicodeError) as exc:
        print(f"Invalid app icon {icon.name}: {exc}", file=sys.stderr)
        checks["SVG icon: " + icon.name] = False

failed = [name for name, ok in checks.items() if not ok]
if failed:
    for name in failed:
        print(f"FAIL: {name}", file=sys.stderr)
    raise SystemExit(1)

print(f"Rebrand guard passed ({len(checks)} identity, license and release checks; {len(icons)} XML icons).")
