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
                item.mode=0o755 if rel.startswith("bin/") else 0o644
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

    def append_linux_member(self, name, kind="file"):
        archive = self.linux_tar()
        with tarfile.open(archive, "r:gz") as source:
            items = [(entry.name, entry.mode, source.extractfile(entry).read()) for entry in source.getmembers()]
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as rebuilt:
            for entry_name, mode, blob in items:
                item = tarfile.TarInfo(entry_name)
                item.size = len(blob)
                item.mode = mode
                rebuilt.addfile(item, io.BytesIO(blob))
            item = tarfile.TarInfo(name)
            if kind == "symlink":
                item.type = tarfile.SYMTYPE
                item.linkname = "../../outside-library"
                rebuilt.addfile(item)
            else:
                blob = b"untrusted extra payload"
                item.size = len(blob)
                rebuilt.addfile(item, io.BytesIO(blob))
        return self.sign_checksum(archive.name, buf.getvalue())

    def test_linux_tarball_path_escape_is_rejected_even_with_fresh_checksum(self):
        path = self.append_linux_member("../../outside-library")
        with self.assertRaisesRegex(ValueError, "unsafe or unrelated Linux archive path"):
            audit.audit(path, False)

    def test_linux_tarball_link_member_is_rejected(self):
        name = f"goreecloud-rich-text-editor-{V}-linux-x86_64/share/applications/link"
        path = self.append_linux_member(name, kind="symlink")
        with self.assertRaisesRegex(ValueError, "links or special members"):
            audit.audit(path, False)

    def test_linux_tarball_duplicate_member_is_rejected(self):
        name = f"goreecloud-rich-text-editor-{V}-linux-x86_64/LICENSE"
        path = self.append_linux_member(name)
        with self.assertRaisesRegex(ValueError, "duplicate Linux archive member"):
            audit.audit(path, False)

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

    def test_distribution_rejects_unsigned_mac_even_with_release_gate(self):
        path = self.macos("arm64")
        with patch.dict(os.environ, {
            "GOREECLOUD_RELEASE_ENABLED": "yes",
            "GOREECLOUD_DOWNLOAD_HOST": "https://releases.example.com",
            "GOREECLOUD_DOWNLOAD_BUCKET": "test-candidate-bucket",
        }):
            with self.assertRaisesRegex(ValueError, "ad-hoc macOS CI package"):
                audit.audit(path, True)

    def test_distribution_rejects_invalid_https_host_shapes(self):
        path = self.appimage()
        for host in ["http://releases.example.com", "https://updates.invalid",
                     "https://download.quiet.md", "https://alice:secret@releases.example.com",
                     "https://releases.example.com/unexpected/path"]:
            with self.subTest(host=host), patch.dict(os.environ, {
                "GOREECLOUD_RELEASE_ENABLED": "yes",
                "GOREECLOUD_DOWNLOAD_HOST": host,
                "GOREECLOUD_DOWNLOAD_BUCKET": "test-candidate-bucket",
            }):
                with self.assertRaisesRegex(ValueError, "HTTPS origin"):
                    audit.audit(path, True)

    def test_linux_distribution_uses_the_staged_signature(self):
        # A mocked invocation verifies *which* verifier and key are called;
        # real cryptographic signing is gated on the owner's private key.
        path = self.appimage()
        pub = self.root / "packaging/update-key.pub"
        pub.parent.mkdir(parents=True)
        pub.write_text("untrusted comment: synthetic fixture only\n")
        staged = self.root / "signed-in-private-staging.minisig"
        staged.write_text("synthetic test signature")
        with patch.object(audit, "ROOT", self.root), patch.dict(os.environ, {
            "GOREECLOUD_RELEASE_ENABLED": "yes",
            "GOREECLOUD_DOWNLOAD_HOST": "https://release.example.com",
            "GOREECLOUD_DOWNLOAD_BUCKET": "test-release-bucket",
        }), patch.object(audit.subprocess, "run") as call:
            audit.verify_distribution(path, "linux-x86_64", staged)
            call.assert_called_once_with(
                ["minisign", "-Vm", str(path), "-x", str(staged), "-p", str(pub)], check=True)
            with self.assertRaisesRegex(ValueError, "no detached minisign signature"):
                audit.verify_distribution(path, "linux-x86_64")
        print("Staged Linux signature verifier checked; actual cryptographic signing requires owner key.")

    def test_distribution_rejects_placeholder_hosts(self):
        path=self.appimage()
        with patch.dict(os.environ,{"GOREECLOUD_RELEASE_ENABLED":"yes",
                                  "GOREECLOUD_DOWNLOAD_HOST":"https://updates.invalid",
                                  "GOREECLOUD_DOWNLOAD_BUCKET":"goreecloud-releases"}):
            with self.assertRaisesRegex(ValueError, "HTTPS origin"): audit.audit(path, True)

if __name__ == "__main__":
    unittest.main()
