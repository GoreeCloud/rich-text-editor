#!/usr/bin/env bash
# Exercise the actual Linux AppImage in an isolated X11 session and notes library.
# Needs xvfb-run, xwininfo, a software Vulkan ICD and GNU timeout.
set -euo pipefail
[[ "$(uname -s)" == "Linux" ]] || { echo "Linux only" >&2; exit 1; }
[[ "$#" -eq 1 && -f "$1" ]] || { echo "Usage: $0 <release.AppImage>" >&2; exit 2; }
for tool in xvfb-run xwininfo timeout; do
  command -v "$tool" >/dev/null || { echo "Missing $tool" >&2; exit 2; }
done
app=$(realpath "$1")
sandbox=$(mktemp -d "${TMPDIR:-/tmp}/goreecloud-ui-smoke.XXXXXX")
trap 'rm -rf "$sandbox"' EXIT
mkdir -p "$sandbox"/{home,config,cache,data,runtime,library,logs}
chmod 700 "$sandbox/runtime"
export APPIMAGE_EXTRACT_AND_RUN=1 LIBGL_ALWAYS_SOFTWARE=1
export HOME="$sandbox/home" XDG_CONFIG_HOME="$sandbox/config"
export XDG_CACHE_HOME="$sandbox/cache" XDG_DATA_HOME="$sandbox/data"
export XDG_RUNTIME_DIR="$sandbox/runtime" GOREECLOUD_RTE_HOME="$sandbox/library"
export GOREECLOUD_RTE_LOG_DIR="$sandbox/logs"
unset WAYLAND_DISPLAY
icd=$(find /usr/share/vulkan/icd.d -name '*lvp*.json' -print -quit 2>/dev/null || :)
if [[ -n "$icd" ]]; then export VK_ICD_FILENAMES="$icd"; fi
export GOREECLOUD_SMOKE_APP="$app" GOREECLOUD_SMOKE_ROOT="$sandbox"

# The AppImage --extract-and-run helper can outlive its launcher after Xvfb
# exits. Terminate only binaries inheriting THIS unique sandbox marker,
# including reparented helper descendants, before removing their log files.
cleanup_smoke() {
  local p pid exe
  local -a owned=()
  for p in /proc/[0-9]*/environ; do
    pid=${p#/proc/}
    pid=${pid%/environ}
    # Avoid opening other processes' private environ files.
    [[ $(cat "/proc/$pid/comm" 2>/dev/null || :) == goreecloud_rich* ]] || continue
    if tr '\0' '\n' < "$p" 2>/dev/null | grep -Fxq "GOREECLOUD_SMOKE_ROOT=$sandbox"; then
      exe=$(readlink "/proc/$pid/exe" 2>/dev/null || :)
      if [[ "$exe" == */goreecloud_rich_text_editor* ]]; then
        owned+=("$pid")
      fi
    fi
  done
  for pid in "${owned[@]}"; do kill -TERM "$pid" 2>/dev/null || :; done
  if (("${#owned[@]}" > 0)); then sleep .3; fi
  for pid in "${owned[@]}"; do
    exe=$(readlink "/proc/$pid/exe" 2>/dev/null || :)
    if [[ "$exe" == */goreecloud_rich_text_editor* ]]; then
      kill -KILL "$pid" 2>/dev/null || :
    fi
  done
  rm -rf -- "$sandbox"
}
trap cleanup_smoke EXIT

set +e
timeout --signal=TERM --kill-after=3s 35s xvfb-run -a -s "-screen 0 1280x800x24" bash -c '
  set -euo pipefail
  # Bound the diagnostic log without imposing a file-size limit on the
  # application itself (fonts/GPU caches may legitimately exceed 8 MiB).
  "$GOREECLOUD_SMOKE_APP" > >(head -c 1048576 > "$GOREECLOUD_SMOKE_ROOT/logs/launch.out") 2>&1 &
  child=$!
  # The extracted process may outlive this wrapper; the outer trap also
  # finds that process by its unique GOREECLOUD_SMOKE_ROOT marker.
  trap "kill -TERM $child 2>/dev/null || :; wait $child 2>/dev/null || :" EXIT
  found=0
  for i in $(seq 1 80); do
    if xwininfo -root -tree 2>/dev/null | grep -Fq "\"GoreeCloud Notes\""; then found=1; break; fi
    if ! kill -0 "$child" 2>/dev/null; then break; fi
    sleep .2
  done
  if [[ "$found" != 1 ]] || ! kill -0 "$child" 2>/dev/null; then
    echo "GoreeCloud GUI did not open under isolated X11" >&2
    cat "$GOREECLOUD_SMOKE_ROOT/logs/launch.out" >&2
    exit 1
  fi
  count=$(find "$GOREECLOUD_RTE_HOME/docs" -maxdepth 1 -type f 2>/dev/null | wc -l)
  if [[ "$count" -lt 10 ]]; then
    echo "Expected bundled first-launch guides, got $count docs" >&2
    exit 1
  fi
  echo "Isolated GoreeCloud window opened; $count first-launch guides created."
'
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  echo "Startup smoke test failed (exit $rc)" >&2
  tail -60 "$sandbox/logs/launch.out" >&2 || :
  exit "$rc"
fi
if grep -Eq 'PANIC|panicked at' "$sandbox/logs/launch.out"; then
  echo "App logged a startup panic" >&2
  tail -60 "$sandbox/logs/launch.out" >&2
  exit 1
fi
echo "Linux AppImage isolated GUI smoke test passed."
