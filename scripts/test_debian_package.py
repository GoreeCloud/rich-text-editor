#!/usr/bin/env python3
"""Audit a GoreeCloud Notes unsigned Debian CI package without installing it."""
import hashlib
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parent.parent
packages = sorted((root / "dist/linux").glob("goreecloud-notes_*_amd64.deb"))
assert len(packages) == 1, f"Expected one Debian candidate, got {packages}"
pkg = packages[0]

def field(name):
    return subprocess.check_output(["dpkg-deb", "--field", str(pkg), name], text=True).strip()

assert field("Package") == "goreecloud-rich-text-editor"
assert field("Architecture") == "amd64"
assert field("Homepage") == "https://github.com/GoreeCloud/notes"
import re
cargo_version = re.search(r'^version = "([^"]+)"', (root / "Cargo.toml").read_text(), re.MULTILINE).group(1)
assert field("Version").startswith(cargo_version + "~ci")
assert "GoreeCloud Notes" in field("Description")
assert "libc6" in field("Depends")
checksum = pkg.with_name(pkg.name + ".sha256")
assert checksum.is_file()
assert checksum.read_text().split()[0] == hashlib.sha256(pkg.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix="goreecloud-deb-audit-") as tmp:
    target = Path(tmp)
    subprocess.run(["dpkg-deb", "--extract", str(pkg), str(target)], check=True)
    app = target / "usr/bin/goreecloud_rich_text_editor"
    original = root / "target/release/goreecloud_rich_text_editor"
    assert app.is_file() and original.is_file()
    assert app.read_bytes() == original.read_bytes(), "Packaged executable differs from source build"
    entry = target / "usr/share/applications/com.goreecloud.richtexteditor.desktop"
    assert "Exec=goreecloud_rich_text_editor %F" in entry.read_text()
    assert "Categories=Office;TextEditor;" in entry.read_text()
    assert (target / "usr/share/icons/hicolor/512x512/apps/com.goreecloud.richtexteditor.png").is_file()
    for notice in ("LICENSE", "THIRD_PARTY.md"):
        assert (target / "usr/share/doc/goreecloud-rich-text-editor" / notice).is_file()
    assert not (target / "DEBIAN").exists(), "Maintainer scripts or control files must not ship as payload"
print(f"Unsigned Debian candidate audited: {pkg.name}")
