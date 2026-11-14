#!/usr/bin/env bash
# Ubuntu 22.04 does not ship minisign as an apt package.
# Install the official, static minisign 0.12 Linux x86_64 release for CI only.
# Its upstream archive hash is pinned; never extract arbitrary tarball members.
set -euo pipefail
[[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]] ||
  { echo "Official minisign CI bootstrap is Linux x86_64-only" >&2; exit 2; }
[[ -d "$RUNNER_TEMP" && -n "$GITHUB_PATH" ]] ||
  { echo "RUNNER_TEMP and GITHUB_PATH are required in GitHub Actions" >&2; exit 2; }
tool_dir=$(mktemp -d "$RUNNER_TEMP/goreecloud-minisign.XXXXXX")
archive="$tool_dir/minisign-0.12-linux.tar.gz"
curl -q --fail --silent --show-error --location --retry 3 \
  --proto '=https' --proto-redir '=https' --max-redirs 5 \
  --connect-timeout 15 --max-time 120 \
  https://github.com/jedisct1/minisign/releases/download/0.12/minisign-0.12-linux.tar.gz \
  -o "$archive"
echo "9a599b48ba6eb7b1e80f12f36b94ceca7c00b7a5173c95c3efc88d9822957e73  $archive" |
  sha256sum -c -
mkdir -p "$tool_dir/bin"
tar -xOzf "$archive" minisign-linux/x86_64/minisign > "$tool_dir/bin/minisign"
chmod 755 "$tool_dir/bin/minisign"
"$tool_dir/bin/minisign" -v | grep -Fx "minisign 0.12"
printf '%s\n' "$tool_dir/bin" >> "$GITHUB_PATH"
echo "Pinned official minisign verifier installed in disposable GitHub Actions directory."
