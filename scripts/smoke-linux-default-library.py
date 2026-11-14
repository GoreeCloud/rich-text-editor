#!/usr/bin/env python3
"""Verify first-run Linux AppImage isolation from a legacy Quiet.md library.

Uses a throwaway HOME/XDG tree, not the operator's real home or notes.
Production AppImage only (no devtools); never changes global MIME settings.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("appimage", type=Path)
    args = parser.parse_args()
    app = args.appimage.resolve()
    if sys.platform != "linux" or not app.is_file() or not app.name.endswith("-x86_64.AppImage"):
        parser.error("Expected an existing Linux x86_64 AppImage")
    root = Path(tempfile.mkdtemp(prefix="goreecloud-first-launch-isolation-"))
    home = root / "home"
    legacy = home / "Documents" / "Quiet.md"
    (legacy / "docs").mkdir(parents=True)
    private = legacy / "docs" / "old private notes.md"
    old_index = legacy / "index.json"
    private.write_bytes(b"Upstream private note: no access or migration allowed\n")
    old_index.write_bytes(b"UPSTREAM_INDEX_SENTINEL_DO_NOT_TOUCH\n")
    before = [(p, p.read_bytes(), p.stat().st_mtime_ns) for p in (private, old_index)]
    for name in ("config", "cache", "data", "runtime", "logs"):
        (root / name).mkdir()
    (root / "runtime").chmod(0o700)

    env = dict(os.environ,
               HOME=str(home), XDG_CONFIG_HOME=str(root / "config"),
               XDG_CACHE_HOME=str(root / "cache"), XDG_DATA_HOME=str(root / "data"),
               XDG_RUNTIME_DIR=str(root / "runtime"),
               GOREECLOUD_RTE_LOG_DIR=str(root / "logs"),
               LIBGL_ALWAYS_SOFTWARE="1", APPIMAGE_EXTRACT_AND_RUN="1")
    env.pop("GOREECLOUD_RTE_HOME", None)
    env.pop("WAYLAND_DISPLAY", None)
    icds = sorted(Path("/usr/share/vulkan/icd.d").glob("*lvp*.json"))
    if icds:
        env["VK_ICD_FILENAMES"] = str(icds[0])
    launched = False
    try:
        newlib = home / "Documents" / "GoreeCloud Rich Text Editor"
        log = root / "logs" / "app.out"
        with log.open("wb") as capture:
            proc = subprocess.Popen(
                ["xvfb-run", "-a", "-s", "-screen 0 1280x800x24", str(app)],
                env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, start_new_session=True)
            written = [0]

            def drain() -> None:
                while data := proc.stdout.read(4096):
                    if written[0] < 1024 * 1024:
                        kept = data[:1024 * 1024 - written[0]]
                        capture.write(kept)
                        capture.flush()
                        written[0] += len(kept)

            reader = threading.Thread(target=drain, daemon=True)
            reader.start()
            try:
                for _ in range(110):
                    index = newlib / "index.json"
                    docs = list((newlib / "docs").glob("*.xml"))
                    if index.is_file() and len(docs) >= 10:
                        launched = True
                        break
                    if proc.poll() is not None:
                        break
                    time.sleep(0.3)
                if not launched:
                    raise AssertionError("AppImage did not initialize independent GoreeCloud library")
                if newlib.resolve() == legacy.resolve():
                    raise AssertionError("GoreeCloud library incorrectly resolves to upstream library")
                for path, payload, mtime in before:
                    if path.read_bytes() != payload or path.stat().st_mtime_ns != mtime:
                        raise AssertionError(f"First-run app touched upstream library file {path.name}")
                if sorted(p.relative_to(legacy) for p in legacy.rglob("*") if p.is_file()) != [
                    Path("docs/old private notes.md"), Path("index.json")
                ]:
                    raise AssertionError("First run added/renamed files in legacy Quiet.md library")
                if len(list((newlib / "docs").glob("*.xml"))) < 10:
                    raise AssertionError("Missing independent GoreeCloud onboarding documents")
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                reader.join(timeout=2)
        print("LINUX_APPIMAGE_DEFAULT_LIBRARY_SEPARATE_FROM_QUIET_MD_PASS", flush=True)
        shutil.rmtree(root)
        return 0
    finally:
        if root.exists():
            print(f"First-launch isolation QA failed; disposable logs retained at {root}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
