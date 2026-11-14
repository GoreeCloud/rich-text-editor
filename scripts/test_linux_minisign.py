#!/usr/bin/env python3
"""Test real Linux minisign verification using disposable, non-production keys.

No network calls, release-host credentials, persistent secrets, or production
signing-key changes. The temporary test-only secret key is deleted by teardown.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

import test_release_audit as fixtures

audit = fixtures.audit


class LinuxSignatureRehearsalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("minisign") is None:
            raise RuntimeError("Linux release signing tests require minisign")

    def setUp(self):
        self.fixture = fixtures.ReleaseAuditTests("test_candidate_checks_cover_all_platforms")
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.root = self.fixture.root
        (self.root / "Cargo.toml").write_text(f'[package]\nversion = "{fixtures.V}"\n')
        (self.root / "packaging").mkdir(exist_ok=True)
        self.pub = self.root / "packaging" / "update-key.pub"
        self.priv = self.root / "test-only-ephemeral-minisign.key"
        subprocess.run(["minisign", "-G", "-W", "-p", str(self.pub), "-s", str(self.priv)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    def sign(self, path: Path) -> Path:
        signature = self.root / (path.name + ".minisig")
        subprocess.run(["minisign", "-S", "-q", "-s", str(self.priv), "-m", str(path),
                        "-x", str(signature), "-t", path.name],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return signature

    def audit_signed(self, path: Path, signature: Path):
        with patch.object(audit, "ROOT", self.root), patch.dict(os.environ, {
            "GOREECLOUD_RELEASE_ENABLED": "yes",
            "GOREECLOUD_DOWNLOAD_HOST": "https://releases.example.com",
            "GOREECLOUD_DOWNLOAD_BUCKET": "goreecloud-rehearsal-test",
        }):
            return audit.audit(path, distribution=True, signature_file=signature)

    def test_signed_linux_appimage_passes_actual_minisign(self):
        app = self.fixture.appimage()
        result = self.audit_signed(app, self.sign(app))
        self.assertIn("platform signature", result["verified"])
        self.assertEqual(result["platform"], "linux-x86_64-appimage")

    def test_signed_linux_tarball_passes_actual_minisign(self):
        tar = self.fixture.linux_tar()
        result = self.audit_signed(tar, self.sign(tar))
        self.assertIn("platform signature", result["verified"])
        self.assertEqual(result["platform"], "linux-x86_64-tar")

    def test_appimage_signature_cannot_be_replayed_for_tarball(self):
        app = self.fixture.appimage()
        tar = self.fixture.linux_tar()
        app_sig = self.sign(app)
        with self.assertRaises(subprocess.CalledProcessError):
            self.audit_signed(tar, app_sig)

    def test_checksum_replaced_on_tampered_payload_still_fails_signature(self):
        tar = self.fixture.linux_tar()
        signed = self.sign(tar)
        tampered = tar.read_bytes() + b"unauthorized edit"
        tar.write_bytes(tampered)
        # An attacker could replace a SHA-256 text sidecar too. Minisign
        # must remain an independent provenance check on the changed bytes.
        tar.with_name(tar.name + ".sha256").write_text(
            hashlib.sha256(tampered).hexdigest() + "  " + tar.name + "\n")
        with self.assertRaises(subprocess.CalledProcessError):
            self.audit_signed(tar, signed)

    def test_unconfigured_signature_does_not_verify(self):
        app = self.fixture.appimage()
        missing = self.root / "missing.minisig"
        with self.assertRaisesRegex(ValueError, "no detached minisign signature"):
            self.audit_signed(app, missing)


if __name__ == "__main__":
    unittest.main()
