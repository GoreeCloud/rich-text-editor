# Windows and Linux first-release plan

**Decision: 2026-11-13.** macOS signing and notarization are not on the
initial distribution roadmap. The first public distribution target is
**Windows x64 and Linux x64**. macOS release signing/notarization is a separate deferred
project: it is **not a prerequisite** for completing either target.

This is a scope decision, **not** a statement that the first signed release
has shipped. The current project is still a source beta with automatic
updates disabled and no configured GoreeCloud release host.

## Windows x64 — initial target

- The CI-built unsigned Inno Setup installer is a validation artifact,
  not an approved distribution package.
- Continue automated Rust checks, package-content/sidecar audits, and the
  disposable-runner install, reinstall and uninstall lifecycle smoke.
- Complete hands-on Windows GUI tests for new/edit/imported Markdown notes,
  rich text, persistence, high-DPI/fonts, file association, print/export,
  recovery and accessibility. Recheck with the **final signed package**.
- For a publicly trusted **signed** installer, obtain an owner-controlled
  Windows code-signing certificate or suitable signing service, pin its
  legal publisher and thumbprint, verify Authenticode and timestamp, and
  follow the Windows chapter of [release operations](RELEASE_OPERATIONS.md).
  **Apple credentials are irrelevant to Windows signing.**
- Do not advertise unsigned Windows CI artifacts as signed or broadly
  trusted by Windows SmartScreen.

## Linux x64 — initial target

- Continue CI validation of the AppImage and tarball, package checksums,
  the real AppImage startup smoke, and isolated GUI edit/save/reopen
  regression tests for both native Markdown and rich-text documents.
- Validate the final AppImage and tarball on a clean Linux environment,
  including external Unicode paths, persistence, fonts, keyboard/mouse
  behavior, export/print, recovery and runtime library dependencies.
- Before enabling the existing signed-update/distribution path, create a
  **new GoreeCloud-owned** minisign key pair, commit only its public key,
  test signatures against a clean installation, and use the gated release
  publisher and a verified HTTPS host. The current signature key is
  intentionally unconfigured.

## macOS — deferred, no Apple purchase required

- GitHub-hosted macOS CI can continue to compile, test, and inspect
  **unsigned validation builds** without the owner having a Mac.
- Do not require an Apple Developer Program membership or notarization
  ticket to declare **Windows/Linux** ready.
- Do not weaken macOS signing checks, distribute ad-hoc-signed packages
  as public notarized releases, or imply Apple Gatekeeper acceptance.
- Reconsider macOS distribution only if the owner later opts in to
  developer identity, notarization, and native GUI acceptance.

## Cross-platform release safety (Windows/Linux)

- Preserve MIT and third-party attribution, local-first defaults, and the
  separate GoreeCloud library path.
- Release-publishing scripts must reject unexpected package names,
  unchecked SHA-256, missing required signatures, upstream download hosts,
  and unconfigured credentials. Never mix different native signing
  platform families in one publisher invocation.
- Enable automatic updates only **after** the independently owned host,
  signing public key, validated release artifacts, and rollback/network
  recovery tests exist. `UPDATES_CONFIGURED` remains `false` meanwhile.
- Keep unsigned CI packages clearly labeled as validation artifacts until
  the separate distribution acceptance gate is satisfied.

The [release readiness checklist](RELEASE_READINESS.md) tracks outstanding
work, and [release operations](RELEASE_OPERATIONS.md) details signing and
native verification. Neither document makes an Apple account a requirement
for the initial Windows/Linux targets.
