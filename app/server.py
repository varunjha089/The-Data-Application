"""The window of The Data Application: a small web server on this computer only (127.0.0.1, random port, secret key) that shows the
interface in its own app window. Standard library only. The interface itself is in app/web/ (index.html, style.css, app.js).

Nothing here does the real work: it calls the same modules the terminal commands use (envsetup, dataset, runner) and runs the scripts of steps/.
"""
import csv
import json
import os
import re
import secrets
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import __version__, ai, config, dataset, envsetup, look, native, pipeline, project as projects, report, sample, sheets as sheetlist, update, window, years
from .jobs import Jobs, stream
from .paths import REQUIREMENTS, ROOT, STEPS, default_location

WEB = Path(__file__).resolve().parent / "web"
MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".csv": "text/csv; charset=utf-8",
        ".txt": "text/plain; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".pdf": "application/pdf", ".tif": "image/tiff", ".json": "application/json"}
PREVIEW_COLUMNS = ["Title", "Year", "Source title", "Cited by", "Document Type", "Countries", "Collaboration Type"]
IDLE_SECONDS = 25            # the window pings every few seconds; when it stops (window closed) the application ends
FIRST_PING_SECONDS = 90      # ... and if the window never opened


class App:
    def __init__(self, port=0):
        self.token = secrets.token_urlsafe(24)
        self.jobs = Jobs()
        self.project = None                 # the project that is open (None: the opening screen is shown)
        self.started = time.time()
        self.last_ping = None
        self.httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(self))
        self.port = self.httpd.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}/?key={self.token}"
        self.updated = False                # a new version was installed: the window may restart the application
        threading.Thread(target=update.check, daemon=True).start()       # at most once a day; never blocks the window

    # ---------------------------------------------------------------- state shown in the window
    def projects_list(self):
        items = projects.list_projects()
        for it in items:                                    # the python of each project, so that another project can use the same venv
            py = projects.Project(it["path"]).python() if it["exists"] else None
            it["python_abs"] = str(py) if py is not None and py.exists() else None
        app = config.app_load()
        return {"projects": items, "last": app.get("last_project"), "current": str(self.project.dir) if self.project else None,
                "location": app.get("last_location") or str(default_location())}

    def status(self):
        out = {"ui": config.app_load().get("ui", {}), "folder": str(ROOT), "version": __version__, "project": None}
        pr = self.project
        if pr is None:
            return out
        cfg = pr.load()
        env = {"configured": False, "python": None, "ok": False, "message": "not set up yet", "missing": [], "can_clean": False, "can_plot": False, "venv_here": envsetup.venv_python(pr.venv_dir) is not None}
        if cfg.get("python"):
            py = pr.python()
            ok, msg = envsetup.check(py)
            missing = envsetup.missing_packages(py) if py is not None and py.exists() else list(envsetup.REQUIRED.values())
            env.update(configured=True, python=cfg["python"], ok=ok, message=msg, missing=missing, can_clean="pandas" not in missing, can_plot="matplotlib" not in missing and "pandas" not in missing)
        data = {"chosen": False}
        info = cfg.get("main_data")
        if info:
            data = {"chosen": True, "exists": pr.main_data() is not None, "file": info["file"], "records": info["records"], "copied": info["copied"],
                    "original": info.get("original_path", "")}
        wanted, fallback = pipeline.clean_exclude(pr), pipeline.clean_country_fallback(pr)
        made = cfg.get("clean_data") or {}
        clean = {"exists": pr.clean_file.exists(), "current": bool(made) and pr.clean_file.exists() and made.get("exclude", "") == wanted and made.get("country_fallback", False) == fallback,
                 "made": made.get("made"), "log": pr.clean_log.exists(), "exclude_only_queries": wanted, "country_fallback": fallback}
        out["project"] = {"path": str(pr.dir), "name": pr.name, "dir": str(pr.dir), "created": cfg.get("created", ""), "env": env, "data": data, "clean": clean,
                          "years": years.info(pr), "look": look.get(pr), "look_choices": {"dpi": list(look.DPI), "palettes": look.PALETTES, "limits": look.LIMITS, "table_rows": list(look.TABLE_ROWS)},
                          "steps": sorted(p.name for p in STEPS.glob("*.py"))}
        return out

    def busy(self):
        return self.jobs.snapshot()["state"] == "running"

    # ---------------------------------------------------------------- jobs (always for the project that was open when they started)
    def job_setup(self, pr, path_text=None, install=True):
        """create .venv in the project (path_text None) or use an existing venv; install missing packages; remember it in project.json"""
        def run(log):
            if path_text is None:
                py = envsetup.venv_python(pr.venv_dir)
                if py is None:
                    log("Creating the virtual environment in the project's .venv ...")
                    if stream([envsetup.base_python(), "-m", "venv", pr.venv_dir], log) != 0:
                        return False, "Could not create the venv. On Debian/Ubuntu install 'python3-venv' first, or use an existing venv."
                    py = envsetup.venv_python(pr.venv_dir)
                else:
                    log("A venv already exists in the project's .venv; using it.")
            else:
                py = envsetup.resolve(path_text)
                if py is None:
                    return False, "No python found there. The folder should contain pyvenv.cfg and a bin (Scripts on Windows) folder."
            ok, msg = envsetup.check(py)
            if not ok and msg.startswith("missing packages") and install:
                log("Installing the packages from requirements.txt (this can take a minute) ...")
                if stream([py, "-m", "pip", "install", "--disable-pip-version-check", "-r", REQUIREMENTS], log) != 0:
                    return False, ("The installation failed. Is there an internet connection? If your Python is very new, a package may not exist "
                                   "for it yet: use Python 3.11 to 3.13.")
                ok, msg = envsetup.check(py)
            if not ok:
                return False, msg
            pr.set_python(py)
            return True, "Environment ready: " + msg
        return self.jobs.start("setup", run)

    def job_clean(self, pr):
        return self.jobs.start("clean", lambda log: pipeline.clean_data(pr, log))

    def job_install(self, pr):
        """install the packages of requirements.txt into the project's python (a project made before a new package was needed)"""
        def run(log):
            py = pr.python()
            if py is None or not py.exists():
                return False, "The Python environment is not set up yet."
            log("Installing the packages from requirements.txt (this can take a minute) ...")
            if stream([py, "-m", "pip", "install", "--disable-pip-version-check", "-r", REQUIREMENTS], log) != 0:
                return False, "The installation failed. Is there an internet connection?"
            ok, msg = envsetup.check(py)
            return ok, ("Packages installed: " + msg) if ok else msg
        return self.jobs.start("setup", run)

    def job_sheet(self, pr, name):
        return self.jobs.start("sheet", lambda log: pipeline.run_sheet(pr, name, log))

    def job_plot(self, pr, name, plot_id):
        return self.jobs.start("sheet", lambda log: pipeline.run_plot(pr, name, plot_id, log))

    def job_all(self, pr, plots):
        return self.jobs.start("sheet", lambda log: pipeline.run_all(pr, log, plots))

    def job_report(self, pr, use_ai, rewrite):
        return self.jobs.start("report", lambda log: report.write(pr, log, use_ai, rewrite))

    def job_build(self, pr):
        return self.jobs.start("report", lambda log: report.build(pr, log))

    _rows_cache = {}

    def csv_rows(self, path):
        """number of data rows of a CSV (cached by modification time)"""
        key = (str(path), path.stat().st_mtime)
        if key not in self._rows_cache:
            with open(path, newline="", encoding="utf-8-sig") as f:
                self._rows_cache[key] = max(sum(1 for _ in csv.reader(f)) - 1, 0)
        return self._rows_cache[key]

    def sheets_info(self, pr):
        out = []
        for spec in sheetlist.SHEETS:
            st = pipeline.sheet_state(pr, spec["name"])
            csvs = []
            for c in spec["csvs"]:
                p = pipeline.sheet_csv(pr, spec["name"], c)
                pic = p.with_name(p.stem + "_table.png")
                csvs.append({"file": c, "exists": p.exists(), "rows": self.csv_rows(p) if p.exists() else 0,
                             "picture": pic.exists() and p.exists() and pic.stat().st_mtime >= p.stat().st_mtime - 5})
            plots = [{"id": p["id"], "title": p["title"], "files": [self.plot_file(pr, spec["name"], f) for f in p["files"]]} for p in spec["plots"]]
            out.append({**{k: spec[k] for k in ("name", "group", "title", "what", "needs")}, **st, "csvs": csvs, "plots": plots,
                        "log": (pr.dir / spec["name"] / f"{spec['name']}_log.txt").exists(),
                        "explain": spec["explain"], "downloads": [{**d, "exists": (pr.dir / spec["name"] / d["file"]).exists()} for d in spec["downloads"]], "options": [{**o, "value": sheetlist.option_values(pr, spec["name"])[o["id"]]} for o in spec["options"]],
                        "plot_years": sheetlist.plot_years(pr, spec["name"]), "run_info": (pr.dir / spec["name"] / "run_info.json").exists(),
                        "input": self.input_info(pr, spec)})
        return {"sheets": out, "groups": sheetlist.GROUPS, "clean_ready": pr.clean_file.exists(), "bookmarks": pr.load().get("bookmarks") or {}}

    @staticmethod
    def input_info(pr, spec):
        """the file a sheet reads that the user chooses (e.g. the Scopus Source List): what it is and which file is in use"""
        if not spec.get("input"):
            return None
        f = sheetlist.input_file(pr, spec["name"])
        return {**spec["input"], "file": f.name if f else None, "mb": round(f.stat().st_size / 1048576, 1) if f else 0,
                "when": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%dT%H:%M:%S") if f else None}

    def save_input(self, pr, sheet, name, stream_in, length):
        """copy a file the user chose for a sheet into the project (<project>/<input folder>/); earlier files stay, the newest is used"""
        spec = sheetlist.get(sheet)
        inp = spec.get("input") if spec else None
        if not inp:
            return False, "This sheet does not read a file of yours."
        safe = re.sub(r"[^\w .()+\-]", "_", Path(unquote(name)).name).strip()
        if Path(safe).suffix.lower() not in inp["accept"]:
            return False, f"Choose a file of type {' or '.join(inp['accept'])} (the {inp['label']})."
        folder = pr.dir / inp["folder"]
        folder.mkdir(parents=True, exist_ok=True)
        part = folder / (safe + ".part")
        left = length
        with open(part, "wb") as f:
            while left > 0:
                chunk = stream_in.read(min(1 << 20, left))
                if not chunk:
                    break
                f.write(chunk)
                left -= len(chunk)
        with open(part, "rb") as f:
            head = f.read(4)
        if left > 0 or (safe.lower().endswith(".xlsx") and head != b"PK\x03\x04"):
            part.unlink(missing_ok=True)
            return False, "The copy was not complete." if left > 0 else "This is not an Excel (.xlsx) file: download the Source List again."
        dst = folder / safe
        part.replace(dst)
        os.utime(dst)                                            # the newest file is the one in use
        return True, f"Copied to {pr.rel(dst)} ({dst.stat().st_size / 1048576:.1f} MB). Generate the data to use it."

    @staticmethod
    def plot_file(pr, name, f):
        """a picture of a sheet: does its PNG exist, and which extra formats (PDF, TIFF) were written with this PNG (not left over from an earlier look)"""
        png = pr.dir / name / f"{f}.png"
        if not png.exists():
            return {"name": f, "exists": False, "extra": []}
        t = png.stat().st_mtime
        return {"name": f, "exists": True, "extra": [ext for ext in ("pdf", "tif") if (pr.dir / name / f"{f}.{ext}").exists() and (pr.dir / name / f"{f}.{ext}").stat().st_mtime >= t - 30]}

    def table(self, pr, name, csv_file, page, size):
        spec = sheetlist.get(name)
        if spec is None or csv_file not in spec["csvs"]:
            return {"exists": False}
        p = pipeline.sheet_csv(pr, name, csv_file)
        if not p.exists():
            return {"exists": False}
        with open(p, newline="", encoding="utf-8-sig") as f:
            rd = csv.reader(f)
            header = next(rd, [])
            rows, total = [], 0
            for row in rd:
                if page * size <= total < (page + 1) * size:
                    rows.append(row)
                total += 1
        return {"exists": True, "columns": header, "rows": rows, "total": total, "page": page, "size": size}

    # ---------------------------------------------------------------- data
    def save_upload(self, pr, name, stream_in, length):
        safe = re.sub(r"[^\w .()+\-]", "_", Path(unquote(name)).name).strip() or "scopus_export.csv"
        pr.raw.mkdir(parents=True, exist_ok=True)
        part = pr.raw / (safe + ".part")
        left = length
        with open(part, "wb") as f:
            while left > 0:
                chunk = stream_in.read(min(1 << 20, left))
                if not chunk:
                    break
                f.write(chunk)
                left -= len(chunk)
        ok, msg, n = dataset.validate(part)
        if not ok:
            part.unlink(missing_ok=True)
            return False, msg
        dst = pr.raw / safe
        part.replace(dst)
        dataset.register(pr, dst, safe, n)
        return True, f"Copied to {pr.rel(dst)} ({msg})"

    def preview(self, pr, rows=25):
        if not pr.clean_file.exists():
            return {"exists": False}
        with open(pr.clean_file, newline="", encoding="utf-8-sig") as f:
            rd = csv.reader(f)
            header = next(rd)
            take = [i for i, c in enumerate(header) if c in PREVIEW_COLUMNS] or list(range(min(7, len(header))))
            out, total = [], 0
            for row in rd:
                total += 1
                if len(out) < rows:
                    out.append([row[i] if i < len(row) else "" for i in take])
        return {"exists": True, "columns": [header[i] for i in take], "rows": out, "total": total, "all_columns": len(header)}


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        server_version = "TheDataApplication"
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):        # quiet
            pass

        # ------------------------------------------------ plumbing
        def _send(self, code, body=b"", ctype="application/json", extra=None):
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode("utf-8")
            elif isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json_body(self):
            n = int(self.headers.get("Content-Length") or 0)
            if not n:
                return {}
            try:
                return json.loads(self.rfile.read(n).decode("utf-8"))
            except ValueError:
                return {}

        def _allowed_host(self):
            ok_hosts = (f"127.0.0.1:{app.port}", f"localhost:{app.port}")
            if self.headers.get("Host", "") not in ok_hosts:
                return False
            origin = self.headers.get("Origin")
            return not origin or origin in (f"http://127.0.0.1:{app.port}", f"http://localhost:{app.port}")

        def _has_key(self):
            for part in (self.headers.get("Cookie") or "").split(";"):
                if part.strip() == "tda=" + app.token:
                    return True
            return False

        # ------------------------------------------------ GET
        def do_GET(self):
            if not self._allowed_host():
                return self._send(403, {"error": "forbidden"})
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if q.get("key", [""])[0] == app.token:                       # first visit: remember the key in a cookie, then show the page
                tab = re.sub(r"[^A-Za-z0-9_:]", "", q.get("tab", [""])[0])[:60]        # optional ?tab=settings: start on that tab (used by tests)
                return self._send(302, b"", "text/plain", {"Location": "/" + ("#" + tab if tab else ""), "Set-Cookie": f"tda={app.token}; Path=/; HttpOnly; SameSite=Strict"})
            if not self._has_key():
                return self._send(401, "<h2>Open The Data Application with its launcher.</h2>", "text/html; charset=utf-8")
            p = u.path
            pr = app.project
            if p == "/api/status":
                return self._send(200, app.status())
            if p == "/api/update":
                return self._send(200, {**update.state(), "installed": app.updated})
            if p == "/api/projects":
                return self._send(200, app.projects_list())
            if p == "/api/job":
                return self._send(200, app.jobs.snapshot(int(q.get("since", ["0"])[0])))
            if p == "/api/preview":
                return self._send(200, app.preview(pr) if pr else {"exists": False})
            if p == "/api/report":
                return self._send(200, {"text": pr.clean_report.read_text(encoding="utf-8") if pr and pr.clean_report.exists() else ""})
            if p == "/api/ai":                                         # AI writing: provider, model, whether a key is saved (never the key)
                return self._send(200, ai.status())
            if p == "/api/report/state":
                return self._send(200, report.state(pr) if pr else {"error": "no project is open"})
            if p == "/api/sheets":
                return self._send(200, app.sheets_info(pr) if pr else {"sheets": [], "groups": [], "clean_ready": False})
            if p == "/api/sheet/table":
                if pr is None:
                    return self._send(409, {"error": "no project is open"})
                name = q.get("name", [""])[0]
                spec = sheetlist.get(name)
                csv_file = q.get("csv", [spec["csvs"][0] if spec else ""])[0]
                return self._send(200, app.table(pr, name, csv_file, max(int(q.get("page", ["0"])[0]), 0), min(max(int(q.get("size", ["50"])[0]), 1), 500)))
            if p.startswith("/files/"):                              # pictures and tables of a sheet: /files/<sheet>/<file>
                parts = p[len("/files/"):].split("/")
                if pr is None or len(parts) != 2 or (sheetlist.get(parts[0]) is None and parts[0] not in ("01_Clean_Data", report.FOLDER)):
                    return self._send(404, {"error": "not found"})
                fname = Path(parts[1]).name
                path = pr.dir / parts[0] / fname
                if path.suffix not in (".png", ".svg", ".pdf", ".tif", ".csv", ".txt", ".html", ".json") or not path.is_file() or (path.suffix in (".html", ".pdf", ".tif") and not q.get("download")):
                    return self._send(404, {"error": "not found"})            # an .html file of a task is only offered as a download, never shown by the application itself
                extra = {"Content-Disposition": f'attachment; filename="{fname}"'} if q.get("download") else None
                return self._send(200, path.read_bytes(), MIME.get(path.suffix, "application/octet-stream"), extra)
            if p.startswith("/download/"):
                name = p[len("/download/"):]
                path = {"clean_main_data.csv": pr.clean_file, "clean_report.txt": pr.clean_report, "clean_log.txt": pr.clean_log, "run_info.json": pr.clean / "run_info.json"}.get(name) if pr else None
                if path is None or not path.exists():
                    return self._send(404, {"error": "not found"})
                return self._send(200, path.read_bytes(), MIME.get(path.suffix, "application/octet-stream"),
                                  {"Content-Disposition": f'attachment; filename="{name}"'})
            rel = "index.html" if p in ("/", "") else p.lstrip("/")
            f = (WEB / rel).resolve()
            if WEB.resolve() not in f.parents or not f.is_file():
                return self._send(404, {"error": "not found"})
            return self._send(200, f.read_bytes(), MIME.get(f.suffix, "application/octet-stream"))

        # ------------------------------------------------ POST
        def do_POST(self):
            if not self._allowed_host() or not self._has_key():
                return self._send(403, {"error": "forbidden"})
            u = urlparse(self.path)
            p = u.path
            if p == "/api/ping":
                app.last_ping = time.time()
                return self._send(200, {"ok": True})
            if p == "/api/quit":
                self._send(200, {"ok": True})
                threading.Thread(target=app.httpd.shutdown, daemon=True).start()
                return
            pr = app.project
            if p == "/api/project/close":
                if app.busy():
                    return self._send(200, {"ok": False, "message": "A task is still running: wait until it has finished."})
                app.project = None
                return self._send(200, {"ok": True})
            if p == "/api/data/upload":
                if pr is None:
                    return self._send(409, {"error": "no project is open"})
                name = parse_qs(u.query).get("name", ["scopus_export.csv"])[0]
                length = int(self.headers.get("Content-Length") or 0)
                ok, msg = app.save_upload(pr, name, self.rfile, length)
                return self._send(200, {"ok": ok, "message": msg})
            if p == "/api/sheet/input":
                if pr is None:
                    return self._send(409, {"error": "no project is open"})
                q = parse_qs(u.query)
                length = int(self.headers.get("Content-Length") or 0)
                ok, msg = app.save_input(pr, q.get("sheet", [""])[0], q.get("name", [""])[0], self.rfile, length)
                return self._send(200, {"ok": ok, "message": msg})
            body = self._json_body()
            if p == "/api/settings":                                  # text size and theme: settings of the application itself
                cfg = config.app_load()
                ui = cfg.get("ui", {})
                for k in ("font", "theme"):
                    if k in body:
                        ui[k] = body[k]
                cfg["ui"] = ui
                config.app_save(cfg)
                return self._send(200, {"ok": True})
            if p == "/api/update/check":
                return self._send(200, update.check(force=True))
            if p == "/api/update/settings":
                return self._send(200, update.set_enabled(body.get("enabled", True)))
            if p == "/api/update/skip":
                return self._send(200, update.skip(str(body.get("version", ""))))
            if p == "/api/update/install":
                if app.busy():
                    return self._send(200, {"started": False, "message": "A task is still running: wait until it has finished."})

                def run(log):
                    ok, msg = update.install(log)
                    app.updated = app.updated or ok
                    return ok, msg
                return self._send(200, {"started": app.jobs.start("update", run)})
            if p == "/api/update/restart":
                if not app.updated:
                    return self._send(200, {"ok": False, "message": "No new version was installed."})
                update.restart()
                self._send(200, {"ok": True})
                threading.Thread(target=app.httpd.shutdown, daemon=True).start()
                return
            if p == "/api/ai/settings":
                return self._send(200, {"ok": True, "settings": ai.save_settings(body), "status": ai.status()})
            if p == "/api/ai/key":
                prov = body.get("provider", "")
                if body.get("delete"):
                    ai.delete_key(prov)
                    return self._send(200, {"ok": True, "message": "The key was removed.", "status": ai.status()})
                ok, msg = ai.set_key(prov, body.get("key", ""))
                if ok:                                             # a new key is tested at once by asking for the provider's models
                    good, models = ai.list_models(prov)
                    msg = msg + (" The key works: %d models available." % len(models) if good else " But: " + models)
                return self._send(200, {"ok": ok, "message": msg, "status": ai.status()})
            if p == "/api/ai/models":
                ok, models = ai.list_models(body.get("provider", ""))
                return self._send(200, {"ok": ok, "models": models if ok else [], "message": "" if ok else models})
            if p == "/api/browse":
                path, err = native.browse(body.get("kind", "folder"), body.get("title", "venv"))
                return self._send(200, {"path": path, "error": err})
            if p in ("/api/project/create", "/api/project/open", "/api/project/add", "/api/project/forget", "/api/project/sample"):
                if app.busy():
                    return self._send(200, {"ok": False, "message": "A task is still running: wait until it has finished."})
                if p == "/api/project/forget":                      # off the list only; the folder and its files stay
                    projects.forget(body.get("path", ""))
                    return self._send(200, {"ok": True})
                if p == "/api/project/create":
                    target, err = projects.create(body.get("name", ""), body.get("location", ""))
                elif p == "/api/project/sample":                   # a project with made-up data, to try the application before having an export
                    target, err = sample.create_sample_project(body.get("location", ""))
                elif p == "/api/project/add":
                    target, err = projects.add_existing(body.get("path", ""))
                else:
                    target = projects.get(body.get("path", ""))
                    err = None if target else "That project is not in the list or its folder is gone."
                if target is None:
                    return self._send(200, {"ok": False, "message": err})
                target.touch()
                app.project = target
                return self._send(200, {"ok": True, "path": str(target.dir)})
            if pr is None:
                return self._send(409, {"error": "no project is open"})
            if p == "/api/env/create":
                return self._send(200, {"started": app.job_setup(pr, None)})
            if p == "/api/env/use":
                text = (body.get("path") or "").strip()
                py = envsetup.resolve(text) if text else None
                if py is None:
                    return self._send(200, {"ok": False, "message": "No python found there. Give the folder of your venv (it contains pyvenv.cfg and a bin or Scripts folder)."})
                ok, msg = envsetup.check(py)
                if ok:
                    pr.set_python(py)
                    return self._send(200, {"ok": True, "message": "Environment ready: " + msg})
                if msg.startswith("missing packages"):
                    if body.get("install"):
                        return self._send(200, {"started": app.job_setup(pr, text, True)})
                    return self._send(200, {"ok": False, "needs_install": True, "message": "This venv is missing packages (" + msg.split(": ", 1)[1] + ")."})
                return self._send(200, {"ok": False, "message": msg})
            if p == "/api/env/install":
                return self._send(200, {"started": app.job_install(pr)})
            if p == "/api/bookmark":                                 # a coloured star in the menu: {page, color} (color null = remove)
                page, color = str(body.get("page", ""))[:80], body.get("color")
                if not page or color not in (None, "red", "green", "violet", "orange"):
                    return self._send(400, {"error": "Choose red, green, violet or orange."})
                marks = dict(pr.load().get("bookmarks") or {})
                if color is None:
                    marks.pop(page, None)
                else:
                    marks[page] = color
                pr.update(bookmarks=marks or None)
                return self._send(200, {"bookmarks": marks})
            if p == "/api/sheet/options":
                spec = sheetlist.get(body.get("name", ""))
                if spec is None or not spec["options"]:
                    return self._send(400, {"error": "This sheet has no options."})
                return self._send(200, {"values": sheetlist.save_options(pr, spec["name"], body.get("values") or {})})
            if p == "/api/sheet/run":
                return self._send(200, {"started": app.job_sheet(pr, body.get("name", ""))})
            if p == "/api/sheet/plot":
                return self._send(200, {"started": app.job_plot(pr, body.get("name", ""), body.get("plot", ""))})
            if p == "/api/sheets/run_all":
                return self._send(200, {"started": app.job_all(pr, bool(body.get("plots")))})
            if p == "/api/clean/options":
                opts = dict(pr.load().get("clean_options") or {})
                if "exclude_only_queries" in body:
                    opts["exclude_only_queries"] = ",".join(q for q in re.split(r"[,;\s]+", str(body.get("exclude_only_queries") or "")) if q)
                if "country_fallback" in body:
                    opts["country_fallback"] = bool(body["country_fallback"])
                pr.update(clean_options=opts)
                return self._send(200, {"exclude_only_queries": pipeline.clean_exclude(pr), "country_fallback": pipeline.clean_country_fallback(pr)})
            if p == "/api/years":                                     # the years the plots of this project draw
                try:
                    if body.get("roll"):
                        years.roll_forward(pr)
                    else:
                        years.set_window(pr, body.get("preset", ""), body.get("from") or 0, body.get("to") or 0)
                except (ValueError, TypeError) as e:
                    return self._send(200, {"ok": False, "message": str(e), "years": years.info(pr)})
                return self._send(200, {"ok": True, "years": years.info(pr)})
            if p == "/api/look":                                      # the look of this project's plots
                return self._send(200, {"ok": True, "look": look.save(pr, body.get("values") or {})})
            if p == "/api/clean":
                return self._send(200, {"started": app.job_clean(pr)})
            if p == "/api/report/options":
                report.save_options(pr, body)
                return self._send(200, report.state(pr))
            if p in ("/api/report/template", "/api/report/default"):
                if app.busy():
                    return self._send(200, {"ok": False, "message": "A task is still running: wait until it has finished."})
                ok, msg = report.use_template(pr, body.get("path", "")) if p.endswith("template") else report.use_default(pr)
                return self._send(200, {"ok": ok, "message": msg})
            if p == "/api/report/write":
                return self._send(200, {"started": app.job_report(pr, bool(body.get("ai", True)), bool(body.get("rewrite")))})
            if p == "/api/report/build":
                return self._send(200, {"started": app.job_build(pr)})
            if p == "/api/open":
                where = {"raw": pr.raw, "clean": pr.clean, "project": pr.dir, "app": ROOT, "report": report.folder(pr)}.get(body.get("which"), pr.dir)
                if sheetlist.get(body.get("sheet", "")):
                    where = pr.dir / body["sheet"]
                where.mkdir(parents=True, exist_ok=True)
                return self._send(200, {"ok": native.show_in_file_manager(where)})
            return self._send(404, {"error": "not found"})
    return Handler


def run(port=0, open_window=True):
    app = App(port)
    print(f"The Data Application is running at {app.url}", flush=True)
    how = window.open_window(app.url) if open_window else "not opened (--no-window)"
    print("Opened as:", how, flush=True)

    def watchdog():                       # ends the application when its window has been closed
        while True:
            time.sleep(2)
            now = time.time()
            if app.last_ping is None and now - app.started > FIRST_PING_SECONDS and open_window:
                break
            if app.last_ping is not None and now - app.last_ping > IDLE_SECONDS:
                break
        app.httpd.shutdown()
    if open_window:
        threading.Thread(target=watchdog, daemon=True).start()
    try:
        app.httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    print("The Data Application has stopped.", flush=True)
    return 0
