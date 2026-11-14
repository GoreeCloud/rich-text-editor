# GoreeCloud Rich Text Editor — engineering and release readiness

This repository is an independently branded source import of Quiet.md. The upstream revision and MIT attribution are recorded in [UPSTREAM.md](../UPSTREAM.md) and [LICENSE](../LICENSE).

## Initial release scope — Linux first

**Linux x64 is the first public-release target**, with an AppImage and
portable tarball. Native Linux acceptance, package integrity and Linux-only
signing/distribution are its release gates. **Windows x64 is the next stage:**
retain the GitHub-hosted builds and installer lifecycle tests, but defer
Windows distribution until suitable native GUI acceptance is possible.
macOS remains deferred, with CI compatibility validation where practical.

No Windows or Apple device, Authenticode certificate or Apple Developer ID
is required to complete the Linux release. Preserve fail-closed signing
checks if Windows or macOS distribution is later attempted. All currently
unsigned CI packages remain labeled for testing and automatic updates
remain disabled.

See the [Linux-first release plan](LINUX_FIRST_RELEASE_PLAN.md).

## Source-level validation

Run the lightweight brand, attribution, data-safety and icon audit:

```bash
python3 scripts/rebrand_guard.py
```

Run the platform Rust test and lint suite (requires the platform dependencies listed in [CONTRIBUTING.md](../CONTRIBUTING.md)):

```bash
cargo check --locked --workspace
scripts/check.sh
```

`scripts/check.sh` runs `scripts/rebrand_guard.py`, Rust workspace tests, bundled guide checks, and Clippy (including `devtools`). CI runs native build and packaging jobs for macOS, Windows and Linux.

## Current safety guarantees

- The app's bundle/package identifiers and default notes directory are independent of Quiet.md.
- Automatic updates are explicitly disabled in `src/update.rs` until a GoreeCloud-signed distribution and update endpoint exist.
- Release publishing is gated on explicit configuration; do not point this fork to upstream's download bucket.
- Cloudflare analytics and website settings do not reuse the upstream zone and database IDs.
- Original MIT attributions and third-party notices are included; app-shell Nucleo assets were replaced with Lucide ISC icons.
- No user library migration is performed automatically.

## Tasks before distributing the initial Linux release

- [ ] Run `python3 -B scripts/check-linux-release.py dist/linux` on the paired Linux candidates; check both package checksums, GLIBC compatibility and dependency reports.
- [ ] Run `scripts/smoke-linux-tarball.sh dist/linux/goreecloud-rich-text-editor-*-linux-x86_64.tar.gz` and the AppImage smoke on candidate packages; these use disposable X11 libraries and do not replace physical-desktop QA.
- [ ] Verify final AppImage/tarball behavior on a physical Linux desktop: Markdown import/edit, native rich text, Unicode paths, printing/export, fonts, persistence, and interrupted-write recovery. Windows/macOS GUI acceptance is deferred.
- [ ] Run `scripts/check.sh` and verify the current GitHub Actions CI jobs are green on the release commit.
- [ ] Create an independent **production** GoreeCloud minisign key and verify detached signatures on Linux packages. CI only uses disposable test keys; Windows Authenticode and Apple notarization are not Linux release gates.
- [ ] For signed Linux publishing, configure a GoreeCloud-owned HTTPS host/bucket. Keep `src/update.rs` disabled until independent Linux update and rollback tests pass.
- [ ] Test manual Linux upgrades, failure/recovery and (later) signed updates on disposable Linux systems.
- [ ] Publish both verified Linux packages and their SHA-256 sidecars and detached minisign signatures once the Linux release gate passes; publish an update feed **only for AppImage** and keep unsigned CI artifacts clearly labeled.
- [ ] Validate app name, documentation, translated onboarding guides, screenshots, accessibility and any remaining upstream terminology.

The app's core note engine supports both Markdown files and Feishu/Lark DocxXML documents. This project should not claim that every note is stored as Markdown.

The Linux GUI regression additionally opens a local Markdown file through the
application command line using a filename with **Unicode and spaces**. It
verifies that the external source bytes and modification timestamp are
unchanged, the file is linked in the library rather than copied, unrelated
non-Markdown command-line files are ignored, and the same local-file record
survives closing/reopening the app. It then edits the original file through
the GUI, verifies Unicode text was saved at that **same external path**,
and checks its bytes survive another full restart. The external note is
explicitly marked `0600` before opening; its private permissions
must remain unchanged after saving and reopening. Existing nonprivate modes
are covered by Rust storage tests. Printing/export and additional real
desktop environments still require separate acceptance.

## Import hardening checks

The static public landing page intentionally contains no downloadable package links until GoreeCloud releases exist. The updater uses the reserved `https://updates.invalid/` placeholder and an unconfigured public-key file; both must be replaced with GoreeCloud-owned infrastructure before explicitly enabling updates. Reusing upstream signing keys or download domains is prohibited.

Linux AppImage packaging smoke-tests the extracted `AppRun` launcher with an isolated stub executable and checks that the correct binary is selected with forwarded arguments. This avoids running the GUI or touching notes during CI.

The first-launch guide includes an original GoreeCloud-branded one-page PDF quick reference. The guide's source and bundled assets must remain byte-identical; `rebrand_guard.py` enforces this.

The Windows installer, macOS app/DMG, Linux tarball, and AppImage must all ship both `LICENSE` and `THIRD_PARTY.md`; the Linux tarball packaging step verifies its output archive contents.

## Web-image privacy baseline

