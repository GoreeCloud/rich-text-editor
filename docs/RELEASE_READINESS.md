# GoreeCloud Rich Text Editor — engineering and release readiness

This repository is an independently branded source import of Quiet.md. The upstream revision and MIT attribution are recorded in [UPSTREAM.md](../UPSTREAM.md) and [LICENSE](../LICENSE).

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

## Tasks before distributing a signed release

- [ ] Confirm native UI behavior on macOS, Windows and Linux (including Markdown file association, printing, font rendering and install/uninstall).
- [ ] Run `scripts/check.sh` and verify the current GitHub Actions CI jobs are green on the release commit.
- [ ] Configure independent macOS notarization, Windows code-signing and a release/update signing key.
- [ ] Configure a GoreeCloud-owned download host and R2 bucket, update `src/update.rs` to trust only that host and key, and deliberately enable its updater.
- [ ] Test installer upgrades, fallback/recovery, and signed update verification on disposable test systems.
- [ ] Publish signed packages and SHA-256 checksums; keep unsigned CI artifacts labeled for testing only.
- [ ] Validate app name, documentation, translated onboarding guides, screenshots, accessibility and any remaining upstream terminology.

The app's core note engine supports both Markdown files and Feishu/Lark DocxXML documents. This project should not claim that every note is stored as Markdown.

## Import hardening checks

The static public landing page intentionally contains no downloadable package links until GoreeCloud releases exist. The updater uses the reserved `https://updates.invalid/` placeholder and an unconfigured public-key file; both must be replaced with GoreeCloud-owned infrastructure before explicitly enabling updates. Reusing upstream signing keys or download domains is prohibited.

Linux AppImage packaging smoke-tests the extracted `AppRun` launcher with an isolated stub executable and checks that the correct binary is selected with forwarded arguments. This avoids running the GUI or touching notes during CI.

The first-launch guide includes an original GoreeCloud-branded one-page PDF quick reference. The guide's source and bundled assets must remain byte-identical; `rebrand_guard.py` enforces this.

The Windows installer, macOS app/DMG, Linux tarball, and AppImage must all ship both `LICENSE` and `THIRD_PARTY.md`; the Linux tarball packaging step verifies its output archive contents.
