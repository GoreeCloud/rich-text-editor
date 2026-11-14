# GoreeCloud Rich Text Editor — release operations

**Status: source beta, not approved for public distribution.** The **first release target is Linux x64** (AppImage and tarball). Windows remains CI-tested, with public distribution deferred until native GUI acceptance. macOS is deferred. Windows and Apple credentials are not prerequisites for Linux. Unsigned CI packages are validation artifacts; updates remain disabled. See the [Linux-first plan](LINUX_FIRST_RELEASE_PLAN.md).

## 1. Gate and artifact validation

Run the release auditor **before** moving artifacts into a publish directory:

```sh
python3 -B scripts/test_release_audit.py
python3 -B scripts/audit-release-artifacts.py path/to/package.zip
```

The audit checks a package's version, filename, SHA-256 sidecar and platform-specific contents. The output explicitly states that **a checksum and package structure are not a signature**. Replacing a package and its sidecar together does not prove who produced it.

`--distribution` is a separate fail-closed mode that requires deliberate release activation and platform-native verification. It refuses unconfigured/unsigned packages, including unsigned macOS CI ZIPs. Run it **on the native platform** where the signature can actually be assessed (Windows on Windows, macOS on macOS). Linux packages require a detached minisign signature. Keep your private keys outside the repo and never place their contents in GitHub issues, logs or chat.

The proposed download bucket and hostname must be configured by the owner as `GOREECLOUD_DOWNLOAD_BUCKET` and `GOREECLOUD_DOWNLOAD_HOST`. The host must be an HTTPS origin owned by GoreeCloud, not Quiet.md's endpoint, `updates.invalid`, a localhost address, or any other unowned placeholder. Passing the hostname format check **does not prove DNS ownership**.

## 2. macOS (deferred): Developer ID signing and notarization

**Do not treat this section as part of the initial Linux release
checklist.** Apple hardware, Developer ID enrollment and notarization are
not on the initial release roadmap. Keep macOS CI validation for feedback,
but do not publish or label unsigned macOS artifacts as trusted installers.
The following instructions are retained solely for an eventual decision to
support independently signed and notarized macOS distribution.

Requires a Mac with Xcode command-line tools, an Apple Developer Program team, a **Developer ID Application** signing certificate accessible in that Mac's keychain, and a stored `notarytool` authentication profile. Have your Apple team administrator provision these; do not commit the private key or password. Apple requires the hardened runtime, an appropriate Developer ID signature and a secure timestamp to notarize outside-the-App-Store apps.

Check your credentials locally:

```sh
security find-identity -v -p codesigning
xcrun notarytool history --keychain-profile "$NOTARY_PROFILE"
```

Then set all four variables intentionally:

```sh
export GOREECLOUD_RELEASE_ENABLED=yes
export GOREECLOUD_APPLE_TEAM_ID=REPLACE_WITH_10_CHARACTER_TEAM_ID
export SIGNING_IDENTITY='Developer ID Application: YOUR LEGAL PUBLISHER (YOUR_TEAM_ID)'
export NOTARY_PROFILE=YOUR_EXISTING_KEYCHAIN_PROFILE
scripts/release.sh
```

`scripts/release.sh` verifies the application's expected team, signs with hardened runtime and timestamp, uploads the signed ZIP to the Apple notary service, requires an **Accepted** response, staples the app, and checks both `stapler` and Gatekeeper before creating the final ZIP. A failure exits without a distributable artifact. Build arm64 and x86_64 variants separately.

For the alternate DMG flow, set `CODESIGN_ID` to the same identity and run `scripts/package.sh` on the Mac. It now refuses to guess a keychain identity, uses a separate output directory, requires Accepted notarization and fails on a rejected Gatekeeper assessment.

Verify the signed app on a separate macOS installation after downloading it (Gatekeeper quarantine behavior may differ from a build machine). To inspect a signed ZIP using the full preflight:

```sh
export GOREECLOUD_DOWNLOAD_HOST=https://YOUR_VERIFIED_RELEASE_DOMAIN
export GOREECLOUD_DOWNLOAD_BUCKET=YOUR_RELEASE_BUCKET
python3 scripts/audit-release-artifacts.py --distribution dist-release.XXXXXX/goreecloud-rich-text-editor-VERSION-macos-arm64.zip
```

## 3. Windows: Authenticode and installer verification

Use a Windows machine or signing service with an accessible **code-signing** certificate, an RFC 3161 timestamp server and the Windows SDK SignTool. Run in a Visual Studio Developer PowerShell. The certificate's actual legal subject and thumbprint must be pinned **explicitly**; a certificate from a different publisher is rejected.

```powershell
$env:GOREECLOUD_RELEASE_ENABLED = 'yes'
$env:GOREECLOUD_WINDOWS_CERT_SUBJECT = 'CN=EXACT CERTIFICATE SUBJECT, O=...'
$env:GOREECLOUD_WINDOWS_CERT_THUMBPRINT = 'YOUR_40_CHARACTER_HEX_THUMBPRINT'
$env:GOREECLOUD_DOWNLOAD_HOST = 'https://YOUR_VERIFIED_RELEASE_DOMAIN'
$env:GOREECLOUD_DOWNLOAD_BUCKET = 'YOUR_RELEASE_BUCKET'

scripts/package-windows.ps1 -CertificateThumbprint $env:GOREECLOUD_WINDOWS_CERT_THUMBPRINT -TimestampUrl 'https://timestamp.digicert.com'
python scripts/audit-release-artifacts.py --distribution dist/windows/signed/goreecloud-rich-text-editor-VERSION-windows-x64-setup.exe
```

