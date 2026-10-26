"""Tests of The Data Application. They never touch your settings or projects: everything happens in a temporary folder.

    python -m unittest discover -s tests -v                 everything (needs a Python with pandas, numpy and matplotlib: the full run takes 2-3 minutes)
    TDA_QUICK=1 python -m unittest discover -s tests -v     only the fast tests (the standard library is enough)

The full run makes the sample project (made-up data, app/sample.py), cleans it, generates every sheet and every plot, and checks that each file
the application lists was written, that the run records exist, and that the plot-look wrapper writes PDF and TIFF files.
"""
import csv
import http.client
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import date
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="tda_test_"))
os.environ["THE_DATA_APP_HOME"] = str(TMP / "appdata")          # before the application is imported: its settings go to the temporary folder
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["THE_DATA_APP_UPDATE_API"] = "http://127.0.0.1:9/no-update-server"   # the tests never ask GitHub
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "steps" / "common"))

from app import dataset, look, pipeline, project as projects, sample, sheets, update, years  # noqa: E402
import names  # noqa: E402

DAY = date(2026, 10, 24)


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def have_science():
    try:
        import matplotlib, numpy, pandas  # noqa: F401
        return True
    except ImportError:
        return False


def new_project(name):
    pr, err = projects.create(name, str(TMP / "projects"))
    assert pr is not None, err
    return pr


class Years(unittest.TestCase):
    def test_presets(self):
        self.assertEqual(years.resolve("last10", DAY), (2016, 2025))
        self.assertEqual(years.resolve("last5", DAY), (2021, 2025))
        self.assertEqual(years.resolve("last10", DAY, last_data=2020), (2011, 2020))        # an export that ends in 2020
        self.assertEqual(years.resolve("last10", date(2027, 1, 2)), (2017, 2026))
        self.assertEqual(years.resolve("all", DAY), (0, 0))
        self.assertEqual(years.resolve("custom", DAY, lo=2020, hi=2010), (2010, 2020))

    def test_saved_until_rolled_forward(self):
        pr = new_project("Years test")
        w = years.set_window(pr, "last10", today=DAY)
        self.assertEqual((w["from"], w["to"]), (2016, 2025))
        self.assertEqual(years.get(pr)["to"], 2025)                       # next year it is still 2016-2025 ...
        info = years.info(pr, today=date(2027, 3, 1))
        self.assertTrue(info["can_roll"])
        self.assertEqual(info["today"], [2017, 2026])
        w = years.roll_forward(pr, today=date(2027, 3, 1))                  # ... until it is rolled forward
        self.assertEqual((w["from"], w["to"]), (2017, 2026))
        with self.assertRaises(ValueError):
            years.set_window(pr, "custom", 1200, 2000)

    def test_sheet_choices(self):
        pr = new_project("Sheet years test")
        years.set_window(pr, "last10", today=DAY)
        self.assertEqual(sheets.option_args(pr, "04_Avg_Citations", plot=True), ["--from-year", "2016", "--to-year", "2025"])   # default: the project's years
        self.assertEqual(sheets.option_args(pr, "03_Annual_Production", plot=True), ["--from-year", "0", "--to-year", "0"])     # default: all years
        sheets.save_options(pr, "04_Avg_Citations", {"years": "custom", "year_from": 2001, "year_to": 2010})
        self.assertEqual(sheets.option_args(pr, "04_Avg_Citations", plot=True), ["--from-year", "2001", "--to-year", "2010"])
        self.assertEqual(sheets.option_args(pr, "04_Avg_Citations"), [])                                  # year choices never reach the data script
        cfg = pr.load()                                                    # a project saved before the "years" choice existed keeps its two years
        cfg["sheet_options"]["11_Sources_Over_Time"] = {"year_from": 1999, "year_to": 2004}
        pr.save(cfg)
        self.assertEqual(sheets.option_values(pr, "11_Sources_Over_Time")["years"], "custom")
        self.assertIn("--top-sources", sheets.option_args(pr, "11_Sources_Over_Time"))
        sheets.save_options(pr, "17_Top_Affiliations", {"by": "nonsense"})
        self.assertEqual(sheets.option_values(pr, "17_Top_Affiliations")["by"], "institution")


class Validation(unittest.TestCase):
    def write(self, name, data):
        p = TMP / "files" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def test_messages(self):
        ok = self.write("ok.csv", b"EID,Title,Authors,Year\n2-s2.0-1,A,B,2020\n")
        self.assertTrue(dataset.validate(ok)[0])
        cases = {"semi.csv": (b"EID;Title;Authors;Year\n1;2;3;4\n", "semicolons"), "book.xlsx": (b"PK\x03\x04rest", "Excel workbook"),
                 "wos.txt": (b"FN Clarivate Analytics Web of Science\n", "Web of Science"), "latin.csv": ("EID,Title,Authors,Year\n1,Universit\xe4t,B,2020\n".encode("cp1252"), "UTF-8"),
                 "cols.csv": (b"Title,Year\nA,2020\n", "not a Scopus export"), "empty.csv": (b"", "empty"), "none.csv": (b"EID,Title,Authors,Year\n", "no papers")}
        for name, (data, words) in cases.items():
            ok, msg, _ = dataset.validate(self.write(name, data))
            self.assertFalse(ok, name)
            self.assertIn(words, msg, name)


