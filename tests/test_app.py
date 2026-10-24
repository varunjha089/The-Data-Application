"""Tests of The Data Application. They never touch your settings or projects: everything happens in a temporary folder.

    python -m unittest discover -s tests -v                 everything (needs a Python with pandas, numpy and matplotlib: the full run takes 2-3 minutes)
    TDA_QUICK=1 python -m unittest discover -s tests -v     only the fast tests (the standard library is enough)

The full run makes the sample project (made-up data, app/sample.py), cleans it, generates every sheet and every plot, and checks that each file
the application lists was written, that the run records exist, and that the plot-look wrapper writes PDF and TIFF files.
"""
import csv
import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from datetime import date
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="tda_test_"))
os.environ["THE_DATA_APP_HOME"] = str(TMP / "appdata")          # before the application is imported: its settings go to the temporary folder
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "steps" / "common"))

from app import dataset, look, pipeline, project as projects, sample, sheets, years  # noqa: E402
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
    def test_look(self):
        pr = new_project("Look test")
        self.assertEqual(look.args(pr), [])                                # the defaults: the plot script runs on its own
        look.save(pr, {"text": 9, "palette": "colourblind", "pdf": True, "dpi": 123})
        lk = look.get(pr)
        self.assertEqual((lk["text"], lk["dpi"], lk["palette"]), (2.5, 0, "colourblind"))      # clipped and checked
        self.assertEqual(look.args(pr), ["--text", "2.5", "--formats", "pdf", "--palette", "colourblind"])

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
        finally:
            app.httpd.shutdown()


@unittest.skipIf(os.environ.get("TDA_QUICK") or not have_science(), "full run skipped (TDA_QUICK set, or this Python has no pandas/numpy/matplotlib)")
class FullRun(unittest.TestCase):
    """the sample project from the export to every plot, with the Python that runs the tests as the project's Python"""

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
        for ext in ("png", "svg", "pdf", "tif"):
            self.assertTrue((pr.dir / "03_Annual_Production" / f"annual_production.{ext}").exists(), ext)
        # counting by parent organisation
        sheets.save_options(pr, "17_Top_Affiliations", {"by": "parent"})
        ok, msg = pipeline.run_plot(pr, "17_Top_Affiliations", "top_affiliations", log.append)
        self.assertTrue(ok, msg)
        with open(pr.dir / "17_Top_Affiliations" / "17_Top_Affiliations.csv", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        self.assertIn("Chinese Academy of Sciences", [r["Parent Organisation"] for r in rows])
        # a failure is explained in plain words
        (pr.dir / "Affiliations" / "Affiliations.csv").write_text("EID\n1\n", encoding="utf-8")
        ok, msg = pipeline.run_sheet(pr, "17_Top_Affiliations", log.append)
        self.assertFalse(ok)
        self.assertIn("missing", msg)


if __name__ == "__main__":
    unittest.main()
