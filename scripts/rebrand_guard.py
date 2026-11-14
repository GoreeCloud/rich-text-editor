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

def production_rust(path: str) -> str:
    """Ignore unit-test fixtures when checking executable settings and security flags."""
    return read(path).split("#[cfg(test)]", 1)[0]

GUIDE = "goreecloud-rich-text-editor-cheatsheet.pdf"
GUIDE_SOURCE = ROOT / "shared-mock/guides/assets" / GUIDE
GUIDE_BUNDLED = ROOT / "shared-mock/library/assets/guides" / GUIDE

checks = {
    "application identifier": 'com.goreecloud.richtexteditor' in read("src/main.rs"),
    "binary name": 'name = "goreecloud_rich_text_editor"' in read("Cargo.toml"),
    "independent notes directory": '.join("GoreeCloud Rich Text Editor")' in read("crates/core/src/store.rs"),
    "upstream auto-updates disabled": 'const UPDATES_CONFIGURED: bool = false;' in read("src/update.rs"),
    "private new-library web image default": "remote_images: false" in production_rust("src/settings.rs"),
    "private new-library updater default": "auto_update: false" in production_rust("src/settings.rs"),
    "web image redirects protocol restricted": '"--proto-redir", "=http,https"' in production_rust("src/editor/image.rs"),
    "web image stdout output binary": '"--output", "-", "--"' in production_rust("src/editor/image.rs"),
    "web image cache path native Unicode": 'image_download_command(url)' in production_rust("src/editor/image.rs") and 'Stdio::from(out)' in production_rust("src/editor/image.rs"),
    "Windows image downloads hide console": 'cmd.creation_flags(0x0800_0000)' in production_rust("src/editor/image.rs"),
    "web image curlrc disabled": 'cmd.args(["-q", "--fail"' in production_rust("src/editor/image.rs"),
    "web image downloads capped": '"--max-filesize", "20971520"' in production_rust("src/editor/image.rs"),
    "release builds ignore update URL override": 'if !(cfg!(test) || cfg!(debug_assertions)) { return None; }' in production_rust("src/update.rs"),
    "development update feeds are loopback-only": 'url.strip_prefix("http://127.0.0.1:")' in production_rust("src/update.rs"),
    "update manifest URL is exact versioned path": 'm.url != format!("{package_origin}v{}/{name}", m.version)' in production_rust("src/update.rs"),
    "update curl disables user curlrc": 'cmd.args(["-q", "-fsSL"' in production_rust("src/update.rs"),
    "local update feed cannot redirect away": 'let max_redirs = if loopback { "0" } else { "5" };' in production_rust("src/update.rs"),
    "update curl restricts redirected protocols": '"--proto-redir", proto' in production_rust("src/update.rs") and '"--max-redirs", max_redirs' in production_rust("src/update.rs"),
    "update manifest max response size": '"--max-filesize", "65536"' in production_rust("src/update.rs"),
    "update packages bounded before download": '"--max-filesize", &max_size' in production_rust("src/update.rs"),
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
    "Windows installer lifecycle smoke wired": "scripts/smoke-windows-installer.ps1" in read(".github/workflows/ci.yml") and "Smoke-test Windows installation, reinstall and uninstall" in read(".github/workflows/ci.yml"),
    "Windows install QA isolated notes": "External Notes with spaces" in read("scripts/smoke-windows-installer.ps1") and "Get-FileHash" in read("scripts/smoke-windows-installer.ps1"),
    "Windows test requires disposable account": "GOREECLOUD_WINDOWS_SMOKE_TEST" in read("scripts/smoke-windows-installer.ps1") and "GITHUB_ACTIONS" in read("scripts/smoke-windows-installer.ps1"),
    "Windows installer includes third-party notices": "THIRD_PARTY.md" in read("packaging/windows/goreecloud-rich-text-editor.iss"),
    "Linux tar includes third-party notices": "install -m644 THIRD_PARTY.md" in read("scripts/package-linux.sh") and "tar -tf" in read("scripts/package-linux.sh"),
    "macOS DMG includes third-party notices": 'cp LICENSE THIRD_PARTY.md "$app/Contents/Resources/"' in read("scripts/package.sh"),
    "Windows signing tool matches installer": "SignTool=goreecloudrte" in read("packaging/windows/goreecloud-rich-text-editor.iss") and "/Sgoreecloudrte=" in read("scripts/package-windows.ps1"),
    "Linux app identity": "Name=GoreeCloud Rich Text Editor" in read("packaging/linux/com.goreecloud.richtexteditor.desktop"),
    "AppImage launcher calls renamed binary": 'exec "$appdir/usr/bin/goreecloud_rich_text_editor" "$@"' in read("packaging/linux/AppRun"),
    "AppImage launcher is smoke-tested": "AppImage launcher smoke test passed" in read("scripts/package-appimage.sh"),
    "Linux GUI smoke validates Markdown persistence": "--markdown" in read("scripts/smoke-linux-editor.py") and "LINUX_GUI_MARKDOWN_EDIT_SAVE_REOPEN_PASS" in read("scripts/smoke-linux-editor.py") and "index.json" in read("scripts/smoke-linux-editor.py"),
    "real Linux tarball executable smoke in CI": "scripts/smoke-linux-tarball.sh dist/linux/" in read(".github/workflows/ci.yml") and "scripts/smoke-linux-appimage.sh" in read("scripts/smoke-linux-tarball.sh"),
    "Linux tarball smoke streams only application member": 'tar -xOzf "$archive"' in read("scripts/smoke-linux-tarball.sh"),
    "Linux-first CI candidate gate": "scripts/test_linux_release.py" in read(".github/workflows/ci.yml") and "scripts/check-linux-release.py dist/linux" in read(".github/workflows/ci.yml"),
    "Linux AppImage downloader disables curlrc": "curl -q --fail --location" in read("scripts/package-appimage.sh"),
    "Linux candidate gate caps GLIBC": "highest[:2] > (2, 35)" in read("scripts/check-linux-release.py"),
    "Linux CI exercises both document formats": "scripts/smoke-linux-editor.py target/release/goreecloud_rich_text_editor --markdown" in read(".github/workflows/ci.yml"),
    "interactive Linux GUI edit QA in CI": "scripts/smoke-linux-editor.py" in read(".github/workflows/ci.yml") and "cargo build --release --locked --features devtools" in read(".github/workflows/ci.yml"),
    "interactive QA uses isolated notes home": 'GOREECLOUD_RTE_HOME=str(work / "library")' in read("scripts/smoke-linux-editor.py") and 'FDL_SCRIPT=str(source)' in read("scripts/smoke-linux-editor.py"),
    "GUI scripted clicks use platform-independent GPUI input": '"rclick" | "click" =>' in read("src/devtools.rs"),
    "GUI smoke reaps orphaned AppImage processes": "cleanup_smoke()" in read("scripts/smoke-linux-appimage.sh") and "GOREECLOUD_SMOKE_ROOT=$sandbox" in read("scripts/smoke-linux-appimage.sh"),
    "GUI smoke caps diagnostic output": "head -c 1048576" in read("scripts/smoke-linux-appimage.sh"),
    "release artifact audit wired across platforms": read(".github/workflows/ci.yml").count("scripts/audit-release-artifacts.py") == 3,
    "signed macOS release gate": "GOREECLOUD_RELEASE_ENABLED" in read("scripts/release.sh") and "TeamIdentifier=" in read("scripts/release.sh"),
    "signed Windows publisher pinned": "GOREECLOUD_WINDOWS_CERT_SUBJECT" in read("scripts/package-windows.ps1"),
    "DMG Gatekeeper may not be ignored": 'spctl -a -vvv -t install "$dmg"' in read("scripts/package.sh") and 'spctl -a -vvv -t install "$dmg" || true' not in read("scripts/package.sh"),
    "DMG package identity explicit": "GOREECLOUD_APPLE_TEAM_ID" in read("scripts/package.sh") and "CODESIGN_ID:?" in read("scripts/package.sh"),
    "publisher validates signed-channel origin": "GOREECLOUD_DOWNLOAD_HOST must be a GoreeCloud-owned HTTPS origin" in read("scripts/publish-downloads.sh"),
    "publisher requires native distribution verification": 'scripts/audit-release-artifacts.py --distribution "$file"' in read("scripts/publish-downloads.sh") and 'scripts/audit-release-artifacts.py --distribution --signature-file "$sig"' in read("scripts/publish-downloads.sh"),
    "publisher preflights all packages before upload": 'seen="$seen $platform"' in read("scripts/publish-downloads.sh") and 'mkdir -p "$work/signed"' in read("scripts/publish-downloads.sh"),
    "publisher refuses mixed native signing families": 'Mixed native signing platforms cannot be published together' in read("scripts/publish-downloads.sh"),
    "publisher stages all update manifests last": 'ready_manifests+=("$platform" "$manifest")' in read("scripts/publish-downloads.sh") and 'for ((i=0; i<' in read("scripts/publish-downloads.sh"),
    "publisher dry-run regression tests in CI": read(".github/workflows/ci.yml").count("scripts/test_publish_downloads.py") == 2,
    "publisher requires package audit": 'python3 -B scripts/audit-release-artifacts.py "$file"' in read("scripts/publish-downloads.sh"),
    "Windows verification pins publisher": "GOREECLOUD_WINDOWS_CERT_SUBJECT" in read("scripts/sign-windows-file.ps1"),
    "release scope is Linux-first": "Priority 1: Linux x64" in read("docs/LINUX_FIRST_RELEASE_PLAN.md") and "Priority 2: Windows x64" in read("docs/LINUX_FIRST_RELEASE_PLAN.md"),
    "Windows credentials do not block Linux": "Windows Authenticode and Apple notarization are not Linux release gates" in read("docs/RELEASE_READINESS.md"),
    "README gives Linux priority": "**Linux x64 is the first release target.**" in read("README.md"),
    "readiness has Linux-first release gate": "## Initial release scope — Linux first" in read("docs/RELEASE_READINESS.md"),
    "release publishing gated": "GOREECLOUD_RELEASE_ENABLED" in read("scripts/publish-downloads.sh"),
    "upstream analytics worker source retired": not any((ROOT / path).exists() for path in [
        "services/stats/wrangler.jsonc", "services/stats/wrangler.jsonc.example",
        "services/stats/backfill.mjs", "services/stats/src/index.js",
        "services/stats/migrations/0001_metrics.sql",
    ]),
    "contributor generator uses GoreeCloud repository": "'GoreeCloud/rich-text-editor'" in read("scripts/update-contributors.py"),
    "unreferenced upstream promotional art not bundled": not any((ROOT / "site/public" / name).exists() for name in ["home.jpg", "home-2000.webp", "home-1400.webp", "bg.png"]),
    "historical upstream release notes labeled": "not GoreeCloud Rich Text Editor releases" in read("docs/releases/README.md"),
    "placeholder site redirects to independent repository": 'const TARGET = "https://github.com/GoreeCloud/rich-text-editor"' in read("site/index.js"),
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
