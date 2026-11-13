#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ $(uname -s) == Linux ]] || { echo 'Run this preview inside Linux.' >&2; exit 1; }
cargo build --release --locked
export GOREECLOUD_RTE_HOME="${GOREECLOUD_RTE_HOME:-$(mktemp -d "${TMPDIR:-/tmp}/goreecloud-rich-text-editor-linux-preview.XXXXXX")}"
printf 'Preview library: %s\n' "$GOREECLOUD_RTE_HOME"
exec "${CARGO_TARGET_DIR:-target}/release/goreecloud_rich_text_editor"