class Pieces(unittest.TestCase):
    def test_moved_project(self):
        """a project folder that was moved is found again: the list points to the new folder, nothing else changes"""
        pr = new_project("Moved project test")
        old = pr.dir
        new = TMP / "moved_here" / old.name
        new.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old), str(new))
        self.assertFalse(next(p for p in projects.list_projects() if p["path"] == str(old))["exists"])
        moved, err = projects.relocate(str(old), str(new))
        self.assertIsNone(err)
        paths = [p["path"] for p in projects.list_projects()]
        self.assertIn(str(new.resolve()), paths)
        self.assertNotIn(str(old), paths)
        self.assertEqual(projects.relocate(str(new), str(TMP))[0], None)          # a folder without project.json is refused

    def test_shared_venv(self):
        """all projects share one venv in the settings folder (never inside a project, never in the application folder)"""
        from app import paths
        pr = new_project("Shared venv test")
        pr.set_python(paths.shared_python())
        self.assertEqual(pr.load()["python"], "shared")
        self.assertEqual(pr.python(), paths.shared_python())
        self.assertTrue(pr.uses_shared())
        self.assertIn(Path(os.environ["THE_DATA_APP_HOME"]), paths.SHARED_VENV.parents)
        self.assertNotIn(ROOT, paths.SHARED_VENV.parents)
        self.assertNotIn(pr.dir, paths.SHARED_VENV.parents)

    def test_venv_python_is_not_followed(self):
        """the python of a venv is a link to the base python: resolving it would leave the venv (and pip would then refuse a Homebrew python)"""
        from app import envsetup
        v = TMP / "linkvenv"
        (v / "bin").mkdir(parents=True, exist_ok=True)
        (v / "pyvenv.cfg").write_text("home = x\n", encoding="utf-8")
        link = v / "bin" / "python3"
        if not link.exists():
            os.symlink(sys.executable, link)
        for given in (str(link), str(v), str(v / "bin")):
            self.assertEqual(envsetup.resolve(given), link, given)

    def test_look(self):
        pr = new_project("Look test")
        self.assertEqual(look.args(pr), ["--no-titles"])                   # the defaults: no title at the top of the plots (it goes to the plot's log)
        look.save(pr, {"titles": True})
        self.assertEqual(look.args(pr), [])                                # titles on and the rest default: the plot script runs on its own
        look.save(pr, {"text": 9, "palette": "colourblind", "pdf": True, "dpi": 123})
        lk = look.get(pr)
        self.assertEqual((lk["text"], lk["dpi"], lk["palette"]), (2.5, 0, "colourblind"))      # clipped and checked
        self.assertEqual(look.args(pr), ["--text", "2.5", "--formats", "pdf", "--palette", "colourblind"])
        look.save(pr, {"titles": False})
        self.assertEqual(look.args(pr)[-1], "--no-titles")

    def test_explain_failure(self):
        msg = pipeline.explain_failure(["Traceback (most recent call last):", "  File x", "KeyError: 'Affiliations'"])
        self.assertIn("export the data again from Scopus", msg)
        self.assertIn("is not installed", pipeline.explain_failure(["ModuleNotFoundError: No module named 'matplotlib'"]))

    def test_names(self):
        self.assertEqual(names.parent_of_affiliation("Aerospace Information Research Institute, Chinese Academy of Sciences, Beijing, China"), "Chinese Academy of Sciences")
        self.assertIsNone(names.parent_of_affiliation("University of Chinese Academy of Sciences, Beijing, China"))
        self.assertIsNone(names.parent_of_affiliation("Leibniz University Hannover, Hannover, Germany"))
        self.assertEqual(names.parent_of_affiliation("CSIR-National Geophysical Research Institute, Hyderabad, India"), "CSIR (India)")
        learned = names.learn_institution_countries(["Wuhan University, Wuhan, China", "School of Geography, Wuhan University, Wuhan, 430072, China", "Wuhan University, Wuhan"])
        self.assertEqual(names.country_with_fallback("Wuhan University, Wuhan", learned), ("China", "institution"))
        self.assertEqual(names.country_with_fallback("Wuhan University, Wuhan, China", learned), ("China", "address"))
        for empty in ("", " ", ",", " , "):                 # Scopus writes "; ; ;" for some correspondence addresses (crashed 0.4.0)
            self.assertIsNone(names.institution_of_affiliation(empty))
            self.assertEqual(names.country_with_fallback(empty, learned), (None, None))
        once = names.learn_institution_countries(["Lone Institute, Paris, France", "Lone Institute, Paris"])
        self.assertEqual(names.country_with_fallback("Lone Institute, Paris", once), (None, None))            # one address is not enough

    def test_sample_data(self):
        a, b = sample.make_rows(seed=3, today=DAY), sample.make_rows(seed=3, today=DAY)
        self.assertEqual(a, b)                                             # same seed, same data
        self.assertEqual(max(int(r["Year"]) for r in a), 2027)              # early access: next year's date
        p = TMP / "files" / "sample.csv"
        sample.write_csv(p, today=DAY)
        ok, msg, n = dataset.validate(p)
        self.assertTrue(ok, msg)
        self.assertGreater(n, 500)


