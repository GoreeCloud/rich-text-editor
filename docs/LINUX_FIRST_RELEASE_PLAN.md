# Linux-first release plan

**Priority 1: Linux x64. Priority 2: Windows x64. macOS: deferred.**

Linux is the first public-distribution candidate. Windows remains maintained
through hosted CI, but Windows release acceptance is postponed until a suitable
native GUI test environment is available. **Windows hardware, Windows signing
credentials, and Apple enrollment are not prerequisites for shipping Linux.**

The repository is a source beta; production release keys and hosting are
unconfigured. Automatic updates remain disabled.

## Priority 1 — Linux x64 AppImage and tarball

**Automated gate:** Build on Ubuntu 22.04 x86_64 (glibc 2.35 baseline).
Run Rust tests and Clippy; package both the AppImage and portable tarball;
verify SHA-256 sidecars, license notices, runtime dependency reports, and
real GUI startup of **both** the AppImage and the packaged tarball binary
under an isolated Linux X11 session. Continue isolated real-GUI creation, editing, and
save/reopen tests for rich-text notes and native Markdown, including Unicode.
Run `python3 -B scripts/test_linux_release.py` and
`python3 -B scripts/check-linux-release.py dist/linux` to validate the
**pair** of packages, glibc 2.35 baseline, checksums and runtime reports.
This is an offline candidate gate, not a cryptographic signature check.

**Native Linux acceptance:** On a clean Linux desktop, open both final
packages and test keyboard/mouse, fonts, dark mode, DPI scaling, local
library paths, importing external Markdown with spaces/Unicode, saving,
printing/exporting, attachments/images/tables, and interrupted-write recovery.
Confirm no unauthorized network connections or access to Quiet.md notes.

**Signed distribution gate:** Create an independent GoreeCloud minisign key
on a secured Linux system; commit only the public key. Verify detached
signatures on downloaded packages and validate actual distribution checksums.
Configure a GoreeCloud-controlled HTTPS host/bucket before using the existing
signed-update publisher. Never expose a private key in Git, logs, or chat.
Automatic updates remain disabled until signed updates, failed downloads,
and rollback/recovery are tested on disposable Linux libraries.

GitHub CI packages can be shared only as **explicitly unsigned development
artifacts**. Do not label them signed public releases or silently enable
updates. Windows or Apple credentials never block this Linux release path.

## Priority 2 — Windows x64, CI maintenance until native acceptance

Continue GitHub-hosted Windows Rust builds/tests, package audits, and
ephemeral install/reinstall/uninstall smoke tests. No personal Windows
device is required for those CI tasks. The generated installer remains an
**unsigned validation artifact**, not an Authenticode-verified release.

When a trusted Windows VM or suitable native test environment is available,
complete real GUI Markdown/rich-text acceptance, Unicode paths, accessibility,
high DPI, printing/export, recovery and file-association QA. Windows
publisher signing and trusted timestamping apply **only** to the later
Windows release, not to Linux.

## Priority 3 — macOS compatibility CI only

Keep macOS hosted build/tests when useful. Unsigned CI app bundles are not
notarized distributable releases. Developer ID, Apple hardware and
notarization are out of scope unless macOS distribution is reconsidered.
Never bypass the current macOS signing gate to create public packages.

## Shared safety invariants

Preserve the MIT and third-party attribution, independent GoreeCloud notes
directory and opt-in web-image behavior. Keep strict checksums, expected
package names, pinned public signatures and owner-controlled release hosts.
The update flag `UPDATES_CONFIGURED` stays `false` until an
independently signed release channel and rollback checks actually exist.

Review the [release readiness](RELEASE_READINESS.md) checklist and the
[release operations](RELEASE_OPERATIONS.md) runbook for platform-specific
verification. **The first Linux release does not depend on a Windows or
macOS release.**
