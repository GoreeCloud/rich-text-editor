# GoreeCloud Notes

**A local-first desktop notes app, Markdown editor, Markdown viewer, and rich-text text editor.**

GoreeCloud Notes is a rebranded import of the open-source [Quiet.md](https://github.com/s1dashu/quiet-md) project, built with Rust and GPUI. **Linux x64 is the first release target.** Windows x64 remains CI-tested, with public distribution deferred until native GUI acceptance is possible. macOS remains a validation-only target for now. Windows or Apple hardware/signing credentials do not block Linux.

> **Status: source import / beta.** This repository does not yet publish GoreeCloud installers or automatic updates. Do not use the upstream Quiet.md release packages as GoreeCloud builds.

**Release order:** Linux AppImage/tarball, native Linux GUI acceptance and signed Linux packages first. Windows CI maintenance second; public Windows and macOS releases deferred. See the [Linux-first release plan](docs/LINUX_FIRST_RELEASE_PLAN.md).

## Features

- **Local-first:** notes are stored in a folder on your own computer; no account or cloud service is required.
- **Markdown editing and viewing:** open and edit Markdown files in place, import Markdown folders, and export Markdown or PDF.
- **Rich-text notes:** headings, checklists, code blocks, math, tables, columns, callouts, images, covers, and attachments.
- **Organize your notes:** nested folders, full-text search, favorites, pinning, and trash.
- **Native desktop app:** built in Rust and GPUI without Electron.

## Note formats and privacy

The application supports Markdown documents and Feishu/Lark DocxXML documents. **Not all notes are stored as Markdown by default**; the underlying library can store DocxXML, while Markdown files can be edited directly. Files stay local by default. **Web images are not fetched automatically in new libraries**; you can enable remote images in Settings or load an individual image explicitly. Remote image transfers are limited to HTTP(S) and 20 MiB.

The existing application's default library location is retained for upgrade compatibility:
- `~/Documents/GoreeCloud Rich Text Editor` (where the Documents directory is available).

`GOREECLOUD_RTE_HOME` continues to select an alternative library. Do not rename, move, or delete existing notes automatically: **the GoreeCloud Notes display-name change does not migrate user data**, and the legacy on-disk directory and executable identifiers intentionally remain compatible. See [rename migration](docs/NOTES_RENAME_MIGRATION.md). This separate location avoids reusing or modifying an existing Quiet.md library.

## Build from source

A current Rust toolchain and the platform-specific dependencies for [GPUI](https://www.gpui.rs/) are required. See `CONTRIBUTING.md` and `docs/ARCHITECTURE.md`.

```bash
cargo run --release
```

You can also use `scripts/check.sh` for the upstream test and lint workflow. Platform packaging lives in `scripts/` and `packaging/`.

See [Release readiness](docs/RELEASE_READINESS.md) and the [release operator runbook](docs/RELEASE_OPERATIONS.md) for signing, notarization, and distribution requirements.

**Updates:** upstream auto-updates are disabled and a non-resolving `updates.invalid` placeholder is configured in this import. GoreeCloud-specific distribution, signing, update metadata, and install testing must be configured before releases are enabled.

## Origin and licensing

- Source: [s1dashu/quiet-md](https://github.com/s1dashu/quiet-md), `main`
- Imported upstream commit: `fa62760d1ca1753608c5bda4e89df0a435476594` (2026-11-13)
- Import type: **Rebranded Import**
- Product name: **GoreeCloud Notes**

The upstream project's MIT copyright and permission notice are preserved in [LICENSE](LICENSE). Third-party notices are preserved in [THIRD_PARTY.md](THIRD_PARTY.md). The original separately licensed Nucleo app-shell icons were replaced with ISC-licensed Lucide icons, and the app icon was replaced with an original GoreeCloud monogram. Read [UPSTREAM.md](UPSTREAM.md) for details.

This project is an independent rebranded derivative, not an official Quiet.md release or affiliation.
