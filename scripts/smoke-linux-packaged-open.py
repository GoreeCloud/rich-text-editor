#!/usr/bin/env python3
"""Exercise command-line Markdown opening in a RELEASE-packaged Linux app.

Run against either a Linux x64 tarball or an AppImage. Uses isolated X11 and
a disposable external Unicode Markdown fixture: never the user's real notes.
No devtools features or scripted editor hooks.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import threading
import time


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    source_package = args.artifact.resolve()
    if sys.platform != "linux" or not source_package.is_file():
        parser.error("Requires an existing Linux AppImage or Linux tar.gz artifact")
    tarball = source_package.name.endswith("-linux-x86_64.tar.gz")
    appimage = source_package.name.endswith("-x86_64.AppImage")
    if not (tarball or appimage):
        parser.error("Unexpected Linux package format")
    root = Path(tempfile.mkdtemp(prefix="goreecloud-packaged-open-"))
    for name in ("home", "config", "cache", "data", "runtime", "library", "logs", "external 中文 notes"):
        (root / name).mkdir()
    (root / "runtime").chmod(0o700)
    source = root / "external 中文 notes" / "An external note 中文 spaces.md"
    other = root / "external 中文 notes" / "Not Markdown.txt"
    original = "# External Markdown 中文\n\nOpen this note without writing 🌿\n".encode("utf-8")
    source.write_bytes(original)
    other.write_text("Must not open as Markdown.\n", encoding="utf-8")
    timestamp = source.stat().st_mtime_ns
    env = dict(os.environ, HOME=str(root / "home"),
               XDG_CONFIG_HOME=str(root / "config"), XDG_CACHE_HOME=str(root / "cache"),
               XDG_DATA_HOME=str(root / "data"), XDG_RUNTIME_DIR=str(root / "runtime"),
               GOREECLOUD_RTE_HOME=str(root / "library"),
               GOREECLOUD_RTE_LOG_DIR=str(root / "logs"),
               LIBGL_ALWAYS_SOFTWARE="1")
    env.pop("WAYLAND_DISPLAY", None)
    icds = sorted(Path("/usr/share/vulkan/icd.d").glob("*lvp*.json"))
    if icds:
        env["VK_ICD_FILENAMES"] = str(icds[0])
    if appimage:
        env["APPIMAGE_EXTRACT_AND_RUN"] = "1"
        executable = source_package
    else:
        # The archive auditor rejects traversal, links, duplicate entries
        # and dangerous modes before this test streams a single known member.
        subprocess.run([sys.executable, "-B", str(Path(__file__).with_name("audit-release-artifacts.py")),
                        str(source_package)], check=True, stdout=subprocess.DEVNULL)
        prefix = source_package.name.removesuffix(".tar.gz")
        member = prefix + "/bin/goreecloud_rich_text_editor"
        executable = root / "goreecloud_rich_text_editor"
        with tarfile.open(source_package, "r:gz") as archive:
            item = archive.getmember(member)
            if not item.isfile() or item.size <= 0 or item.size > 250 * 1024 * 1024:
                raise RuntimeError("Portable Linux tarball has an invalid executable")
            with archive.extractfile(item) as infile, executable.open("wb") as outfile:
                if infile is None:
                    raise RuntimeError("Cannot read packaged executable")
                shutil.copyfileobj(infile, outfile)
        executable.chmod(0o700)

    success = False
    try:
        log = root / "logs" / "app.log"
        with log.open("wb") as capture:
            process = subprocess.Popen(
                ["xvfb-run", "-a", "-s", "-screen 0 1280x800x24",
                 str(executable), str(source), str(other)],
                env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, start_new_session=True)
            written = [0]

            def drain() -> None:
                while data := process.stdout.read(4096):
                    if written[0] < 1024 * 1024:
                        chunk = data[:1024 * 1024 - written[0]]
                        capture.write(chunk)
                        capture.flush()
                        written[0] += len(chunk)

            reader = threading.Thread(target=drain, daemon=True)
            reader.start()
            try:
                associated = False
                for _ in range(110):
                    index = root / "library" / "index.json"
                    if index.is_file():
                        try:
                            data = json.loads(index.read_text(encoding="utf-8"))
                            linked = [(name, row) for name, row in data.items()
                                      if isinstance(row, dict) and row.get("path") == str(source)]
                            if (len(linked) == 1 and linked[0][1].get("markdown") is True
                                    and not any(isinstance(row, dict) and row.get("path") == str(other)
                                                for row in data.values())):
                                associated = True
                                break
                        except (ValueError, OSError, AttributeError):
                            pass
                    if process.poll() is not None:
                        break
                    time.sleep(0.3)
                if not associated:
                    raise AssertionError("Packaged app failed to link original external Markdown path")
                if source.read_bytes() != original or source.stat().st_mtime_ns != timestamp:
                    raise AssertionError("External Markdown modified without explicit edits")
                if other.read_text(encoding="utf-8") != "Must not open as Markdown.\n":
                    raise AssertionError("Non-Markdown command-line file was modified")
                docdir = root / "library" / "docs"
                if docdir.exists() and any(docdir.iterdir()):
                    raise AssertionError("External Markdown was copied into the notes library")
            finally:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                reader.join(timeout=2)
        print("LINUX_PACKAGED_EXTERNAL_MARKDOWN_IN_PLACE_PASS",
              "tarball" if tarball else "AppImage", flush=True)
        success = True
        return 0
    finally:
        if success:
            shutil.rmtree(root)
        else:
            print(f"Packaged Linux command-line opening failed; isolated logs: {root}",
                  file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
