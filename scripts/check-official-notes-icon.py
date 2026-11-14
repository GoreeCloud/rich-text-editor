#!/usr/bin/env python3
"""Offline source-pinned official GoreeCloud Notes icon verification.

Protect native branding and package compatibility with no network or access
to user documents. Source is GoreeCloud/brand-assets commit 14fa8e5ac4fd.
"""
import hashlib
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = {
    "assets/branding/app-icon.png": (
        "a7d94be348d09cf1e78896cbe11f98ee4234a106fa268a6ea4b1b47d7762e60e", 43097),
    "assets/branding/app-icon.ico": (
        "9c6ec314131ac42163c7edfbcae6a7ecd15a277f44badb79a95aa1747fc4cca1", 25311),
}
for name, (sha, length) in ASSETS.items():
    data = (ROOT / name).read_bytes()
    assert len(data) == length, "Wrong official icon size: " + name
    assert hashlib.sha256(data).hexdigest() == sha, "Invalid official Notes icon SHA-256: " + name
    if name.endswith(".png"):
        assert data[:8] == bytes.fromhex("89504e470d0a1a0a")
        assert struct.unpack(">II", data[16:24]) == (512, 512)
    else:
        assert data[:6] == bytes.fromhex("000001000400")
        sizes = tuple((data[6 + i * 16] or 256, data[7 + i * 16] or 256) for i in range(4))
        assert sizes == ((16, 16), (32, 32), (48, 48), (256, 256))
build = (ROOT / "build.rs").read_text()
assert 'VALUE "ProductName", "GoreeCloud Notes\\0"' in build
assert 'VALUE "FileDescription", "GoreeCloud Notes\\0"' in build
assert 'VALUE "OriginalFilename", "goreecloud_rich_text_editor.exe\\0"' in build
linux = (ROOT / "scripts/package-linux.sh").read_text()
appimage = (ROOT / "scripts/package-appimage.sh").read_text()
assert 'install -m644 assets/branding/app-icon.png' in linux
assert 'install -m644 assets/branding/app-icon.png' in appimage
assert "-resize 512x512" not in linux
assert "-resize 512x512" not in appimage
desktop = (ROOT / "packaging/linux/com.goreecloud.richtexteditor.desktop").read_text()
assert "Name=GoreeCloud Notes" in desktop
assert "Icon=com.goreecloud.richtexteditor" in desktop
print("OFFICIAL_NOTES_ICON_PROVENANCE_PASS brand-assets@14fa8e5: PNG 512px and Windows ICO")