The installer build checks the cert's private key, expiration and code-signing EKU, signs the app, signs the installer, and verifies Authenticode, expected publisher and timestamp. Do a fresh install, Markdown “Open with”, upgrade and uninstall on a disposable Windows test account. The **unsigned** CI installer is not a signed release.

## 4. Linux packages and independent update signatures

The Linux tarball and AppImage already build in CI, pass checksum verification and have a real-GUI startup smoke test on a disposable library. Linux package publication additionally requires a detached minisign signature. Generate a **new GoreeCloud-owned** minisign key pair on a secured owner-controlled system:

```sh
minisign -G -p packaging/update-key.pub -s "$HOME/.minisign/goreecloud-rich-text-editor.key"
```

Keep the secret key on the signing machine, add only the public key to this repo, then validate it from another installation. Never reuse Quiet.md's signing key.

The publisher `scripts/publish-downloads.sh` runs **once per native signing platform family**: macOS arm64 and Intel may be signed and published together on the same Mac, Windows must be verified on Windows, and Linux may be verified on a system with minisign. Do not pass a Windows installer and a macOS ZIP in the same command. All supplied files are checked for integrity and duplicate platforms first. Each candidate is copied to a disposable private staging directory and checked again, then minisign-signed and verified **against the pinned GoreeCloud key**. macOS and Windows must pass platform-native signing/notarization checks before any upload; Linux must pass detached minisign verification. The publisher uploads the packages and versioned signatures first, verifies delivery, and publishes the update manifests **after all packages in that invocation have passed**. This limits partial release exposure but cannot guarantee atomic deployment across separate operating systems.

The publisher `scripts/publish-downloads.sh` is gated on `GOREECLOUD_RELEASE_ENABLED=yes`, a bucket, a host and a configured public/private minisign pair. It validates package contents and checksums before it signs or uploads, publishes versioned packages first, verifies they are served, and writes the `latest/update-<platform>.json` manifest last. Run a **DRY_RUN** and inspect the output before any actual upload. The host and bucket values above are placeholders until the owner has configured DNS, bucket permissions and the distribution service.

`src/update.rs` deliberately retains `UPDATES_CONFIGURED = false` and the non-resolving `updates.invalid` host. **Do not change these** until the new public key is committed, signed packages are live at the GoreeCloud-owned host, and update/rollback/failed-network tests pass on disposable installations. Running the publisher by itself does not enable automatic updates.

## 5. Human acceptance checklist — Linux first

Exercise both final Linux packages on a clean physical Linux desktop, not only in CI. Record the OS version, checksum, app version and observed result. Windows/macOS acceptance is deferred and does not block Linux:

- [ ] Deferred only — macOS arm64 and x86_64: no public macOS release without a valid developer team, notarization, trusted final artifact, and separate device-level acceptance
- [ ] Deferred — Windows x64: complete native GUI validation and trusted publisher verification when Windows distribution is planned
- [ ] Linux x64: tarball and AppImage start on a physical display; icons, font rendering, image scaling and keyboard/mouse interactions work
- [ ] Linux x64: create a Markdown note, type Unicode, close/reopen, confirm disk persistence and Markdown round-trip
- [ ] Linux x64: create a rich-text note, insert an image/table, save, restart and inspect recovery after a simulated interrupted write
- [ ] Linux x64: import an external Markdown file with spaces in its path, edit and save it, confirm the original is not unexpectedly overwritten before Save
- [ ] Linux x64: defaults have no external web-image fetches or automatic update requests; individual opt-in respects HTTP(S)-only redirects and limits
- [ ] Linux x64: print/export with expected formatting and file permissions; check accessibility, high DPI and dark theme
- [ ] Linux x64: update with the **GoreeCloud-signed** release, reject a tampered artifact, gracefully recover from interrupted download and preserve existing notes
- [ ] Verify fresh-machine install from the public HTTPS host, compare checksum, confirm no upstream brand/assets or unlicensed works remain

### Validated so far (2026-11-13)

- GitHub Actions macOS/Windows/Linux unsigned builds, tests and packaging pass at merged commit `7ad3b2d`.
- Existing AppImage launched on a **physical Linux desktop**, displayed an intact GoreeCloud UI (sidebar, cards and graphics), and used an isolated temporary notes library. This is *limited visual validation*, not a complete interactive accessibility/printing test.
- Isolated virtual-X11 AppImage smoke checks the real window, seeds 12 onboarding documents, and catches the prior broken `quiet_md` launcher.
- **No real Developer ID, Windows Authenticode or production update-key verification has happened** because the owner's signing keys, developer-team authorization and release-host credentials are not connected.

## References

- Apple: https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
- Microsoft: https://learn.microsoft.com/windows/win32/seccrypto/signtool
