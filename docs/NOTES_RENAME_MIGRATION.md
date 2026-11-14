# GoreeCloud Notes — product rename and safe upgrade protocol

**Canonical product:** GoreeCloud Notes. **Canonical source:** https://github.com/GoreeCloud/notes.

## What changed

- Public product name, desktop menu title, About text, and source/preview links now use **GoreeCloud Notes**.
- The inherited Quiet.md source history, MIT license and third-party notices remain intact.
- Linux x64 remains the first development target. This is not a signed Stable release or a completed native Linux UI migration.

## Existing installations and data

Do **not** automatically move, rename, import or delete a user's document library as part of the UI rename. Existing installs use `~/Documents/GoreeCloud Rich Text Editor` by default (or the platform's Documents location); `GOREECLOUD_RTE_HOME` overrides it. The executable `goreecloud_rich_text_editor`, application ID `com.goreecloud.richtexteditor`, legacy Linux desktop filename, and Windows installer AppId remain unchanged in this compatibility phase.

An existing manually installed Debian development package named `goreecloud-rich-text-editor` is **not** automatically upgraded or replaced by this source-only change. A package-name transition to `goreecloud-notes`, a new library path, app/desktop identifiers, or a revised icon requires separate migration, conflict/replaces handling, rollback, and physical-Linux acceptance. Preserve copies of private notes and do not put them in CI.

## Linux UI and visual quality gate

The currently shipped GPUI UI is **not** compliant with the mandatory Linux primary UI standard; see [migration issue #12](https://github.com/GoreeCloud/notes/issues/12). Implement a reviewed Qt Quick 6.12.0, Flutter Linux Desktop or Slint frontend before claiming compliance. Reuse existing Rust document engine and data formats where suitable; check licenses and sandbox boundaries. The canonical [GoreeCloud UI design language](https://github.com/GoreeCloud/gc-ui/blob/main/docs/DESIGN_LANGUAGE.md) requires premium identity and purposeful frosted **Cloud Lens** treatment for elevated navigation, menus and overlays, with contrast, reduced-transparency and opaque fallback. Do not make document reading canvases translucent by default. The screenshot feedback reports a weak launcher icon and missing frosted glass; native compositor behavior, icon quality and accessibility remain unverified.

## Acceptance gates

1. Run identity/attribution guard and all existing Rust/CI checks after any visible rebranding.
2. Compare Linux desktop entry, window title, launcher shortcut, About/settings, README, source-preview links and installer names with the canonical product name.
3. Test first launch with isolated libraries and confirm old GoreeCloud and upstream Quiet.md notes are not modified or migrated.
4. Test manual upgrade/rollback, legacy file associations, note save/reopen, markdown in place, Unicode names, and packaging on a physical Linux desktop before signed release.
5. Verify native design behavior in normal/contrast/reduced-transparency modes and screen-reader/keyboard interaction on a supported framework.
6. Keep updates disabled until an owner-controlled, signed release and rollback channel are accepted.

**Scope:** This document describes a staged compatibility-first rename. It does not claim a deployed package, completed native port, signed build, or production release.
