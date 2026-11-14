#!/usr/bin/env python3
"""Exercise actual desktop create, edit, save and reopen in disposable X11.

Requires the app binary built with --features devtools (never a release app).
The script never reads or writes the user's normal library, clipboard or home.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid

def main() -> int:
    if sys.platform != "linux":
        raise SystemExit("Linux only")
    if (len(sys.argv) not in (2, 3) or not Path(sys.argv[1]).is_file()
            or (len(sys.argv) == 3 and sys.argv[2] != "--markdown")):
        raise SystemExit("Usage: smoke-linux-editor.py <devtools-enabled-binary> [--markdown]")
    markdown = len(sys.argv) == 3
    app = Path(sys.argv[1]).resolve()
    token = uuid.uuid4().hex[:12]
    title = "GoreeCloudSavedTitle_" + token
    body = "GoreeCloudSavedBody_" + token + (" 中文" if markdown else "")
    work = Path(tempfile.mkdtemp(prefix="goreecloud-editor-interaction-"))
    for name in ("home", "config", "cache", "data", "runtime", "library", "logs"):
        (work / name).mkdir()
    (work / "runtime").chmod(0o700)
    # Force Markdown only inside this newly created disposable library.
    # Never change the production app's defaults or an existing user preference.
    if markdown:
        (work / "library" / "preferences.json").write_text(
            '{"new_default":"markdown","language":"en"}', encoding="utf-8")
    env = dict(os.environ, HOME=str(work / "home"),
               XDG_CONFIG_HOME=str(work / "config"),
               XDG_CACHE_HOME=str(work / "cache"),
               XDG_DATA_HOME=str(work / "data"),
               XDG_RUNTIME_DIR=str(work / "runtime"),
               GOREECLOUD_RTE_HOME=str(work / "library"),
               GOREECLOUD_RTE_LOG_DIR=str(work / "logs"),
               LIBGL_ALWAYS_SOFTWARE="1", FDL_TRACE="1")
    env.pop("WAYLAND_DISPLAY", None)
    icds = sorted(Path("/usr/share/vulkan/icd.d").glob("*lvp*.json"))
    if icds:
        env["VK_ICD_FILENAMES"] = str(icds[0])

    def session(name: str, script: str) -> None:
        source = work / (name + ".steps")
        source.write_text(script, encoding="utf-8")
        appenv = dict(env, FDL_SCRIPT=str(source))
        log = work / "logs" / (name + ".log")
        with log.open("wb") as capture:
            process = subprocess.Popen(
                ["xvfb-run", "-a", "-s", "-screen 0 1280x800x24", str(app)],
                env=appenv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, start_new_session=True)
            count = [0]
            def drain() -> None:
                while data := process.stdout.read(4096):
                    if count[0] < 1024 * 1024:
                        kept = data[:1024 * 1024 - count[0]]
                        capture.write(kept)
                        capture.flush()
                        count[0] += len(kept)
            reader = threading.Thread(target=drain, daemon=True)
            reader.start()
            try:
                result = process.wait(timeout=35)
                if result != 0:
                    raise RuntimeError(f"{name} exited with {result}")
            finally:
                # Scope kill to this process group only, and reap the wrapper.
                try: os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                time.sleep(0.1)
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                try: process.wait(timeout=3)
                except subprocess.TimeoutExpired: pass
                reader.join(timeout=2)
        content = log.read_text(errors="replace")
        if name == "create":
            if "key ctrl-n handled=true" not in content:
                raise AssertionError("Ctrl+N did not create a note via the focused editor")
            if "key enter handled=true" not in content:
                raise AssertionError("Enter did not transfer focus into the note body")
        print(f"PASS: {name} GUI session exited and logged {len(content)} characters", flush=True)

    passed = False
    try:
        session("create", "\n".join((
            "wait 1200", "click 650 320", "wait 300", "key ctrl-n",
            "wait 700", "type " + title, "key enter", "wait 250",
            "type " + body, "wait 2400", "quit", ""
        )))
        notes = [p for p in (work / "library").rglob("*")
                 if p.is_file() and p.suffix.lower() in (".xml", ".md")]
        if markdown:
            # Markdown serializes the body into the .md file. The note title
            # lives in index.json, and underscores are escaped by the writer.
            matches = [p for p in notes if p.suffix.lower() == ".md"
                       and body.replace("_", r"\_") in p.read_text(errors="replace")]
            index = work / "library" / "index.json"
            if not index.is_file() or title not in index.read_text(errors="replace"):
                raise AssertionError("Markdown note title missing from library index")
        else:
            matches = [p for p in notes if title in p.read_text(errors="replace")
                       and body in p.read_text(errors="replace")]
        if len(matches) != 1:
            raise AssertionError(f"Expected one persisted {'Markdown' if markdown else 'rich-text'} note; found {len(matches)}")
        doc = matches[0]
        digest = hashlib.sha256(doc.read_bytes()).hexdigest()
        session("reopen", "wait 1100\nquit\n")
        if not doc.is_file() or hashlib.sha256(doc.read_bytes()).hexdigest() != digest:
            raise AssertionError("Saved note changed or disappeared after reopening")
        if markdown and title not in index.read_text(errors="replace"):
            raise AssertionError("Markdown note title disappeared after reopening")
        print("LINUX_GUI_MARKDOWN_EDIT_SAVE_REOPEN_PASS" if markdown else
              "LINUX_GUI_EDIT_SAVE_REOPEN_PASS", flush=True)
        passed = True
        return 0
    finally:
        if passed:
            import shutil
            shutil.rmtree(work)
        else:
            print(f"GUI QA failed; isolated logs retained at {work}", file=sys.stderr)

if __name__ == "__main__":
    sys.exit(main())
