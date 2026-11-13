#!/bin/bash
# Upload release packages to the separately configured GoreeCloud R2 bucket: an immutable copy under v<version>/ and the
# fixed latest/ link the site and README point at. Pass the macOS ZIP, the Windows installer, or both:
#   scripts/publish-downloads.sh dist-release.XXXX/goreecloud-rich-text-editor-0.1.2-macos-arm64.zip dist/windows/signed/goreecloud-rich-text-editor-0.1.2-windows-x64-setup.exe
# Each package is signed with minisign (MINISIGN_KEY, default ~/.minisign/goreecloud-rich-text-editor.key) and checked against
# packaging/update-key.pub; latest/update-<platform>.json, written last, is what the app's updater reads.
# The key's password comes from the login keychain when stored there once, else minisign asks:
#   security add-generic-password -U -s goreecloud-rich-text-editor-minisign -a "$USER" -w
# DRY_RUN=1 prints the uploads without signing or sending them. WRANGLER overrides the wrangler command.
set -euo pipefail
cd "$(dirname "$0")/.."
[ "${GOREECLOUD_RELEASE_ENABLED:-}" = "yes" ] || { echo "Release publishing disabled until configured." >&2; exit 2; }
[ $# -ge 1 ] || { sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
bucket=${GOREECLOUD_DOWNLOAD_BUCKET:?Set GoreeCloud download bucket}
host=${GOREECLOUD_DOWNLOAD_HOST:?Set GoreeCloud download host}
python3 - "$host" "$bucket" <<'PYTHON'
import re, sys
from urllib.parse import urlsplit
host, bucket = sys.argv[1:]
u = urlsplit(host)
if (u.scheme != "https" or not u.hostname or u.username or u.password or u.query or u.fragment
        or u.path not in ("", "/") or not u.netloc or "quiet.md" in u.hostname
        or u.hostname.endswith((".invalid", ".localhost", ".local", ".test"))
        or u.hostname in ("localhost", "127.0.0.1")):
    raise SystemExit("GOREECLOUD_DOWNLOAD_HOST must be a GoreeCloud-owned HTTPS origin")
if not re.fullmatch(r"[A-Za-z0-9._-]{3,128}", bucket):
    raise SystemExit("Invalid GOREECLOUD_DOWNLOAD_BUCKET")
print("Release host and bucket shape validated; verify domain ownership before publishing.")
PYTHON
wrangler=${WRANGLER:-npx -y wrangler@4}
key=${MINISIGN_KEY:-$HOME/.minisign/goreecloud-rich-text-editor.key}
pub=packaging/update-key.pub
expected=$(sed -n 's/^version = "\(.*\)"/\1/p' Cargo.toml | head -1)
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT

put() {  # key file content-type cache-control [content-disposition]
  local cmd=($wrangler r2 object put "$bucket/$1" --file "$2" --remote --content-type "$3" --cache-control "$4")
  [ -n "${5:-}" ] && cmd+=(--content-disposition "$5")
  if [ -n "${DRY_RUN:-}" ]; then printf '%q ' "${cmd[@]}"; echo; else "${cmd[@]}" >/dev/null; fi
}

if [ -z "${DRY_RUN:-}" ]; then
  command -v minisign >/dev/null || { echo "minisign is not installed (brew install minisign)" >&2; exit 1; }
  grep -q '^RW' "$pub" || { echo "$pub has no public key yet; see the comment in it" >&2; exit 1; }
  [ -f "$key" ] || { echo "Missing signing key $key (set MINISIGN_KEY)" >&2; exit 1; }
  password=$(security find-generic-password -s goreecloud-rich-text-editor-minisign -a "$USER" -w 2>/dev/null || true)
fi

for file in "$@"; do
  name=$(basename "$file")
  case "$name" in
    goreecloud-rich-text-editor-*-macos-arm64.zip) platform=macos-arm64; latest=goreecloud-rich-text-editor-macos-arm64.zip; type=application/zip ;;
    goreecloud-rich-text-editor-*-macos-x86_64.zip) platform=macos-x86_64; latest=goreecloud-rich-text-editor-macos-x86_64.zip; type=application/zip ;;
    goreecloud-rich-text-editor-*-windows-x64-setup.exe) platform=windows-x64; latest=goreecloud-rich-text-editor-windows-x64-setup.exe; type=application/vnd.microsoft.portable-executable ;;
    goreecloud-rich-text-editor-*-x86_64.AppImage) platform=linux-x86_64; latest=goreecloud-rich-text-editor-x86_64.AppImage; type=application/octet-stream ;;
    *) echo "Unrecognised package name: $name" >&2; exit 1 ;;
  esac
  version=${name#goreecloud-rich-text-editor-}; version=${version%%-*}
  [ "$version" = "$expected" ] || { echo "$name is $version but Cargo.toml says $expected" >&2; exit 1; }
  [ -f "$file" ] || { echo "Missing $file" >&2; exit 1; }
  # Reject a tampered or incomplete package before using signing keys or uploading.
  python3 -B scripts/audit-release-artifacts.py "$file" || { echo "Package audit failed: $file" >&2; exit 1; }
  # The trusted comment is the file name: the app accepts the signature only for the version the manifest names.
  sig="$work/$name.minisig"
  if [ -z "${DRY_RUN:-}" ]; then
    if [ -n "$password" ]; then printf '%s\n' "$password" | minisign -S -s "$key" -m "$file" -x "$sig" -t "$name" >/dev/null
    else minisign -S -s "$key" -m "$file" -x "$sig" -t "$name"; fi
    minisign -V -q -p "$pub" -m "$file" -x "$sig" || { echo "$name: signature does not match $pub" >&2; exit 1; }
  else
    echo "minisign -S -s $key -m $file -x $sig -t $name"; : > "$sig"
  fi
  put "v$version/$name" "$file" "$type" "public, max-age=31536000, immutable"
  [ -f "$file.sha256" ] && put "v$version/$name.sha256" "$file.sha256" "text/plain; charset=utf-8" "public, max-age=31536000, immutable"
  put "v$version/$name.minisig" "$sig" "text/plain; charset=utf-8" "public, max-age=31536000, immutable"
  # latest/ keeps a stable URL; the download still saves under the versioned file name.
  put "latest/$latest" "$file" "$type" "public, max-age=300" "attachment; filename=\"$name\""
  size=$(python3 - "$file" <<'PYTHON'
import os, sys
print(os.path.getsize(sys.argv[1]))
PYTHON
)
  manifest="$work/update-$platform.json"
  python3 - "$version" "$host/v$version/$name" "$size" "$sig" > "$manifest" <<'PYTHON'
import json, sys
version, url, size, sig = sys.argv[1:]
print(json.dumps({"version": version, "url": url, "size": int(size), "signature": open(sig).read()}, indent=2))
PYTHON
  [ -n "${DRY_RUN:-}" ] && { put "latest/update-$platform.json" "$manifest" "application/json" "public, max-age=300"; continue; }
  headers=$(curl -sfI "$host/latest/$latest?check=$RANDOM" | tr -d '\r')
  grep -qi "^content-length: $size$" <<<"$headers" && grep -qi "filename=\"$name\"" <<<"$headers" \
    || { echo "latest/$latest did not update as expected" >&2; exit 1; }
  curl -sfI "$host/v$version/$name" | tr -d '\r' | grep -qi "^content-length: $size$" \
    || { echo "v$version/$name is not served" >&2; exit 1; }
  # Last: running copies see the new version only once the package it points at is served.
  put "latest/update-$platform.json" "$manifest" "application/json" "public, max-age=300"
  echo "$host/latest/$latest -> $name ($size bytes); $host/latest/update-$platform.json -> $version"
done