class OldPython(unittest.TestCase):
    def test_no_new_fstring_quotes(self):
        """the application must run on Python 3.9: an f-string that reuses its own quote inside {} (allowed only from 3.12) stops a script there"""
        import re
        same = re.compile(r"""\bf"[^"\n]*\{[^}"\n]*"|\bf'[^'\n]*\{[^}'\n]*'""")
        bad = []
        for f in sorted(list(ROOT.glob("app/*.py")) + list(ROOT.glob("steps/**/*.py")) + [ROOT / "the_data_app.py"]):
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if same.search(line):
                    bad.append(f"{f.relative_to(ROOT)}:{i}")
        self.assertEqual(bad, [])


class Window(unittest.TestCase):
    def test_buttons_work_again_after_a_task(self):
        """a task greys out the buttons (setBusy(true)); when it ends they must work again, or "Choose the Scopus CSV" stays grey after the venv setup"""
        js = (ROOT / "app" / "web" / "app.js").read_text(encoding="utf-8")
        polling = js[js.index("function startPolling"):]
        polling = polling[:polling.index("\n}\n")]
        self.assertIn("setBusy(true)", polling)
        self.assertIn("setBusy(false)", polling[polling.index('j.state !== "running"'):])


class FakeGitHub:
    """a local stand-in for GitHub's 'latest release' API (and the release ZIP)"""

    def __init__(self, tag, zip_path=None, body="- something new"):
        import http.server
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if self.path.startswith("/zip") and zip_path:
                    data = Path(zip_path).read_bytes()
                    self.send_response(200); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
                    return
                data = json.dumps({"tag_name": tag, "name": tag, "body": body, "html_url": "https://example.org/r",
                                   "zipball_url": f"http://127.0.0.1:{outer.port}/zip", "published_at": "2026-10-25T00:00:00Z"}).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(data)
        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), H)
        self.port = self.httpd.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}/latest"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


