# Official GoreeCloud Notes branding — pinned source and consumers

## Verified authority and provenance

- Central official graphics source: https://github.com/GoreeCloud/brand-assets/tree/14fa8e5ac4fd372fee27d062980fc578a7919f61/products/notes
- Central merge: brand-assets PR #30, commit 14fa8e5ac4fd372fee27d062980fc578a7919f61.
- Original vector master: products/notes/app-icon.svg, Git blob f9be4e8246aa3d702a81f65649bdb4434b30ea89 (not a Quiet.md mark).
- Linux/macOS 512px image: products/notes/raster/icon-512.png, copied unchanged into assets/branding/app-icon.png. SHA-256 a7d94be348d09cf1e78896cbe11f98ee4234a106fa268a6ea4b1b47d7762e60e.
- Windows ICO: products/notes/raster/favicon.ico, copied unchanged into assets/branding/app-icon.ico. SHA-256 9c6ec314131ac42163c7edfbcae6a7ecd15a277f44badb79a95aa1747fc4cca1, with 16/32/48/256px layers.

## Compatibility and reproducibility

The existing application executable goreecloud_rich_text_editor and desktop icon identifier com.goreecloud.richtexteditor are preserved so existing Linux/Windows installs can upgrade in place. Linux packaging now copies the exact already-512px centrally published PNG instead of resampling with ImageMagick. The Windows resource ProductName and FileDescription are GoreeCloud Notes, but the original executable filename stays unchanged.

The offline scripts/check-official-notes-icon.py checks exact hashes, dimensions and metadata; it is invoked by scripts/check.py in cross-platform CI. scripts/test_debian_package.py validates the installed Linux PNG matches the official binary exactly. Upstream attributions and the app's existing notes path remain intact.

## Outstanding acceptance

CI verification and provenance are NOT proof of human icon approval, physical desktop icon-cache acceptance, every 16px/32px launcher rendering, true Cloud Lens frosted glass, full GoreeCloud UI compliance, a migrated approved Linux Qt Quick/Flutter/Slint primary UI, a signed Stable release, or an installed device upgrade. The central artwork is first-party original and reviewed as a development source; consumer release remains gated.
