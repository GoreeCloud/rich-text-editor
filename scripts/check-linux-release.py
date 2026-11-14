#!/usr/bin/env python3
"""Fail-closed offline validation of a *pair* of Linux x64 candidate packages.

Checks the tarball, AppImage, checksums, packaged license notices, glibc
compatibility report, and unresolved-library reports. This deliberately
does NOT claim packages are signed or authorized for public distribution.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("linux_release_package_audit", ROOT / "scripts/audit-release-artifacts.py")
assert spec and spec.loader
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)

def validate(directory: Path) -> dict[str, object]:
    if not directory.is_dir():
        raise ValueError(f"Missing Linux package directory: {directory}")
    version = audit.version()
    base = f"goreecloud-rich-text-editor-{version}"
    tar = directory / f"{base}-linux-x86_64.tar.gz"
    app = directory / f"{base}-x86_64.AppImage"
    expected = {tar.name, app.name}
    packages = {p.name for p in directory.iterdir() if p.is_file() and (
        p.name.endswith(".AppImage") or p.name.endswith(".tar.gz"))}
    if packages != expected:
        raise ValueError(f"Expected exactly two Linux v{version} candidates: {sorted(expected)}; got {sorted(packages)}")

    reports = [audit.audit(tar, False), audit.audit(app, False)]
    for path in (tar, app):
        if path.stat().st_size == 0:
            raise ValueError(f"Empty release candidate: {path.name}")

    # The appimage packaging script creates and audits both diagnostics.
    glibc = app.with_name(app.name + ".glibc.txt")
    libraries = app.with_name(app.name + ".libraries.txt")
    for diagnostic in (glibc, libraries):
        if not diagnostic.is_file() or not (0 < diagnostic.stat().st_size <= 1_000_000):
            raise ValueError(f"Missing or invalid AppImage diagnostic: {diagnostic.name}")
    versions = []
    for line in glibc.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not re.fullmatch(r"[0-9]+\.[0-9]+(?:\.[0-9]+)?", line):
            raise ValueError(f"Invalid GLIBC version in diagnostic: {line}")
        versions.append(tuple(int(x) for x in line.split(".")))
    if not versions:
        raise ValueError("Empty AppImage GLIBC compatibility report")
    highest = max(versions)
    if highest[:2] > (2, 35):
        raise ValueError(f"AppImage exceeds Ubuntu 22.04 GLIBC 2.35 baseline: {'.'.join(map(str, highest))}")
    if "not found" in libraries.read_text(encoding="utf-8").lower():
        raise ValueError("AppImage runtime report contains unresolved libraries")

    with tarfile.open(tar, "r:gz") as stream:
        member = stream.getmember(f"{base}-linux-x86_64/runtime-libraries.txt")
        if not member.isfile() or member.size > 1_000_000:
            raise ValueError("Invalid packaged tarball runtime library report")
        fp = stream.extractfile(member)
        if fp is None:
            raise ValueError("Unreadable tarball runtime library report")
        details = fp.read().decode("utf-8", errors="replace")
        if not details.strip() or "not found" in details.lower():
            raise ValueError("Tarball contains an empty or unresolved runtime library report")

    return {"version": version, "glibc_max": ".".join(map(str, highest)),
            "artifacts": [report["artifact"] for report in reports]}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, nargs="?", default=Path("dist/linux"))
    args = parser.parse_args()
    try:
        report = validate(args.directory)
    except (ValueError, OSError, tarfile.TarError) as err:
        print(f"FAIL Linux candidate: {err}", file=sys.stderr)
        return 1
    print(f"PASS Linux x64 v{report['version']} candidate pair: {', '.join(report['artifacts'])}")
    print(f"PASS GLIBC max {report['glibc_max']} <= 2.35; checksums, package contents and library reports verified.")
    print("Validation only: signing and public distribution authorization are NOT verified.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