class FakeAI:
    """a stand-in for the Anthropic API on 127.0.0.1: lists one model and answers every report item with JSON (one invented number in it)"""
    def __init__(self):
        self.requests = []
        self.broke = False
        fake = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, data):
                body = json.dumps(data).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                self._send({"data": [{"id": "claude-test", "display_name": "Claude Test"}], "has_more": False})

            def do_POST(self):
                req = json.loads(self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8"))
                fake.requests.append({"headers": {k.lower(): v for k, v in self.headers.items()}, "body": req})
                if fake.broke:                                       # an account without credit: the API answers 400 for every request
                    body = json.dumps({"type": "error", "error": {"type": "invalid_request_error", "message": "Your credit balance is too low to access the Anthropic API."}}).encode()
                    self.send_response(400)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                text = req["messages"][0]["content"][-1]["text"]
                n = re.search(r"Documents,(\d+)", text)
                answer = {"analysis": f"FAKE ANALYSIS: the data set holds {n.group(1) if n else 0} documents [REF]; *Remote Sensing* leads with 5% & more, and 98765.43 is invented.",
                          "conclusion": "FAKE CONCLUSION: the field grows."}
                self._send({"content": [{"type": "thinking", "thinking": ""}, {"type": "text", "text": json.dumps(answer)}], "stop_reason": "end_turn",
                            "usage": {"input_tokens": 100, "output_tokens": 50}})
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()


@unittest.skipIf(shutil.which("git") is None or not (ROOT / ".git").exists() or os.environ.get("THE_DATA_APP_UPDATING"),
                 "needs git and a git checkout (and does not run inside an update's own check)")
class Updates(unittest.TestCase):
    """the updater, run inside throw-away copies of this repository (never on this folder)"""

    def test_versions(self):
        self.assertTrue(update.newer("v0.10.0", "0.9.9"))
        self.assertFalse(update.newer("0.3.0", "v0.3.0"))
        self.assertEqual(update.parse_version("v1.2.3-beta"), (1, 2, 3))

    def make_release(self, root, version, broken=False):
        """origin repo (a clone of this one, current commit) + a newer commit tagged v<version>; returns the origin path"""
        origin = root / "origin"
        subprocess.run(["git", "clone", "-q", str(ROOT), str(origin)], check=True)
        cur = (ROOT / "app" / "__init__.py").read_text(encoding="utf-8")
        import re as _re
        (origin / "app" / "__init__.py").write_text(_re.sub(r'__version__ = "[^"]+"', f'__version__ = "{version}"', cur), encoding="utf-8")
        if broken:
            (origin / "tests" / "test_broken.py").write_text("import unittest\nclass T(unittest.TestCase):\n    def test(self):\n        self.fail('broken release')\n", encoding="utf-8")
        g = ["git", "-C", str(origin), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run(g + ["add", "-A"], check=True)
        subprocess.run(g + ["commit", "-q", "-m", f"release {version}"], check=True)
        subprocess.run(g + ["tag", f"v{version}"], check=True)
        return origin

    def run_update(self, copy, api, home):
        """install from inside `copy` (a separate process: ROOT is that copy); returns (exit code, output)"""
        env = dict(os.environ, THE_DATA_APP_UPDATE_API=api, THE_DATA_APP_HOME=str(home), PYTHONDONTWRITEBYTECODE="1")
        code = "import sys; from app import update; print(update.check(force=True)['available']); ok, msg = update.install(print); print(msg); sys.exit(0 if ok else 1)"
        r = subprocess.run([sys.executable, "-c", code], cwd=copy, env=env, capture_output=True, text=True, timeout=900)
        return r.returncode, r.stdout + r.stderr

    def test_git_update_and_rollback(self):
        root = Path(tempfile.mkdtemp(dir=TMP))
        origin = self.make_release(root, "9.9.9")
        copy = root / "copy"
        subprocess.run(["git", "clone", "-q", str(ROOT), str(copy)], check=True)
        subprocess.run(["git", "-C", str(copy), "remote", "set-url", "origin", str(origin)], check=True)
        gh = FakeGitHub("v9.9.9")
        try:
            code, out = self.run_update(copy, gh.url, root / "home")
        finally:
            gh.close()
        self.assertEqual(code, 0, out)
        self.assertIn('"9.9.9"', (copy / "app" / "__init__.py").read_text(encoding="utf-8"))
        # a release that fails its own tests is rolled back
        root2 = Path(tempfile.mkdtemp(dir=TMP))
        origin2 = self.make_release(root2, "9.9.8", broken=True)
        copy2 = root2 / "copy"
        subprocess.run(["git", "clone", "-q", str(ROOT), str(copy2)], check=True)
        subprocess.run(["git", "-C", str(copy2), "remote", "set-url", "origin", str(origin2)], check=True)
        before = subprocess.run(["git", "-C", str(copy2), "rev-parse", "HEAD"], capture_output=True, text=True).stdout
        gh = FakeGitHub("v9.9.8")
        try:
            code, out = self.run_update(copy2, gh.url, root2 / "home")
        finally:
            gh.close()
        self.assertNotEqual(code, 0, out)
        self.assertIn("was put back", out)
        self.assertEqual(subprocess.run(["git", "-C", str(copy2), "rev-parse", "HEAD"], capture_output=True, text=True).stdout, before)
        # local changes to tracked files: refused, nothing changed
        (copy / "README.md").write_text("changed by hand", encoding="utf-8")
        (origin / "x.txt").write_text("x")
        gh = FakeGitHub("v9.9.10")
        try:
            code, out = self.run_update(copy, gh.url, root / "home2")
        finally:
            gh.close()
        self.assertNotEqual(code, 0)
        self.assertIn("changed by hand", out)

    def test_zip_update(self):
        root = Path(tempfile.mkdtemp(dir=TMP))
        origin = self.make_release(root, "9.9.9")
        z = root / "release.zip"
        subprocess.run(["git", "-C", str(origin), "archive", "--format=zip", "--prefix=The-Data-Application-v9.9.9/", "-o", str(z), "v9.9.9"], check=True)
        copy = root / "zipcopy"
        subprocess.run(["git", "clone", "-q", str(ROOT), str(copy)], check=True)
        shutil.rmtree(copy / ".git")                       # a copy downloaded as a ZIP has no .git
        gh = FakeGitHub("v9.9.9", zip_path=z)
        try:
            code, out = self.run_update(copy, gh.url, root / "home")
        finally:
            gh.close()
        self.assertEqual(code, 0, out)
        self.assertIn('"9.9.9"', (copy / "app" / "__init__.py").read_text(encoding="utf-8"))
        self.assertTrue(list((root / "home" / "updates").glob("backup_*.zip")))


class Server(unittest.TestCase):
    def test_api(self):
        from app import server
        app = server.App(0)
        threading.Thread(target=app.httpd.serve_forever, daemon=True).start()
        try:
            def call(path, body=None, cookie=True):
                c = http.client.HTTPConnection("127.0.0.1", app.port, timeout=20)
                headers = {"Host": f"127.0.0.1:{app.port}", "Content-Type": "application/json"}
                if cookie:
                    headers["Cookie"] = "tda=" + app.token
                c.request("POST" if body is not None else "GET", path, json.dumps(body) if body is not None else None, headers)
                r = c.getresponse()
                out = r.status, r.read()
                c.close()
                return out
            self.assertEqual(call("/api/status", cookie=False)[0], 401)
            st, body = call("/api/project/sample", {"location": str(TMP / "projects")})
            self.assertTrue(json.loads(body)["ok"])
            st = json.loads(call("/api/status")[1])
            self.assertEqual(st["project"]["years"]["preset"], "last10")
            self.assertIn("version", st)
            r = json.loads(call("/api/years", {"preset": "custom", "from": 2000, "to": 2010})[1])
            self.assertEqual((r["years"]["from"], r["years"]["to"]), (2000, 2010))
            r = json.loads(call("/api/years", {"preset": "custom", "from": 1500, "to": 2010})[1])
            self.assertFalse(r["ok"])
            r = json.loads(call("/api/look", {"values": {"pdf": True}})[1])
            self.assertTrue(r["look"]["pdf"])
            r = json.loads(call("/api/clean/options", {"country_fallback": False})[1])
            self.assertFalse(r["country_fallback"])
            sh = json.loads(call("/api/sheets")[1])
            opts = {o["id"]: o for o in next(s for s in sh["sheets"] if s["name"] == "04_Avg_Citations")["options"]}
            self.assertEqual(opts["years"]["kind"], "select")
            self.assertEqual(opts["year_from"]["show_if"], ["years", "custom"])
            dt = next(s for s in sh["sheets"] if s["name"] == "Document_Types")     # the report's names are shown with every plot and table
            ref = dt["plots"][0]["files"][0]["report"]
            self.assertEqual((ref["kind"], ref["title"], ref["stem"]), ("fig", "Share of the document types", "fig_document_types_pie"))
            self.assertEqual(dt["csvs"][0]["report"]["stem"], "tab_Document_Types")
            self.assertFalse(json.loads(call("/api/report/tick", {"stem": "tab_Document_Types", "on": False})[1])["selected"])   # the tick box on a sheet page
            dt = next(s for s in json.loads(call("/api/sheets")[1])["sheets"] if s["name"] == "Document_Types")
            self.assertFalse(dt["csvs"][0]["report"]["selected"])
            self.assertTrue(json.loads(call("/api/report/tick", {"stem": "tab_Document_Types", "on": True})[1])["selected"])
            r = json.loads(call("/api/sheet/table_rows", {"name": "09_Pivot", "rows": 12})[1])        # rows in a sheet's table pictures: its own number
            self.assertEqual(r["rows"], 12)
            self.assertEqual(look.table_rows(app.project, "09_Pivot"), 12)
            self.assertEqual(look.table_rows(app.project, "07_Top_Sources"), look.get(app.project)["table_rows"])
            for _ in range(50):
                if json.loads(call("/api/job")[1])["state"] != "running":
                    break
                time.sleep(0.1)
            self.assertEqual(json.loads(call("/api/sheet/table_rows", {"name": "09_Pivot", "rows": None})[1])["rows"], look.get(app.project)["table_rows"])
            self.assertEqual(look.save(app.project, {"table_rows": 7})["table_rows"], 7)                  # any number, not only 20/50/100
            def idle():
                for _ in range(50):
                    if json.loads(call("/api/job")[1])["state"] != "running":
                        return
                    time.sleep(0.1)
            idle()
            r = json.loads(call("/api/sheet/table_rows", {"name": "Bradford_Core", "csv": "Bradford_Core_matrix.csv", "rows": 5})[1])   # one picture's own number
            self.assertEqual(r["rows"], 5)
            self.assertEqual(look.table_rows(app.project, "Bradford_Core", "Bradford_Core_matrix.csv"), 5)
            self.assertEqual(look.table_rows(app.project, "Bradford_Core", "Bradford_Core.csv"), 7)
            bc = next(s for s in json.loads(call("/api/sheets")[1])["sheets"] if s["name"] == "Bradford_Core")
            self.assertEqual([(c["file"], c["picture_rows"], c["picture_rows_own"]) for c in bc["csvs"]],
                             [("Bradford_Core.csv", 7, False), ("Bradford_Core_baseline.csv", 7, False), ("Bradford_Core_matrix.csv", 5, True)])
            idle()
            self.assertTrue(json.loads(call("/api/tables/redraw", {})[1])["started"])                    # Settings: redraw every table picture
            idle()
            # a file the user chooses for a sheet (the Scopus Source List): the sample project brings a made-up one; wrong types are refused
            sa = next(s for s in sh["sheets"] if s["name"] == "Subject_Areas")
            self.assertEqual(sa["input"]["file"], "sample_source_list.csv")

            def upload(name, data):
                c = http.client.HTTPConnection("127.0.0.1", app.port, timeout=20)
                c.request("POST", "/api/sheet/input?sheet=Subject_Areas&name=" + name, data,
                          {"Host": f"127.0.0.1:{app.port}", "Cookie": "tda=" + app.token, "Content-Length": str(len(data))})
                out = json.loads(c.getresponse().read())
                c.close()
                return out
            self.assertFalse(upload("list.txt", b"x")["ok"])
            self.assertFalse(upload("list.xlsx", b"not a zip file")["ok"])
            self.assertTrue(upload("my_list.csv", b"Source Title,ISSN,ASJC\nA,12345678,1700\n")["ok"])
            sa = next(s for s in json.loads(call("/api/sheets")[1])["sheets"] if s["name"] == "Subject_Areas")
            self.assertEqual(sa["input"]["file"], "my_list.csv")
            self.assertEqual(sheets.option_args(app.project, "Subject_Areas", plot=True), ["--top", "10"])
        finally:
            app.httpd.shutdown()


@unittest.skipIf(os.environ.get("TDA_QUICK") or not have_science(), "full run skipped (TDA_QUICK set, or this Python has no pandas/numpy/matplotlib)")
class FullRun(unittest.TestCase):
    """the sample project from the export to every plot, with the Python that runs the tests as the project's Python"""

    def test_word_cloud_merges_variants(self):
        """plurals and abbreviations in brackets are one keyword; a paper counts once; an abbreviation that starts with another letter is not taken"""
        folder = TMP / "word_cloud"
        (folder / "01_Clean_Data").mkdir(parents=True, exist_ok=True)
        (folder / "Word_Cloud").mkdir(exist_ok=True)
        rows = [("1", "retrieval augmented generation (rag); rag"), ("2", "rag; knowledge graphs"), ("3", "retrieval augmented generation; knowledge graph"),
                ("4", "large language models (llms); llm"), ("5", "large language model; python (snake)"), ("6", "analysis")]
        with open(folder / "01_Clean_Data" / "clean_main_data.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["EID", "Author Keywords"])
            w.writerows([("2-s2.0-" + e, k) for e, k in rows])
        for name in ("Word_Cloud.py", "Word_Cloud_plot.py"):
            shutil.copy(ROOT / "steps" / "sheets" / "Word_Cloud" / name, folder / "Word_Cloud" / name)
        for script, extra in (("Word_Cloud.py", []), ("Word_Cloud_plot.py", ["--leave-out", "1"])):
            r = subprocess.run([sys.executable, script] + extra, cwd=folder / "Word_Cloud", capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
        with open(folder / "Word_Cloud" / "Word_Cloud.csv", encoding="utf-8-sig") as f:
            got = {row["Keyword"]: int(row["Papers"]) for row in csv.DictReader(f)}
        self.assertEqual(got, {"retrieval augmented generation": 3, "knowledge graph": 2, "large language model": 2, "python (snake)": 1, "analysis": 1})
        self.assertTrue((folder / "Word_Cloud" / "word_cloud.png").exists())

    def test_publisher_names_merge(self):
        """the ways the export writes one publisher are one publisher; a source belongs to the publisher named most often; the treemaps are drawn"""
        folder = TMP / "publishers"
        (folder / "01_Clean_Data").mkdir(parents=True, exist_ok=True)
        (folder / "Publishers").mkdir(exist_ok=True)
        rows = [("1", "Remote Sensing", "MDPI"), ("2", "Remote Sensing", "MDPI AG info@example.org Postfach Basel"),
                ("3", "Remote Sensing", "Multidisciplinary Digital Publishing Institute (MDPI)"), ("4", "Remote Sensing", "Elsevier B.V."),
                ("5", "Journal of Hydrology", "Elsevier B.V."), ("6", "Journal of Hydrology", "Academic Press Inc."), ("7", "", "Elsevier Ltd"),
                ("8", "Small Journal", "Small Society Ltd."), ("9", "Other Journal", "")]
        with open(folder / "01_Clean_Data" / "clean_main_data.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["EID", "Source title", "Publisher", "Cited by"])
            w.writerows([("2-s2.0-" + e, s, p, "1") for e, s, p in rows])
        for name in ("Publishers.py", "Publishers_plot.py"):
            shutil.copy(ROOT / "steps" / "sheets" / "Publishers" / name, folder / "Publishers" / name)
        for script in ("Publishers.py", "Publishers_plot.py"):
            r = subprocess.run([sys.executable, script], cwd=folder / "Publishers", capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
        with open(folder / "Publishers" / "Publishers.csv", encoding="utf-8-sig") as f:
            got = {row["Publisher"]: int(row["Documents"]) for row in csv.DictReader(f)}
        self.assertEqual(got, {"MDPI": 4, "Elsevier": 3, "Small Society": 1, "Unknown publisher": 1})
        with open(folder / "Publishers" / "Publishers.csv", encoding="utf-8-sig") as f:
            self.assertNotIn("@", f.read())                                   # e-mail addresses in the export never reach the table
        self.assertTrue((folder / "Publishers" / "publisher_treemaps.png").exists())

    def test_same_doi_twice(self):
        """one paper indexed twice under two titles (same DOI): the cleaning keeps the first, instead of stopping at the check "no DOI appears twice\""""
        rows = sample.make_rows()
        first = next(r for r in rows if r.get("DOI"))
        rows.append(dict(first, EID="2-s2.0-99999999999", Title=first["Title"] + " Demonstration Track", DOI=first["DOI"].upper(), **{"Cited by": "0"}))
        src, out = TMP / "doi_twice" / "export.csv", TMP / "doi_twice" / "clean.csv"
        src.parent.mkdir(parents=True, exist_ok=True)
        with open(src, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=sample.COLUMNS)
            w.writeheader()
            w.writerows(rows)
        r = subprocess.run([sys.executable, str(ROOT / "steps" / "01_clean_data.py"), "--input", str(src), "--output", str(out)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
        self.assertIn("4b. duplicate papers (same DOI) removed", r.stdout)
        with open(out, encoding="utf-8-sig") as f:
            eids = [row["EID"] for row in csv.DictReader(f)]
        self.assertIn(first["EID"], eids)
        self.assertNotIn("2-s2.0-99999999999", eids)

    def check_report(self, pr, log):
        """the report: written without AI, then by a (stand-in) model; a file the user edited or deleted is kept; the key reaches no file"""
        from app import ai, report
        fake = FakeAI()
        os.environ["THE_DATA_APP_ANTHROPIC_URL"] = fake.url
        ok, msg = report.write(pr, log.append, use_ai=False)
        self.assertTrue(ok, msg + "\n" + "\n".join(log[-20:]))
        rp = pr.dir / "Report"
        self.assertTrue((rp / "report.tex").exists() and (rp / "results_chapter.tex").exists())
        self.assertGreater(sum(1 for it in report.state(pr)["items"] if it["file_state"] == "written"), 40)
        key = "sk-test-" + "k" * 30
        self.assertTrue(ai.set_key("anthropic", key)[0])
        ok, models = ai.list_models("anthropic")
        self.assertTrue(ok and models[0]["id"] == "claude-test", models)
        ai.save_settings({"provider": "anthropic", "model": "claude-test"})
        edited, gone = rp / "results" / "fig_annual_trend.tex", rp / "results" / "fig_lotka.tex"
        edited.write_text(edited.read_text(encoding="utf-8") + "% my own note\n", encoding="utf-8")
        gone.unlink()
        st = {it["stem"]: it for it in report.state(pr)["items"]}
        self.assertEqual((st["fig_lotka"]["file_state"], st["fig_lotka"]["selected"]), ("deleted", False))
        self.assertEqual(st["fig_annual_trend"]["file_state"], "edited")
        ok, msg = report.write(pr, log.append, use_ai=True)
        self.assertTrue(ok, msg + "\n" + "\n".join(log[-20:]))
        text = (rp / "results" / "fig_annual_production.tex").read_text(encoding="utf-8")
        self.assertIn("FAKE ANALYSIS", text)
        self.assertIn("Figure~\\ref{fig:fig_annual_production}", text)
        self.assertIn("\\emph{Remote Sensing}", text)
        self.assertIn("5\\% \\& more", text)
        self.assertIn("% CHECK", text)                                  # the invented number is flagged, the true one is not
        self.assertIn("98765.43", text.splitlines()[3])
        self.assertIn("% my own note", edited.read_text(encoding="utf-8"))
        self.assertFalse(gone.exists())
        for r in fake.requests:
            self.assertEqual(r["headers"].get("x-api-key"), key)
            self.assertNotIn("temperature", r["body"])
            self.assertIn("output_config", r["body"])
        for f in rp.rglob("*"):
            if f.is_file() and f.suffix in (".txt", ".json", ".tex", ".log"):
                self.assertNotIn(key, f.read_text(encoding="utf-8", errors="replace"), f.name)
        n = len(fake.requests)
        ok, msg = report.write(pr, log.append, use_ai=True)                 # nothing changed: the model is not asked again
        self.assertTrue(ok, msg)
        self.assertEqual(len(fake.requests), n)
        fake.broke = True                                                   # no credit: the run stops at the first item, with a plain message
        n = len(fake.requests)
        ok, msg = report.write(pr, log.append, use_ai=True, rewrite=True)
        self.assertFalse(ok)
        self.assertIn("lack of credit", msg)
        self.assertEqual(len(fake.requests), n + 1)
        fake.broke = False
        tpl = TMP / "template"                                              # a template of the user's: packages and the results chapter are added
        tpl.mkdir(exist_ok=True)
        (tpl / "thesis.tex").write_text("\\documentclass{report}\n\\begin{document}\nMy thesis.\n\\end{document}\n", encoding="utf-8")
        ok, msg = report.use_template(pr, str(tpl))
        self.assertTrue(ok, msg)
        main = (rp / "thesis.tex").read_text(encoding="utf-8")
        self.assertIn("\\input{results_chapter}", main)
        self.assertIn("\\usepackage{tabularx}", main)
        self.assertTrue(any(p.name.startswith("_backup_") and (p / "report.tex").exists() for p in rp.iterdir()))
        if report.tex_tool("pdflatex"):
            ok, msg = report.build(pr, log.append)
            self.assertTrue(ok, msg + "\n" + "\n".join(log[-30:]))
        fake.httpd.shutdown()

    def test_everything(self):
        pr, err = sample.create_sample_project(str(TMP / "projects"))
        self.assertIsNotNone(pr, err)
        pr.set_python(Path(sys.executable))
        log = []
        ok, msg = pipeline.clean_data(pr, log.append)
        self.assertTrue(ok, msg + "\n" + "\n".join(log[-20:]))
        self.assertTrue((pr.clean / "institution_countries.csv").exists())
        self.assertIn("got one from the same institution", pr.clean_report.read_text(encoding="utf-8"))
        ok, msg = pipeline.run_all(pr, log.append)
        self.assertTrue(ok, msg + "\n" + "\n".join(log[-30:]))
        ok, msg = pipeline.run_all(pr, log.append, plots=True)
        self.assertTrue(ok, msg + "\n" + "\n".join(log[-30:]))
        missing = []
        for spec in sheets.SHEETS:
            folder = pr.dir / spec["name"]
            if spec["name"] == "Topic_Slices":                              # writes only what topic_slices.json asks for
                continue
            if not (folder / spec["csvs"][0]).exists():
                missing.append(spec["csvs"][0])
            for pl in spec["plots"]:
                for f in pl["files"]:
                    if not (folder / f"{f}.png").exists() and not (spec["name"] == "Bradford_Core" and f.endswith(("_cpp", "_ncs"))):   # these need 3 papers on each side
                        missing.append(f"{spec['name']}/{f}.png")
            if not (folder / "run_info.json").exists():
                missing.append(f"{spec['name']}/run_info.json")
        self.assertEqual(missing, [])
        with open(pr.dir / "Author_Radial" / "Author_Radial.csv", encoding="utf-8-sig") as f:     # authors' countries read from the addresses
            radial = list(csv.DictReader(f))
        self.assertEqual(len(radial), 50)
        self.assertGreater(sum(r["Country"] != "Unknown" for r in radial), 40)
        self.assertEqual([float(r["Fractional score"]) for r in radial], sorted((float(r["Fractional score"]) for r in radial), reverse=True))
        self.check_report(pr, log)
        long_decimals = []                                          # every number in a sheet's tables has at most 2 decimal places
        for spec in sheets.SHEETS:
            for path in (pr.dir / spec["name"]).glob("*.csv"):
                with open(path, encoding="utf-8-sig") as f:
                    long_decimals += [f"{path.name}: {v}" for row in csv.reader(f) for v in row if re.fullmatch(r"-?\d+\.\d{3,}", v)][:1]
        self.assertEqual(long_decimals, [])
        sys.path.insert(0, str(pr.dir / "common"))                 # a year-limited table picture: rows kept, Grand Total recounted
        import table_image
        tmp_csv = TMP / "years.csv"
        tmp_csv.write_text("Country,2014,2015,2016,Grand Total\nA,1,2,3,6\nB,4,0,5,9\n", encoding="utf-8")
        table_image.draw(tmp_csv, 50, "t", 2015, 2016)
        self.assertTrue((TMP / "years_table.svg").exists())
        svg = (TMP / "years_table.svg").read_text(encoding="utf-8")
        self.assertIn("Total 2015–2016", svg)
        self.assertNotIn(">2014<", svg)
        for sheet, csv_name in (("03_Annual_Production", "03_Annual_Production"), ("09_Pivot", "09_Pivot"), ("Bradford_Core", "Bradford_Core_baseline")):
            for ext in ("png", "svg"):                          # every table also as a picture (first look.table_rows rows)
                self.assertTrue((pr.dir / sheet / f"{csv_name}_table.{ext}").exists(), f"{sheet}/{csv_name}_table.{ext}")
        with open(pr.dir / "05_Life_Cycle" / "05_Life_Cycle.csv", encoding="utf-8-sig") as f:
            fit = {int(r["Year"]): r["In Fit"] for r in csv.DictReader(f)}
        this = date.today().year
        self.assertEqual((fit[this - 1], fit[this], fit[this + 1]), ("yes", "no", "no"))       # incomplete years are left out of the fit
        info = json.loads((pr.dir / "04_Avg_Citations" / "run_info.json").read_text(encoding="utf-8"))
        self.assertTrue(info["data"]["ok"] and info["plots"]["all"]["ok"])
        self.assertIn(f"--from-year {this - 10} --to-year {this - 1}", info["plots"]["all"]["command"])
        # the look of the plots: bigger text, colour-blind palette, PDF and TIFF next to the PNG
        look.save(pr, {"text": 1.3, "palette": "colourblind", "pdf": True, "tiff": True, "dpi": 300})
        ok, msg = pipeline.run_plot(pr, "03_Annual_Production", "annual_production", log.append)
        self.assertTrue(ok, msg + "\n" + "\n".join(log[-20:]))
        self.assertIn("title of annual_production (not drawn in the picture): Annual scientific production",
                      (pr.dir / "03_Annual_Production" / "03_Annual_Production_plot_log.txt").read_text(encoding="utf-8"))
        for ext in ("png", "svg", "pdf", "tif"):
            self.assertTrue((pr.dir / "03_Annual_Production" / f"annual_production.{ext}").exists(), ext)
        # counting by parent organisation
        sheets.save_options(pr, "17_Top_Affiliations", {"by": "parent"})
        ok, msg = pipeline.run_plot(pr, "17_Top_Affiliations", "top_affiliations", log.append)
        self.assertTrue(ok, msg)
        with open(pr.dir / "17_Top_Affiliations" / "17_Top_Affiliations.csv", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        self.assertIn("Chinese Academy of Sciences", [r["Parent Organisation"] for r in rows])
        # subject areas: the sample's made-up source list matches most sources by title; the rest are "Not matched"
        with open(pr.dir / "Subject_Areas" / "Subject_Areas.csv", encoding="utf-8-sig") as f:
            areas = list(csv.DictReader(f))
        self.assertEqual(areas[-1]["Subject Area"], "Not matched (source not in the list)")
        self.assertAlmostEqual(sum(float(r["Share of Assignments (%)"]) for r in areas[:-1]), 100, delta=0.2)
        with open(pr.dir / "Subject_Areas" / "Subject_Areas_papers.csv", encoding="utf-8-sig") as f:
            how = {r["Matched By"] for r in csv.DictReader(f)}
        self.assertEqual(how, {"Source title", "not matched"})
        # without a source list the sheet is skipped, not an error, and Generate all plots goes on
        (pr.dir / "data" / "source_list" / "sample_source_list.csv").rename(TMP / "kept_source_list.csv")
        (pr.dir / "Subject_Areas" / "Subject_Areas.csv").unlink()
        ok, msg = pipeline.run_sheet(pr, "Subject_Areas", log.append)
        self.assertTrue(ok and "skipped" in msg, msg)
        self.assertFalse((pr.dir / "Subject_Areas" / "Subject_Areas.csv").exists())
        ok, msg = pipeline.run_plot(pr, "Subject_Areas", "subject_areas", log.append)
        self.assertTrue(ok and "skipped" in msg, msg)
        # a data set of one search (no Query_IDs): Topic_Slices does not apply and is skipped, so Generate all goes on
        with open(pr.clean_file, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        keep = [c for c in rows[0] if c not in ("Query_IDs", "N_Queries")]
        with open(pr.clean_file, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keep, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        for old in (pr.dir / "Topic_Slices").glob("Topic_Slices*.csv"):
            old.unlink()
        ok, msg = pipeline.run_sheet(pr, "Topic_Slices", log.append)
        self.assertTrue(ok and "skipped" in msg, msg + "\n" + "\n".join(log[-5:]))
        ok, msg = pipeline.run_sheet(pr, "23_Top_Cited", log.append)          # the sheet after it in the menu still runs
        self.assertTrue(ok, msg)
        # a failure is explained in plain words
        (pr.dir / "Affiliations" / "Affiliations.csv").write_text("EID\n1\n", encoding="utf-8")
        ok, msg = pipeline.run_sheet(pr, "17_Top_Affiliations", log.append)
        self.assertFalse(ok)
        self.assertIn("missing", msg)


if __name__ == "__main__":
    unittest.main()
