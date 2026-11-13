#!/usr/bin/env python3
"""Hermetic regression tests for release-package audit and safe defaults."""
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import plistlib
import struct
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("release_audit", HERE / "audit-release-artifacts.py")
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)
V = audit.version()

class ReleaseAuditTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="goreecloud-release-audit-tests-")
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def sign_checksum(self, name, payload):
        path = self.root / name
        path.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        path.with_name(name + ".sha256").write_text(f"{digest}  {name}\n", encoding="ascii")
        return path

    def macos(self, target):
        name = f"goreecloud-rich-text-editor-{V}-macos-{target}-unsigned.zip"
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as z:
            base = "GoreeCloud Rich Text Editor.app/"
            z.writestr(base + "Contents/Info.plist", plistlib.dumps({
                "CFBundleIdentifier": "com.goreecloud.richtexteditor",
                "CFBundleDisplayName": "GoreeCloud Rich Text Editor",
                "CFBundleExecutable": "goreecloud_rich_text_editor",
            }))
            z.writestr(base + "Contents/MacOS/goreecloud_rich_text_editor", b"MACHO MOCK")
            z.writestr(base + "Contents/Resources/LICENSE", b"MIT")
            z.writestr(base + "Contents/Resources/THIRD_PARTY.md", b"credits")
        return self.sign_checksum(name, data.getvalue())

    def linux_tar(self):
        name = f"goreecloud-rich-text-editor-{V}-linux-x86_64.tar.gz"
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode="w:gz") as tf:
            for rel in ["bin/goreecloud_rich_text_editor", "LICENSE", "THIRD_PARTY.md",
                        "share/applications/com.goreecloud.richtexteditor.desktop",
                        "runtime-libraries.txt"]:
                content=b"content"
                item=tarfile.TarInfo(name.removesuffix(".tar.gz") + "/" + rel)
                item.size=len(content)
                tf.addfile(item,io.BytesIO(content))
        return self.sign_checksum(name, data.getvalue())

    def windows(self):
        name = f"goreecloud-rich-text-editor-{V}-windows-x64-setup.exe"
        data = bytearray(140)
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 0x3c, 128)
        data[128:132] = b"PE\0\0"
        return self.sign_checksum(name, data)

    def appimage(self):
        return self.sign_checksum(f"goreecloud-rich-text-editor-{V}-x86_64.AppImage", b"\x7fELF"+"-mock".encode())

    def test_candidate_checks_cover_all_platforms(self):
        for path in [self.macos("arm64"), self.macos("x86_64"), self.windows(), self.linux_tar(), self.appimage()]:
            with self.subTest(path=path.name):
                report = audit.audit(path, distribution=False)
                self.assertIn("NOT a distribution signature", report["verified"])
                self.assertEqual(report["version"], V)

    def test_checksum_tampering_is_rejected(self):
        path=self.linux_tar()
        path.write_bytes(path.read_bytes()+b"changed")
        with self.assertRaisesRegex(ValueError, "SHA-256"): audit.audit(path, False)

    def test_wrong_name_and_missing_sidecar_are_rejected(self):
        path=self.macos("arm64")
        path.with_name(path.name+".sha256").unlink()
        with self.assertRaisesRegex(ValueError, "missing checksum"): audit.audit(path, False)
        with self.assertRaisesRegex(ValueError, "unrecognized"): audit.classify("quiet-md-0.1.0-macos-arm64.zip")

    def test_wrong_bundle_identity_is_rejected(self):
        path=self.macos("arm64")
        with zipfile.ZipFile(path) as source:
            members = {name: source.read(name) for name in source.namelist()}
        members["GoreeCloud Rich Text Editor.app/Contents/Info.plist"] = plistlib.dumps({
            "CFBundleIdentifier": "com.example.bad",
        })
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as target:
            for name, content in members.items(): target.writestr(name, content)
        self.sign_checksum(path.name, data.getvalue())
        with self.assertRaisesRegex(ValueError, "identifier"): audit.audit(path, False)

    def test_unsigned_packages_cannot_pass_distribution_without_configuration(self):
        with patch.dict(os.environ, {"GOREECLOUD_RELEASE_ENABLED":""}, clear=True):
            for path in [self.windows(), self.macos("arm64"), self.appimage()]:
                with self.subTest(path=path.name):
                    with self.assertRaisesRegex(ValueError, "distribution disabled"): audit.audit(path, True)

    def test_distribution_rejects_placeholder_hosts(self):
        path=self.appimage()
        with patch.dict(os.environ,{"GOREECLOUD_RELEASE_ENABLED":"yes",
                                  "GOREECLOUD_DOWNLOAD_HOST":"https://updates.invalid",
                                  "GOREECLOUD_DOWNLOAD_BUCKET":"goreecloud-releases"}):
            with self.assertRaisesRegex(ValueError, "HTTPS origin"): audit.audit(path, True)

if __name__ == "__main__":
    unittest.main()
