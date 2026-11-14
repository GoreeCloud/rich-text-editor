#!/usr/bin/env python3
"""Isolated Linux GUI acceptance for command-line external Markdown paths.

No use of the operator's actual HOME or notes directory. The experiment's
Unicode filename, index and source contents are all disposable.
Run with a release *validation* binary compiled with --features devtools.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import uuid
import threading
import time


def main() -> int:
    if sys.platform != "linux" or len(sys.argv) != 2 or not Path(sys.argv[1]).is_file():
        raise SystemExit("Usage: smoke-linux-external-file.py <devtools-enabled-Linux-binary>")
    app = Path(sys.argv[1]).resolve()
    root = Path(tempfile.mkdtemp(prefix="goreecloud-external-markdown-"))
    for name in ("home", "config", "cache", "data", "runtime", "library", "logs",
                 "external 中文 folder"):
        (root / name).mkdir()
    (root / "runtime").chmod(0o700)
    external = root / "external 中文 folder" / "Test Markdown 中文 spaces.md"
    ignored = root / "external 中文 folder" / "Not Markdown 中文.txt"
    source = "# External Markdown 中文\n\nDo not overwrite before editing 🌟\n".encode("utf-8")
    external.write_bytes(source)
    ignored.write_text("Do not open this plain-text fixture.\n", encoding="utf-8")
    original_timestamp = external.stat().st_mtime_ns

    env = dict(os.environ, HOME=str(root / "home"),
               XDG_CONFIG_HOME=str(root / "config"),
               XDG_CACHE_HOME=str(root / "cache"),
               XDG_DATA_HOME=str(root / "data"),
               XDG_RUNTIME_DIR=str(root / "runtime"),
               GOREECLOUD_RTE_HOME=str(root / "library"),
               GOREECLOUD_RTE_LOG_DIR=str(root / "logs"),
               LIBGL_ALWAYS_SOFTWARE="1", FDL_TRACE="1")
    env.pop("WAYLAND_DISPLAY", None)
    icds = sorted(Path("/usr/share/vulkan/icd.d").glob("*lvp*.json"))
    if icds:
        env["VK_ICD_FILENAMES"] = str(icds[0])

    def session(name: str, argv: list[str], script: str | None = None) -> None:
        steps = root / (name + ".steps")
        steps.write_text(script or "wait 2100\nclick 650 330\nwait 200\nquit\n", encoding="utf-8")
        log = root / "logs" / (name + ".log")
        appenv = dict(env, FDL_SCRIPT=str(steps))
        with log.open("wb") as capture:
            proc = subprocess.Popen(
                ["xvfb-run", "-a", "-s", "-screen 0 1280x800x24", str(app), *argv],
                env=appenv, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
            written = [0]

            def drain() -> None:
                while data := proc.stdout.read(4096):
                    if written[0] < 1024 * 1024:
                        view = data[:1024 * 1024 - written[0]]
                        capture.write(view)
                        capture.flush()
                        written[0] += len(view)

            reader = threading.Thread(target=drain, daemon=True)
            reader.start()
            try:
                rc = proc.wait(timeout=35)
                if rc != 0:
                    raise RuntimeError(f"{name}: GUI app exit code {rc}")
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                time.sleep(0.1)
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    pass
                reader.join(timeout=2)
        if "PANIC" in log.read_text(errors="replace"):
            raise RuntimeError(f"{name}: GUI application panic")
        print(f"PASS: {name} GUI session exited normally", flush=True)

    def entries():
        index = root / "library" / "index.json"
        if not index.is_file():
            raise AssertionError("Missing local-library index")
        records = json.loads(index.read_text(encoding="utf-8"))
        if not isinstance(records, dict):
            raise AssertionError("Library index is not an object")
        return records

    def check_unmodified():
        if external.read_bytes() != source:
            raise AssertionError("External Markdown bytes changed unexpectedly")
        if external.stat().st_mtime_ns != original_timestamp:
            raise AssertionError("External Markdown file was rewritten without edits")
        if ignored.read_text(encoding="utf-8") != "Do not open this plain-text fixture.\n":
            raise AssertionError("Ignored plain-text fixture was changed")
        if (root / "library" / "docs").exists() and any((root / "library" / "docs").iterdir()):
            raise AssertionError("External Markdown was unexpectedly copied into the notes library")

    passed = False
    try:
        session("open-external-unicode-path", [str(external), str(ignored)])
        check_unmodified()
        before = entries()
        linked = [(key, value) for key, value in before.items()
                  if isinstance(value, dict) and value.get("path") == str(external)]
        if len(linked) != 1 or linked[0][1].get("markdown") is not True:
            raise AssertionError(f"Expected exactly one in-place Markdown association: {linked}")
        if any(isinstance(value, dict) and value.get("path") == str(ignored)
               for value in before.values()):
            raise AssertionError("Non-Markdown command-line file was accepted")
        id_before = linked[0][0]

        session("reopen-library-without-file-argument", [])
        check_unmodified()
        after = entries()
        linked_after = [key for key, value in after.items()
                        if isinstance(value, dict) and value.get("path") == str(external)]
        if linked_after != [id_before]:
            raise AssertionError("External Markdown association did not survive restart unchanged")
        if len(after) != len(before):
            raise AssertionError("Reopening created a duplicate local-file record")
        print("LINUX_GUI_EXTERNAL_MARKDOWN_UNICODE_IN_PLACE_REOPEN_PASS", flush=True)

        # The actual GUI must save edits back to the *external* Markdown file.
        # Only an isolated source fixture is modified; the user's real files
        # are never opened. Unicode and spaces remain in the original path.
        edit_marker = "GoreeCloudExternalEdited" + uuid.uuid4().hex[:10] + "中文"
        session("edit-original-external-markdown", [str(external)],
                "wait 1700\nclick 675 520\nwait 250\nkey ctrl-end\n"
                "type " + edit_marker + "\nwait 2500\nquit\n")
        edited = external.read_bytes()
        if edit_marker.encode("utf-8") not in edited:
            raise AssertionError("The GUI edit was not saved to the original Markdown path")
        if edited == source:
            raise AssertionError("The external Markdown edit did not change the source")
        after_edit = entries()
        linked_after_edit = [key for key, value in after_edit.items()
                             if isinstance(value, dict) and value.get("path") == str(external)]
        if linked_after_edit != [id_before] or len(after_edit) != len(before):
            raise AssertionError("Editing in place duplicated or replaced the indexed local record")
        if (root / "library" / "docs").exists() and any((root / "library" / "docs").iterdir()):
            raise AssertionError("External file edit unexpectedly copied the source into library docs")

        session("reopen-edited-external-markdown", [])
        if external.read_bytes() != edited:
            raise AssertionError("Reopening changed saved external Markdown contents")
        if edit_marker.encode("utf-8") not in external.read_bytes():
            raise AssertionError("External edit did not persist across application restart")
        if ignored.read_text(encoding="utf-8") != "Do not open this plain-text fixture.\n":
            raise AssertionError("The unrelated non-Markdown source was modified")
        print("LINUX_GUI_EXTERNAL_MARKDOWN_EDIT_SAVE_REOPEN_PASS", flush=True)
        passed = True
        return 0
    finally:
        if passed:
            shutil.rmtree(root)
        else:
            print(f"External Markdown GUI test failed; disposable logs retained: {root}",
                  file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