New libraries start with remote-image fetching and automatic update checks off. User preferences explicitly saved as enabled remain enabled, but the release updater itself stays disabled until separately configured. Optional web-image downloads accept HTTP(S) only, follow only HTTP(S) redirects, cap transfers at 20 MiB, and time out. CI tests both preference persistence and the restricted curl command line without contacting external hosts.

## Release process and signature verification

The [release operations runbook](RELEASE_OPERATIONS.md) contains platform-specific Developer ID/Apple notarization, Windows Authenticode and RFC 3161 timestamps, Linux minisign and GoreeCloud-owned R2 release-host steps. `scripts/audit-release-artifacts.py` checks validation package filenames, expected version, SHA-256 and inner contents on all platforms; in `--distribution` mode it refuses release approval without real signing, hosting configuration and native signature verification. `scripts/test_release_audit.py` supplies synthetic positive and negative examples.

The existing Linux desktop has been visually checked on a real hardware-backed desktop using a **disposable isolated notes library** and an app-only screenshot. The sidebar, text, document cards and images rendered; this does not replace full interaction, printing, accessibility or macOS/Windows installation tests. No signing certificates or notarization credentials have been connected, and the update channel remains disabled.

The Linux real-AppImage smoke also bounds diagnostic output and reaps any extracted child process that inherited the unique disposable library marker, even if the AppImage launcher exits first. The test was validated against both a good package and the original broken launcher, with no leftover process or disk-space growth.


## Windows installer lifecycle automation

The Windows CI job now runs the freshly built unsigned Inno Setup installer
in the ephemeral GitHub runner account, using a unique temporary application
folder and separate Markdown notes folder. It verifies the installed program,
C++ runtime, required legal notices and per-user Markdown association, then
reinstalls the same version and silently uninstalls. SHA-256 checks ensure
independent Unicode/space-containing Markdown notes remain unchanged. A
120-second timeout applies to each installer process. Outside GitHub Actions,
this script requires an explicit GOREECLOUD_WINDOWS_SMOKE_TEST=yes opt-in on a
throwaway Windows account. It **does not** substitute for interactive GUI QA
or test signed production installer trust dialogs on an end-user machine.

## Pre-activation updater protocol hardening

Automatic updates are still disabled. When the channel is eventually enabled,
release builds ignore the development-only GOREECLOUD_RTE_UPDATE_URL environment
override. Local development/test builds may point only at HTTP loopback ports;
arbitrary hosts, files and remote HTTP overrides are not valid. The manifest
must refer to the **exact** versioned GoreeCloud package URL, including the
three-part numeric version and correct platform. The curl client disables
user ~/.curlrc, allows only HTTPS in production (including redirects), limits
redirect count, restricts feed manifests to 64 KiB, and caps package download
transfer to the validated manifest size. A detached minisign signature and
matching trusted comment remain mandatory for the actual payload.
These limits are exercised in Rust tests without contacting a network.

## Linux interactive editing regression

Linux CI now builds an explicitly **devtools-only** binary and launches it
in two temporary Xvfb sessions using isolated HOME/XDG directories and a
unique notes library. A synthetic GPUI left click establishes editor focus,
Ctrl+N creates a rich-text note, typing changes both its title and body, and
the test waits for save. It verifies the serialized note contains distinct
title and body tokens, reopens the same library in a new process and checks
the file's SHA-256 remains identical. The script bounds diagnostics,
terminates its own process group, and deletes the temporary library only
after success. This is an editor persistence regression test, **not** proof
of final rendering quality, real keyboard accessibility, PDF printing, or
signed Windows/macOS releases.

## Distribution upload preflight

Before any real release upload, the publisher now checks every input, refuses
duplicate platforms or mixed native signing families, and stages copies into a
private directory (preventing checksum/signature race conditions). It verifies
the **native signed Windows installer and notarized macOS bundle** (on their
respective OS), or the staged Linux minisign signature, before uploading any
package. Update-feed manifests are published only after every supplied package
has uploaded and is reachable. This still does not make independent multi-OS
rollouts atomic. Offline dry-run tests exercise positive and adversarial
publishing scenarios on both macOS and Linux CI runners. No release signing
keys or host have been configured.


Optional remote-image fetching also uses `curl -q` as its first argument so existing user `.curlrc` settings cannot silently override TLS verification, network protocols, or transfer limits. This is checked by the web-image Rust test and rebrand guard.

Windows remote-image fetching streams through a Rust-opened local file rather than passing the cache path as a curl.exe output argument; this protects Unicode user-folder paths and suppresses curl console flashes. The Rust integration test fetches an original PNG from an in-process 127.0.0.1 server into a Unicode file, with no outside network access.

Windows Unicode-path remote image downloads explicitly request curl binary stdout (`--output -`) and let Rust write the decoded cache path natively. This avoids code-page corruption in file arguments and the binary-output fallback on Windows.

The isolated Linux X11 acceptance suite now exercises both the app's normal
rich-text document format and a second disposable library configured for
Markdown. It opens the actual GUI, creates a note via Ctrl+N, types the title
and body (including Unicode for Markdown), closes and reopens the process,
and checks persisted bytes and the Markdown title index. This does not
establish Windows/macOS GUI round-trip or accessibility acceptance.

The optional upstream Cloudflare analytics worker and backfill were removed
from this derivative because they targeted Quiet.md infrastructure and have
no role in the local-first application. The `services/stats` directory retains
only a retirement explanation and link to the historical upstream source.
The optional contributor-avatar generator defaults to the independent
GoreeCloud GitHub repository.

Unreferenced promotional screenshots and background images imported from the
upstream static site were removed as well. The independent GoreeCloud logo,
icon, and active source-preview HTML were retained; runtime app resources
and historical release notes remain unchanged.
