#!/usr/bin/env python3
"""Hermetic positive and adversarial Linux candidate gate tests."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("linux_candidate_gate", HERE / "check-linux-release.py")
gate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gate
spec.loader.exec_module(gate)
import test_release_audit as release_fixtures


class LinuxCandidateTests(unittest.TestCase):
    def setUp(self):
        self.fixture = release_fixtures.ReleaseAuditTests("test_candidate_checks_cover_all_platforms")
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.tar = self.fixture.linux_tar()
        self.app = self.fixture.appimage()
        self.glibc = self.app.with_name(self.app.name + ".glibc.txt")
        self.libs = self.app.with_name(self.app.name + ".libraries.txt")
        self.glibc.write_text("2.2.5\n2.35\n", encoding="utf-8")
        self.libs.write_text("linux-vdso.so.1\nlibc.so.6 => /lib/libc.so.6\n", encoding="utf-8")

    def test_pair_passes_without_claiming_signatures(self):
        report = gate.validate(self.fixture.root)
        self.assertEqual(report["glibc_max"], "2.35")
        self.assertEqual(len(report["artifacts"]), 2)
        result = subprocess.run([sys.executable, "-B", str(HERE / "check-linux-release.py"),
                                 str(self.fixture.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("NOT verified", result.stdout)

    def test_appimage_missing_fails(self):
        self.app.unlink()
        with self.assertRaisesRegex(ValueError, "Expected exactly two"):
            gate.validate(self.fixture.root)

    def test_missing_tarball_fails(self):
        self.tar.unlink()
        with self.assertRaisesRegex(ValueError, "Expected exactly two"):
            gate.validate(self.fixture.root)

    def test_stale_duplicate_release_artifact_fails(self):
        (self.fixture.root / "goreecloud-rich-text-editor-0.0.0-x86_64.AppImage").write_bytes(b"ELF")
        with self.assertRaisesRegex(ValueError, "Expected exactly two"):
            gate.validate(self.fixture.root)

    def test_tampered_checksum_fails(self):
        self.app.write_bytes(self.app.read_bytes() + b"tampered")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            gate.validate(self.fixture.root)

    def test_missing_or_empty_compatibility_report_fails(self):
        for path in (self.glibc, self.libs):
            original = path.read_bytes()
            path.unlink()
            with self.subTest(path=path.name), self.assertRaisesRegex(ValueError, "diagnostic"):
                gate.validate(self.fixture.root)
            path.write_bytes(b"")
            with self.assertRaisesRegex(ValueError, "diagnostic"):
                gate.validate(self.fixture.root)
            path.write_bytes(original)

    def test_newer_than_ubuntu_2204_glibc_fails(self):
        self.glibc.write_text("2.35\n2.38\n")
        with self.assertRaisesRegex(ValueError, "exceeds.*GLIBC"):
            gate.validate(self.fixture.root)

    def test_invalid_glibc_report_fails(self):
        self.glibc.write_text("2.35\n2.evil\n")
        with self.assertRaisesRegex(ValueError, "Invalid GLIBC"):
            gate.validate(self.fixture.root)

    def test_missing_runtime_lib_fails(self):
        self.libs.write_text("libmissing.so.1 => not found\n")
        with self.assertRaisesRegex(ValueError, "unresolved libraries"):
            gate.validate(self.fixture.root)


if __name__ == "__main__":
    unittest.main()
