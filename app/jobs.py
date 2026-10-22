"""One background job at a time (create the venv, install packages, run a cleaning script) with a log the window can poll."""
import os
import subprocess
import threading
import time


class Jobs:
    def __init__(self):
        self.lock = threading.Lock()
        self.name = None
        self.state = "idle"            # idle | running | done | failed
        self.lines = []
        self.started = None
        self.message = ""

    def snapshot(self, since=0):
        with self.lock:
            return {"name": self.name, "state": self.state, "message": self.message, "next": len(self.lines),
                    "log": self.lines[since:], "seconds": int(time.time() - self.started) if self.started else 0}

    def log(self, text):
        with self.lock:
            self.lines.append(str(text))

    def start(self, name, fn):
        """run fn(log) in a thread; fn returns (ok, message). Returns False if a job is already running."""
        with self.lock:
            if self.state == "running":
                return False
            self.name, self.state, self.lines, self.message, self.started = name, "running", [], "", time.time()

        def work():
            try:
                ok, msg = fn(self.log)
            except Exception as e:                       # a bug must reach the window, not kill the thread silently
                ok, msg = False, f"internal error: {e}"
            with self.lock:
                self.state = "done" if ok else "failed"
                self.message = msg or ""
        threading.Thread(target=work, daemon=True).start()
        return True


def stream(cmd, log, env=None, echo=True, cwd=None):
    """run a command, send each output line to log (first the command itself when echo); returns the exit code"""
    if echo:
        log("$ " + " ".join(str(c) for c in cmd))
    e = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", PYTHONUNBUFFERED="1")
    if env:
        e.update(env)
    try:
        p = subprocess.Popen([str(c) for c in cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=e, cwd=str(cwd) if cwd else None,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError as err:
        log(f"cannot start: {err}")
        return 1
    for line in p.stdout:
        log(line.rstrip("\r\n"))
    return p.wait()
