#!/usr/bin/env python3
"""Offline checks for GoreeCloud desktop packages; no uploads or signing.

A validation report checks checksums and contents, NOT signatures. Use
--distribution to fail closed unless the platform's real signing, notarization
and (where applicable) minisign verification all succeed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import struct
import subprocess
import sys
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
PREFIX = "goreecloud-rich-text-editor-"
CASES = [
    ("macos-arm64", re.compile(r"^goreecloud-rich-text-editor-(\d+\.\d+\.\d+)-macos-arm64(-unsigned)?\.zip$")),
    ("macos-x86_64", re.compile(r"^goreecloud-rich-text-editor-(\d+\.\d+\.\d+)-macos-x86_64(-unsigned)?\.zip$")),
    ("windows-x64", re.compile(r"^goreecloud-rich-text-editor-(\d+\.\d+\.\d+)-windows-x64-setup\.exe$")),
    ("linux-x86_64-tar", re.compile(r"^goreecloud-rich-text-editor-(\d+\.\d+\.\d+)-linux-x86_64\.tar\.gz$")),
    ("linux-x86_64-appimage", re.compile(r"^goreecloud-rich-text-editor-(\d+\.\d+\.\d+)-x86_64\.AppImage$")),
]

def fail(message: str) -> None:
    raise ValueError(message)

def version() -> str:
    source = (ROOT / "Cargo.toml").read_text()
    match = re.search(r'^version\s*=\s*"(\d+\.\d+\.\d+)"', source, re.M)
    if not match: fail("Cargo.toml version not found")
    return match.group(1)

def classify(name: str) -> tuple[str, str]:
    for platform, pattern in CASES:
        m = pattern.fullmatch(name)
        if m: return platform, m.group(1)
    fail(f"unrecognized GoreeCloud release artifact name: {name}")

def checksum(path: Path) -> str:
    sidecar = path.with_name(path.name + ".sha256")
    if not sidecar.is_file(): fail(f"missing checksum sidecar: {sidecar}")
    raw = sidecar.read_text(encoding="ascii")
    match = re.fullmatch(r"([0-9a-fA-F]{64})  ([^\r\n]+)\n?", raw)
    if not match or match.group(2) != path.name:
        fail(f"invalid checksum sidecar format/filename: {sidecar}")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""): h.update(chunk)
    got = h.hexdigest()
    if got.lower() != match.group(1).lower(): fail(f"SHA-256 checksum mismatch: {path}")
    return got

def macos(path: Path, platform: str) -> None:
    try:
        with zipfile.ZipFile(path) as z:
            members = z.infolist()
            if len(members) > 5000 or sum(item.file_size for item in members) > 1024 * 1024 * 1024:
                fail("macOS package exceeds a safe inspection limit")
            bad = z.testzip()
            if bad: fail(f"corrupt ZIP member: {bad}")
            contents = set(z.namelist())
            apps = [n for n in contents if n.endswith(".app/Contents/Info.plist")]
            if len(apps) != 1: fail("ZIP must contain exactly one macOS Info.plist")
            prefix = apps[0].removesuffix("Contents/Info.plist")
            if not prefix.endswith("GoreeCloud Rich Text Editor.app/"):
                fail("unrecognized app bundle inside ZIP")
            for rel in ["Contents/MacOS/goreecloud_rich_text_editor", "Contents/Resources/LICENSE",
                        "Contents/Resources/THIRD_PARTY.md"]:
                if prefix + rel not in contents: fail(f"missing app resource: {rel}")
            meta = plistlib.loads(z.read(apps[0]))
            if meta.get("CFBundleIdentifier") != "com.goreecloud.richtexteditor" or meta.get("CFBundleExecutable") != "goreecloud_rich_text_editor":
                fail("incorrect app bundle identifier or executable")
            if meta.get("CFBundleDisplayName") != "GoreeCloud Rich Text Editor":
                fail("incorrect macOS display name")
            arch = platform.removeprefix("macos-")
            # Native CPU architecture is verified separately by macOS CI with lipo.
            if arch not in ("arm64", "x86_64"): fail("unsupported macOS target")
    except (zipfile.BadZipFile, plistlib.InvalidFileException) as e:
        fail(f"invalid macOS bundle: {e}")

def linux_tar(path: Path) -> None:
    try:
        with tarfile.open(path, "r:gz") as tf:
            names = set(tf.getnames())
            base = path.name.removesuffix(".tar.gz")
            for rel in ["bin/goreecloud_rich_text_editor", "LICENSE", "THIRD_PARTY.md",
                        "share/applications/com.goreecloud.richtexteditor.desktop",
                        "runtime-libraries.txt"]:
                if base + "/" + rel not in names: fail(f"missing Linux package member: {rel}")
    except tarfile.TarError as e:
        fail(f"invalid Linux archive: {e}")

def executable(path: Path, kind: str) -> None:
    with path.open("rb") as f:
        header = f.read(512)
        if kind == "linux-x86_64-appimage":
            if not header.startswith(b"\x7fELF"): fail("AppImage does not contain an ELF executable")
        elif kind == "windows-x64":
            if not header.startswith(b"MZ"): fail("Windows setup is not an MZ executable")
            if len(header) < 64: fail("truncated Windows setup executable")
            offset = struct.unpack_from("<I", header, 0x3c)[0]
            if offset > 1048576: fail("invalid Windows PE header offset")
            f.seek(offset)
            if f.read(4) != b"PE\0\0": fail("Windows setup is not a PE executable")

def verify_distribution(path: Path, platform: str, signature_file: Path | None = None) -> None:
    if os.environ.get("GOREECLOUD_RELEASE_ENABLED") != "yes":
        fail("distribution disabled; set GOREECLOUD_RELEASE_ENABLED=yes after configuring signing and hosting")
    from urllib.parse import urlsplit
    host = os.environ.get("GOREECLOUD_DOWNLOAD_HOST", "")
    parsed = urlsplit(host)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in ("", "/")
            or parsed.hostname.endswith((".invalid", ".localhost", ".local"))
            or parsed.hostname in ("localhost", "127.0.0.1")
            or "quiet.md" in parsed.hostname):
        fail("GOREECLOUD_DOWNLOAD_HOST must be a GoreeCloud-owned HTTPS origin")
    if not re.fullmatch(r"[A-Za-z0-9._-]{3,128}", os.environ.get("GOREECLOUD_DOWNLOAD_BUCKET", "")):
        fail("GOREECLOUD_DOWNLOAD_BUCKET must identify a configured release bucket")
    if platform.startswith("macos"):
        if path.name.endswith("-unsigned.zip"): fail("ad-hoc macOS CI package cannot be distributed")
        if sys.platform != "darwin": fail("signed macOS bundle must be verified on macOS")
        team = os.environ.get("GOREECLOUD_APPLE_TEAM_ID", "")
        if not re.fullmatch(r"[A-Z0-9]{10}", team): fail("GOREECLOUD_APPLE_TEAM_ID is required")
        with tempfile.TemporaryDirectory(prefix="goreecloud-macos-release-") as d:
            # macOS ditto preserves signing metadata and symlinks that Python's
            # zipfile extraction may alter, which would cause false failures.
            subprocess.run(["ditto", "-x", "-k", str(path), d], check=True)
            apps = list(Path(d).glob("*.app"))
            if len(apps) != 1: fail("unexpected signed app bundle layout")
            app = str(apps[0])
            for cmd in (["codesign", "--verify", "--deep", "--strict", "--verbose=2", app],
                        ["xcrun", "stapler", "validate", app],
                        ["spctl", "--assess", "--type", "execute", "--verbose=2", app]):
                subprocess.run(cmd, check=True)
            result = subprocess.run(["codesign", "-dv", "--verbose=4", app],
                                    capture_output=True, text=True, check=True)
            if f"TeamIdentifier={team}" not in result.stderr.splitlines():
                fail("macOS code-signing TeamIdentifier does not match GOREECLOUD_APPLE_TEAM_ID")
    elif platform == "windows-x64":
        if sys.platform != "win32": fail("signed Windows setup must be verified on Windows")
        if path.parent.name != "signed": fail("Windows distribution installers must come from dist/windows/signed")
        thumb = os.environ.get("GOREECLOUD_WINDOWS_CERT_THUMBPRINT", "")
        if not re.fullmatch(r"[a-fA-F0-9]{40}", thumb): fail("GOREECLOUD_WINDOWS_CERT_THUMBPRINT is required")
        if not os.environ.get("GOREECLOUD_WINDOWS_CERT_SUBJECT"):
            fail("GOREECLOUD_WINDOWS_CERT_SUBJECT is required for publisher identity verification")
        cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
               str(ROOT / "scripts/sign-windows-file.ps1"), "-VerifyOnly",
               "-FilePath", str(path), "-CertificateThumbprint", thumb,
               "-TimestampUrl", os.environ.get("GOREECLOUD_WINDOWS_TIMESTAMP_URL", "https://timestamp.digicert.com")]
        subprocess.run(cmd, check=True)
    elif platform.startswith("linux"):
        public = ROOT / "packaging/update-key.pub"
        if not public.read_text().startswith("untrusted comment:"):
            fail("GoreeCloud minisign public key is not configured")
        signature = signature_file or path.with_name(path.name + ".minisig")
        if not signature.is_file(): fail("no detached minisign signature")
        subprocess.run(["minisign", "-Vm", str(path), "-x", str(signature), "-p", str(public)], check=True)

def audit(path: Path, distribution: bool, signature_file: Path | None = None) -> dict[str, object]:
    if not path.is_file(): fail(f"missing artifact: {path}")
    kind, v = classify(path.name)
    if v != version(): fail(f"{path.name} is version {v}; Cargo.toml expects {version()}")
    digest = checksum(path)
    if kind.startswith("macos"): macos(path, kind)
    elif kind == "linux-x86_64-tar": linux_tar(path)
    else: executable(path, kind)
    if signature_file and not kind.startswith("linux"):
        fail("--signature-file is only valid for a Linux artifact")
    if distribution: verify_distribution(path, kind, signature_file)
    return {"artifact": path.name, "platform": kind, "version": v,
            "sha256": digest, "bytes": path.stat().st_size,
            "verified": "platform signature and distribution checks" if distribution else
                        "content and checksum only; NOT a distribution signature"}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distribution", action="store_true",
                        help="verify native signing/notarization or minisign; reject if unconfigured")
    parser.add_argument("--json", action="store_true", help="print report JSON")
    parser.add_argument("--signature-file", type=Path,
                        help="Linux: detached minisign signature from the temporary signing stage")
    parser.add_argument("artifacts", nargs="+", type=Path)
    args = parser.parse_args()
    if args.signature_file and (not args.distribution or len(args.artifacts) != 1):
        parser.error("--signature-file requires --distribution and exactly one Linux artifact")
    reports = []
    for artifact in args.artifacts:
        try: reports.append(audit(artifact.resolve(), args.distribution,
                                 args.signature_file.resolve() if args.signature_file else None))
        except (ValueError, OSError, subprocess.CalledProcessError) as error:
            print(f"FAIL: {artifact}: {error}", file=sys.stderr)
            return 1
    if args.json: print(json.dumps(reports, indent=2))
    else:
        for report in reports:
            print(f"PASS {report['artifact']}: {report['platform']} SHA-256 and contents; {report['verified']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
