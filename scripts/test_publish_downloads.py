#!/usr/bin/env python3
"""Offline release-publisher regression suite; no real keys or network calls."""
from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import plistlib
import re
import struct
import subprocess
import tarfile
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parent.parent
VERSION = re.search(r'^version\s*=\s*"(\d+\.\d+\.\d+)"',
                    (ROOT / "Cargo.toml").read_text(), re.M).group(1)


class PublishSafetyTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix="goreecloud-publish-qa-")
        self.dir = Path(self.work.name)
        self.env = {**os.environ,
                    "GOREECLOUD_RELEASE_ENABLED": "yes",
                    "GOREECLOUD_DOWNLOAD_BUCKET": "goreecloud-test-bucket",
                    "GOREECLOUD_DOWNLOAD_HOST": "https://release.example.com/",
                    "DRY_RUN": "1"}

    def tearDown(self):
        self.work.cleanup()

    def package(self, kind: str, destination: Path | None = None) -> Path:
        d = destination or self.dir
        d.mkdir(parents=True, exist_ok=True)
        if kind == "linux":
            name = f"goreecloud-rich-text-editor-{VERSION}-x86_64.AppImage"
            blob = b"\x7fELF" + b"offline test appimage fixture"
        elif kind == "linux_tar":
            name = f"goreecloud-rich-text-editor-{VERSION}-linux-x86_64.tar.gz"
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
                base = name.removesuffix(".tar.gz")
                for rel in ["bin/goreecloud_rich_text_editor", "LICENSE", "THIRD_PARTY.md",
                            "share/applications/com.goreecloud.richtexteditor.desktop",
                            "runtime-libraries.txt"]:
                    data = b"libc.so.6 => /lib/libc.so.6" if rel == "runtime-libraries.txt" else b"fixture"
                    item = tarfile.TarInfo(base + "/" + rel)
                    item.size = len(data)
                    item.mode = 0o755 if rel.startswith("bin/") else 0o644
                    archive.addfile(item, io.BytesIO(data))
            blob = buffer.getvalue()
        elif kind == "windows":
            name = f"goreecloud-rich-text-editor-{VERSION}-windows-x64-setup.exe"
            data = bytearray(140)
            data[:2] = b"MZ"
            struct.pack_into("<I", data, 0x3c, 128)
            data[128:132] = b"PE\0\0"
            blob = bytes(data)
        elif kind in ("mac", "mac_intel"):
            architecture = "x86_64" if kind == "mac_intel" else "arm64"
            name = f"goreecloud-rich-text-editor-{VERSION}-macos-{architecture}.zip"
            file = io.BytesIO()
            prefix = "GoreeCloud Rich Text Editor.app/"
            with zipfile.ZipFile(file, "w") as z:
                z.writestr(prefix+"Contents/Info.plist", plistlib.dumps({
                    "CFBundleIdentifier": "com.goreecloud.richtexteditor",
                    "CFBundleDisplayName": "GoreeCloud Rich Text Editor",
                    "CFBundleExecutable": "goreecloud_rich_text_editor",
                }))
                for leaf in ["Contents/MacOS/goreecloud_rich_text_editor",
                             "Contents/Resources/LICENSE", "Contents/Resources/THIRD_PARTY.md"]:
                    z.writestr(prefix + leaf, b"fixture only")
            blob = file.getvalue()
        else:
            raise AssertionError(kind)
        output = d / name
        output.write_bytes(blob)
        output.with_name(name+".sha256").write_text(
            f"{hashlib.sha256(blob).hexdigest()}  {name}\n", encoding="ascii")
        return output

    def execute(self, *paths: Path, env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", "scripts/publish-downloads.sh", *map(str, paths)],
                              cwd=ROOT, env=env or self.env, capture_output=True,
                              text=True, timeout=12)

    def test_dry_run_stages_all_packages_before_announcing_any_version(self):
        mac, intel = self.package("mac"), self.package("mac_intel")
        result = self.execute(mac, intel)
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = [line for line in result.stdout.splitlines()
                    if " r2 object put " in line]
        self.assertEqual(len(commands), 10, commands)
        self.assertTrue(all("latest/update-" not in line for line in commands[:-2]), commands)
        self.assertTrue(all("latest/update-" in line for line in commands[-2:]), commands)
        self.assertIn("v"+VERSION+"/goreecloud-rich-text-editor-", result.stdout)
        # Endpoints are normalized without a double slash after the domain.
        self.assertNotIn("example.com//v"+VERSION, result.stdout)
        self.assertNotIn("example.com//latest", result.stdout)

    def test_signed_linux_pair_has_only_one_appimage_update_feed(self):
        app = self.package("linux")
        tar = self.package("linux_tar")
        for order in [(app, tar), (tar, app)]:
            with self.subTest(order=[p.name for p in order]):
                result = self.execute(*order)
                self.assertEqual(result.returncode, 0, result.stderr)
                puts = [line for line in result.stdout.splitlines() if " r2 object put " in line]
                # Each Linux file has versioned package, checksum, minisig and latest
                # link, but ONLY the AppImage should announce an update feed.
                self.assertEqual(len(puts), 9, puts)
                self.assertTrue(all("latest/update-" not in line for line in puts[:-1]), puts)
                self.assertIn("latest/update-linux-x86_64.json", puts[-1])
                self.assertNotIn("update-linux-x86_64-tar.json", result.stdout)
                self.assertEqual(sum("latest/goreecloud-rich-text-editor-linux-x86_64.tar.gz" in x for x in puts), 1)
                self.assertEqual(sum("latest/goreecloud-rich-text-editor-x86_64.AppImage" in x for x in puts), 1)
                self.assertEqual(sum(".minisig" in x for x in puts), 2)

    def test_linux_tarball_alone_is_manual_only(self):
        tar = self.package("linux_tar")
        result = self.execute(tar)
        self.assertEqual(result.returncode, 0, result.stderr)
        puts = [line for line in result.stdout.splitlines() if " r2 object put " in line]
        self.assertEqual(len(puts), 4, puts)
        self.assertNotIn("latest/update-", result.stdout)
        self.assertIn("manual Linux tarball", result.stdout)
        self.assertIn("signing required outside DRY_RUN", result.stdout)
        self.assertIn("application/gzip", result.stdout)

    def test_corrupt_second_linux_tarball_blocks_all_uploads(self):
        app, tar = self.package("linux"), self.package("linux_tar")
        tar.write_bytes(tar.read_bytes() + b"tampered")
        result = self.execute(app, tar)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SHA-256", result.stderr)
        self.assertNotIn(" r2 object put ", result.stdout)

    def test_duplicate_linux_tarball_is_rejected(self):
        first = self.package("linux_tar", self.dir/"one")
        second = self.package("linux_tar", self.dir/"two")
        result = self.execute(first, second)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate platform", result.stderr)
        self.assertNotIn(" r2 object put ", result.stdout)

    def test_second_corrupt_artifact_blocks_all_uploads(self):
        first, second = self.package("mac"), self.package("mac_intel")
        second.write_bytes(second.read_bytes()+b"tampered")
        result = self.execute(first, second)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SHA-256", result.stderr)
        self.assertNotIn(" r2 object put ", result.stdout)

    def test_mixed_native_signing_families_fail_before_upload(self):
        mac, linux = self.package("mac"), self.package("linux")
        result = self.execute(mac, linux)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Mixed native signing platforms", result.stderr)
        self.assertNotIn(" r2 object put ", result.stdout)

    def test_windows_release_requires_signed_directory_even_in_dry_run(self):
        unsigned = self.package("windows")
        rejected = self.execute(unsigned)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("signed/ directory", rejected.stderr)
        signed = self.package("windows", self.dir / "signed")
        accepted = self.execute(signed)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        commands = [v for v in accepted.stdout.splitlines() if " r2 object put " in v]
        self.assertEqual(len(commands), 5, commands)
        self.assertIn("latest/update-windows-x64.json", commands[-1])

    def test_duplicated_platform_preflight_blocks_all_uploads(self):
        first = self.package("linux", self.dir/"first")
        duplicate = self.package("linux", self.dir/"second")
        result = self.execute(first, duplicate)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate platform", result.stderr)
        self.assertNotIn(" r2 object put ", result.stdout)

    def test_disabled_release_and_bad_https_host_block_before_upload(self):
        package = self.package("linux")
        for key, value, wanted in [
            ("GOREECLOUD_RELEASE_ENABLED", "", "publishing disabled"),
            ("GOREECLOUD_DOWNLOAD_HOST", "http://release.example.com", "HTTPS origin"),
            ("GOREECLOUD_DOWNLOAD_HOST", "https://download.quiet.md", "HTTPS origin"),
            ("GOREECLOUD_DOWNLOAD_BUCKET", "bad bucket with spaces", "bucket"),
        ]:
            env = {**self.env, key: value}
            with self.subTest(key=key, value=value):
                result = self.execute(package, env=env)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn(wanted.lower(), result.stderr.lower())
                self.assertNotIn(" r2 object put ", result.stdout)

    def test_unsigned_windows_and_macos_are_never_published_in_production(self):
        # Distribution mode verifies native signatures; the test runner has
        # neither a signing key nor a real release domain.
        for kind in ["windows", "mac"]:
            path = self.package(kind)
            result = subprocess.run(
                ["python3", "-B", "scripts/audit-release-artifacts.py", "--distribution", str(path)],
                cwd=ROOT, env={**self.env, "DRY_RUN": ""}, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("verified: platform signature", result.stdout)
            # Platform-native rejection may happen at team-ID/subject gating
            # or later at actual signature verification. Both fail closed.
            self.assertIn("FAIL:", result.stderr)


if __name__ == "__main__":
    unittest.main()
