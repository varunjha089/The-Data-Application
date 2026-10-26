"""Report: write the results chapter of the project as LaTeX, one file per figure and per table, the analysis written by an AI model (or left open).

Every figure and table gets three paragraphs:
  1. what the plot or table is, why it matters and its limitation: the same for every study, so it is taken from about.json (never asked from a model);
  2. the analysis of this study's numbers, and 3. a short conclusion: asked from the model you chose (Anthropic Claude or Google Gemini), as JSON.
The model gets only the summary tables of the sheet (the first rows of its CSV files), the notes its scripts printed, the main information of the
data set and, if you choose, the plot picture. The raw export is never sent. The API key comes from the environment variable TDA_AI_KEY (the
application passes it; it is never written to a file, an argument or a log).

Your edits are safe: report_manifest.json keeps the SHA-256 of every file this script wrote. A file you changed is never written again, a file you
deleted stays deleted (the application unticks it), and a file whose data, model and text are unchanged is kept without asking the model again.
Every number in the model's text is looked up in the data it was given; numbers not found there (often a sum or a ratio the model computed) are
listed in report_check.txt and in a "% CHECK" line at the top of the file, so you can verify them.

Input : report_items.json (written by the application: the figures and tables you ticked, in order), about.json (next to this script),
        the sheets' CSV files, logs and plot pictures in the project folder (the folder above this one)
Output: results/<item>.tex, figures/<plot>.png, results_chapter.tex (includes only the files that exist), report_info.tex, report_manifest.json,
        report_status.json, report_check.txt
Run   : python3 make_report.py [--provider anthropic|gemini|none] [--model ID] [--images] [--rewrite]
        (--provider none writes paragraph 1 and leaves the analysis open; needs pandas)
"""
import argparse
import base64
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent                       # <project>/Report
PROJECT = HERE.parent
RESULTS, FIGURES = HERE / "results", HERE / "figures"
MANIFEST, STATUS, CHECK = HERE / "report_manifest.json", HERE / "report_status.json", HERE / "report_check.txt"
PROMPT_VERSION = "1"                                         # raise when the prompt changes: the items are then written again
ANTHROPIC_URL = os.environ.get("THE_DATA_APP_ANTHROPIC_URL", "https://api.anthropic.com").rstrip("/")
GEMINI_URL = os.environ.get("THE_DATA_APP_GEMINI_URL", "https://generativelanguage.googleapis.com").rstrip("/")
FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-1"}    # accept the server-side refusal fallback
SCHEMA = {"type": "object", "properties": {"analysis": {"type": "string"}, "conclusion": {"type": "string"}},
          "required": ["analysis", "conclusion"], "additionalProperties": False}
UNICODE = {"β": r"$\beta$", "α": r"$\alpha$", "γ": r"$\gamma$", "μ": r"$\mu$", "×": r"$\times$", "±": r"$\pm$", "≈": r"$\approx$",
           "≤": r"$\leq$", "≥": r"$\geq$", "−": "-", "→": r"$\rightarrow$", "²": r"$^2$", "³": r"$^3$", "°": r"$^{\circ}$"}
SYSTEM = """You write one part of the results chapter of a scientometric (bibliometric) study, for a thesis or a journal article.
For one figure or table you get: the paragraph that is already written before it (what this kind of figure or table is; do not repeat it),
the data behind it, and the main numbers of the data set. Write two things:

analysis: one paragraph of 90 to 160 words that reads this figure or table for this study. Name the leading items with their exact numbers,
compare them, and point out patterns, exceptions and changes over time. Use only numbers that appear in the data you were given, or simple
results of them (a sum, a difference, a ratio); never invent a number, a name or a cause. Mention the figure or table once by writing [REF]
where "Figure 4.3" or "Table 4.3" would stand, for example "(see [REF])" or "As [REF] shows".
conclusion: two to four sentences (35 to 70 words) on what this means for the field. No new numbers.

Style: plain academic English, no headings, no lists, no markdown except *asterisks* around journal or book titles, no LaTeX commands.
Numbers with at most two decimals; write percentages as 12.5%. Use the names exactly as they appear in the data.
Answer with JSON only: {"analysis": "...", "conclusion": "..."}"""


class Fatal(Exception):
    """a problem that stops the whole run (wrong key, unknown model)"""


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def esc(text):
    """plain text -> LaTeX (special characters escaped, a few symbols as math, characters pdflatex cannot set replaced)"""
    out = []
    for ch in str(text):
        if ch in "\\":
            out.append(r"\textbackslash{}")
        elif ch in "&%$#_{}":
            out.append("\\" + ch)
        elif ch == "~":
            out.append(r"\textasciitilde{}")
        elif ch == "^":
            out.append(r"\textasciicircum{}")
        elif ch in UNICODE:
            out.append(UNICODE[ch])
        elif ord(ch) < 256 or ch in "\u2013\u2014\u2018\u2019\u201c\u201d\u2026":
            out.append(ch)
        else:
            out.append("?")
    return "".join(out)


def about_tex(text):
    """the application's own paragraph: formulas between $...$ are kept as LaTeX, the rest is escaped"""
    return "".join(p if i % 2 else esc(p) for i, p in enumerate(re.split(r"(\$[^$]+\$)", text)))


def prose(text, ref, add_ref=True):
    """the model's plain text -> LaTeX: escaped, *title* in italics, [REF] -> Figure~\\ref{...} (added after the first sentence if missing and add_ref)"""
    text = re.sub(r"\s+", " ", str(text)).strip()
    if add_ref and "[REF]" not in text:
        text = re.sub(r"^(.+?)([.!?])(\s|$)", lambda m: m.group(1) + " ([REF])" + m.group(2) + m.group(3), text, count=1)
    parts = re.split(r"(\*[^*]+\*|\[REF\])", text)
    out = []
    for p in parts:
        if p == "[REF]":
            out.append(ref)
        elif len(p) > 2 and p.startswith("*") and p.endswith("*"):
            out.append(r"\emph{" + esc(p[1:-1]) + "}")
        else:
            out.append(esc(p))
    return "".join(out)


# ------------------------------------------------------------------------------------------------------------------ the data a model is given
def csv_text(path, rows):
    """header and the first rows of a CSV as text (long cells shortened), and the number of rows"""
    with open(path, newline="", encoding="utf-8-sig") as f:
        data = list(csv.reader(f))
    head, body = (data[0], data[1:]) if data else ([], [])
    show = [[c if len(c) <= 90 else c[:87] + "..." for c in r] for r in [head] + body[:rows]]
    buf = []
    for r in show:
        buf.append(",".join('"' + c.replace('"', "'") + '"' if "," in c else c for c in r))
    return "\n".join(buf), len(body)


def log_notes(sheet_dir, sheet):
    """what the sheet's scripts printed (results such as fitted parameters), without the command lines and 'written ...' lines"""
    notes = []
    for name in (f"{sheet}_log.txt", f"{sheet}_plot_log.txt"):
        p = sheet_dir / name
        if not p.exists():
            continue
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        if any(l.startswith("-----") for l in lines):
            lines = lines[next(i for i, l in enumerate(lines) if l.startswith("-----")) + 1:]
        notes += [l.rstrip() for l in lines if l.strip() and not l.startswith(("$", "written", "(table pictures"))]
    return notes[:40]


def context(item, main_info):
    """the text the model reads for one item"""
    sheet_dir = PROJECT / item["sheet"]
    blocks = []
    files = [item["file"]] if item["kind"] == "tab" else item.get("csvs", [])
    for c in files[:4]:
        p = sheet_dir / c
        if p.exists() and p.suffix == ".csv":
            text, n = csv_text(p, 40 if item["kind"] == "tab" else 25)
            blocks.append(f"Table {c} ({min(n, 40 if item['kind'] == 'tab' else 25)} of {n} rows shown):\n{text}")
    notes = log_notes(sheet_dir, item["sheet"])
    if notes:
        blocks.append("Notes printed by the scripts of this sheet:\n" + "\n".join(notes))
    return "\n\n".join(blocks)


# ------------------------------------------------------------------------------------------------------------------ the models
def http_json(url, body, headers, timeout=600):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json", **headers}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def call(fn, *a):
    """fn with retries for rate limits, overload and lost connections; a wrong key or model stops the run"""
    for attempt in range(5):
        try:
            return fn(*a)
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:600]
            if e.code in (401, 403) or (e.code == 400 and "API key" in msg):
                raise Fatal("The API key was refused (HTTP %d). Check the key in Settings, AI writing." % e.code)
            if e.code == 404:
                raise Fatal("The model was not found (HTTP 404). Choose another model in Settings, AI writing. " + msg[:200])
            if e.code in (408, 409, 429, 500, 502, 503, 504, 529) and attempt < 4:
                wait = float(e.headers.get("retry-after") or 0) or 5 * 2 ** attempt
                print(f"   the provider is busy (HTTP {e.code}); trying again in {wait:.0f} s")
                time.sleep(min(wait, 90))
                continue
            raise RuntimeError(f"HTTP {e.code}: {msg}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt < 4:
                print(f"   no answer ({e}); trying again in {5 * 2 ** attempt} s")
                time.sleep(5 * 2 ** attempt)
                continue
            raise Fatal(f"The provider cannot be reached: {e}. Is there an internet connection?")


def parse_answer(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\s*|\s*```$", "", text)
    m = re.search(r"\{.*\}", text, re.S)
    data = json.loads(m.group(0) if m else text)
    if not str(data.get("analysis", "")).strip() or not str(data.get("conclusion", "")).strip():
        raise RuntimeError("the answer had no analysis or no conclusion")
    return data


def ask_anthropic(model, key, user_text, image):
    content = []
    if image is not None:
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(image).decode("ascii")}})
    content.append({"type": "text", "text": user_text})
    body = {"model": model, "max_tokens": 16000, "system": SYSTEM, "messages": [{"role": "user", "content": content}],
            "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}}}
    headers = {"x-api-key": key, "anthropic-version": "2026-10-21"}
    if model in FALLBACK_MODELS:                             # on a refusal the server answers with a fallback model instead of stopping
        body["fallbacks"] = "default"
        headers["anthropic-beta"] = "server-side-fallback-2026-07-01"
    for _ in range(3):
        try:
            r = call(http_json, ANTHROPIC_URL + "/v1/messages", body, headers)
            break
        except RuntimeError as e:                            # an older model that does not know a field: send the request without it
            s = str(e)
            if "fallback" in s and "fallbacks" in body:
                body.pop("fallbacks"), headers.pop("anthropic-beta", None)
            elif ("output_config" in s or "json_schema" in s or "format" in s) and "output_config" in body:
                body.pop("output_config")
            else:
                raise
    else:
        raise RuntimeError("the request was refused three times")
    if r.get("stop_reason") == "refusal":
        raise RuntimeError("the model declined to write this part (refusal)")
    if r.get("stop_reason") == "max_tokens":
        raise RuntimeError("the answer was cut off (max_tokens)")
    text = "".join(b.get("text", "") for b in r.get("content", []) if b.get("type") == "text")
    u = r.get("usage") or {}
    return parse_answer(text), (u.get("input_tokens", 0), u.get("output_tokens", 0))


def ask_gemini(model, key, user_text, image):
    parts = [{"text": user_text}]
    if image is not None:
        parts.insert(0, {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(image).decode("ascii")}})
    body = {"systemInstruction": {"parts": [{"text": SYSTEM}]}, "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": {
                "type": "OBJECT", "properties": {"analysis": {"type": "STRING"}, "conclusion": {"type": "STRING"}}, "required": ["analysis", "conclusion"]}}}
    r = call(http_json, f"{GEMINI_URL}/v1beta/models/{model}:generateContent", body, {"x-goog-api-key": key})
    cands = r.get("candidates") or []
    if not cands:
        raise RuntimeError("no answer (blocked: %s)" % ((r.get("promptFeedback") or {}).get("blockReason") or "unknown"))
    if cands[0].get("finishReason") not in (None, "STOP"):
        raise RuntimeError("the answer stopped early (%s)" % cands[0].get("finishReason"))
    text = "".join(p.get("text", "") for p in (cands[0].get("content") or {}).get("parts", []))
    u = r.get("usageMetadata") or {}
    return parse_answer(text), (u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0))


# ------------------------------------------------------------------------------------------------------------------ the number check
NUM = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")


def numbers(text):
    out = []
    for t in NUM.findall(text):
        t2 = t.replace(",", "") if re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", t) else t.split(",")[0]
        try:
            out.append((t, float(t2), len(t2.split(".")[1]) if "." in t2 else 0))
        except ValueError:
            pass
    return out


def unchecked(text, source):
    """the numbers of the model's text that are not in the data it was given (also after rounding)"""
    known = [v for _, v, _ in numbers(source)]
    bad = []
    for t, v, d in numbers(text):
        if d == 0 and abs(v) <= 12:                          # small counts ("2 of the 10")
            continue
        tol = 0.5 * 10 ** -d + 1e-9
        if not any(abs(k - v) <= tol for k in known) and not any(abs(k * 100 - v) <= tol for k in known if 0 < k <= 1):
            bad.append(t)
    return list(dict.fromkeys(bad))


# ------------------------------------------------------------------------------------------------------------------ figures and tables
def fmt_cell(col, v, whole):
    if pd.isna(v):
        return "--"
    if isinstance(v, float):
        return f"{v:,.0f}" if col in whole else f"{v:,.2f}"
    if isinstance(v, (int,)) or (hasattr(v, "dtype") and str(getattr(v, "dtype", "")).startswith("int")):
        low = col.lower()
        return str(v) if ("year" in low or low in ("begin", "end", "rank", "py start") or re.fullmatch(r"\d{4}", col)) else f"{int(v):,}"
    return esc(v)


def table_tex(item, spec):
    d = pd.read_csv(PROJECT / item["sheet"] / item["file"], encoding="utf-8-sig", keep_default_na=False, na_values=[""])
    if spec.get("query"):
        d = d.query(spec["query"])
    if spec.get("cols"):
        d = d[[c for c in spec["cols"] if c in d.columns]]
    d = d.drop(columns=[c for c in spec.get("drop", []) if c in d.columns])
    if spec.get("first") in d.columns:
        d = d[[spec["first"]] + [c for c in d.columns if c != spec["first"]]]
    if d.shape[1] > 13:                                      # a long year table: the first column, the most recent years and the total
        d = d[[d.columns[0]] + list(d.columns[-12:])]
    rows = int(item.get("rows") or spec.get("n", 15)) if item.get("rows") != 0 else 1000     # the sheet's own number of rows, if you set one
    d = d.head(rows).rename(columns=spec.get("rename", {}))
    whole = {c for c in d.columns if pd.api.types.is_float_dtype(d[c]) and d[c].dropna().map(float.is_integer).all()}
    text_cols = [not pd.api.types.is_numeric_dtype(d[c]) for c in d.columns]
    colspec = spec.get("spec") or "".join(r">{\raggedright\arraybackslash}X" if t else "r" for t in text_cols)
    if "X" not in colspec:
        colspec = r">{\raggedright\arraybackslash}X" + colspec[1:]
    size = r"\small" if d.shape[1] <= 5 else (r"\footnotesize" if d.shape[1] <= 7 else r"\scriptsize")
    head = " & ".join(r"\textbf{" + esc(c) + "}" for c in d.columns)
    rows = "\n".join("        " + " & ".join(fmt_cell(c, v, whole) for c, v in zip(d.columns, r)) + r" \\" for r in d.itertuples(index=False, name=None))
    return (f"\\begin{{table}}[H]\n    \\centering\n    {size}\n    \\caption{{{esc(spec['title'])}}}\n    \\label{{tab:{item['stem']}}}\n"
            f"    \\begin{{tabularx}}{{\\textwidth}}{{{colspec}}}\n        \\toprule\n        {head} \\\\\n        \\midrule\n{rows}\n"
            f"        \\bottomrule\n    \\end{{tabularx}}\n\\end{{table}}\n")


def figure_tex(item, spec):
    src = PROJECT / item["sheet"] / f"{item['file']}.png"      # copied into Report/figures by main(): the folder can be built or sent on its own
    return (f"\\begin{{figure}}[H]\n    \\centering\n    \\includegraphics[width=\\textwidth,height=0.62\\textheight,keepaspectratio]{{figures/{src.name}}}\n"
            f"    \\caption{{{esc(spec['title'])}.}}\n    \\label{{fig:{item['stem']}}}\n\\end{{figure}}\n")


def main():
    ap = argparse.ArgumentParser(description="Report: write the results chapter as LaTeX")
    ap.add_argument("--provider", choices=["anthropic", "gemini", "none"], default="none")
    ap.add_argument("--model", default="")
    ap.add_argument("--images", action="store_true", help="also send the plot picture to the model")
    ap.add_argument("--rewrite", action="store_true", help="ask the model again even when nothing has changed")
    args = ap.parse_args()
    key = os.environ.get("TDA_AI_KEY", "")
    if args.provider != "none" and (not key or not args.model):
        print("SKIPPED: no API key or no model was given. Set them in Settings, AI writing, or write without AI.")
        return 2
    cfg = load_json(HERE / "report_items.json", {})
    about = load_json(Path(__file__).with_name("about.json"), {})
    items = cfg.get("items", [])
    if not items:
        print("SKIPPED: no figure or table is ticked. Tick them on the Report page.")
        return 0
    RESULTS.mkdir(exist_ok=True)
    manifest, status, checks = load_json(MANIFEST, {}), {}, []
    main_csv = PROJECT / "02_Main_Information" / "02_Main_Information.csv"
    main_info = csv_text(main_csv, 60)[0] if main_csv.exists() else ""
    study = cfg.get("study") or cfg.get("project", "")
    model_id = "none" if args.provider == "none" else f"{args.provider}:{args.model}"
    ask = {"anthropic": ask_anthropic, "gemini": ask_gemini}.get(args.provider)
    used = [0, 0]
    root = cfg.get("main", "report.tex")
    print(f"{len(items)} figures and tables; writer: {'no AI (paragraph 1 only)' if ask is None else args.provider + ' ' + args.model}"
          f"{', with the plot pictures' if args.images and ask else ''}")

    for it in items:
        stem, kind = it["stem"], it["kind"]
        spec = about.get(("plot:" + it["file"]) if kind == "fig" else ("table:" + it["file"]))
        if spec is None:
            spec = {"title": it.get("title", stem), "about": it.get("what", "")}
        src = PROJECT / it["sheet"] / (f"{it['file']}.png" if kind == "fig" else it["file"])
        out = RESULTS / f"{stem}.tex"
        if not src.exists():
            status[stem] = {"state": "missing", "note": f"{it['sheet']}/{src.name} does not exist yet: generate it first"}
            print(f"-- {stem}: skipped, {src.name} has not been generated yet")
            continue
        if kind == "fig":                                    # the picture is always the current one, also when the text is kept
            FIGURES.mkdir(exist_ok=True)
            shutil.copy2(src, FIGURES / src.name)
        old = manifest.get(stem)
        if out.exists() and (old is None or sha(out.read_bytes()) != old.get("sha256")):
            status[stem] = {"state": "edited", "note": "changed by you: not written again"}
            print(f"-- {stem}: kept, you edited it")
            continue
        ctx = context(it, main_info)
        image = src.read_bytes() if (kind == "fig" and args.images and ask and src.stat().st_size < 4_500_000) else None
        inputs = sha("\n".join([PROMPT_VERSION, study, spec["about"], ctx, main_info, sha(image) if image else "", sha(src.read_bytes()), str(it.get("rows"))]))
        if out.exists() and old and old.get("inputs") == inputs and old.get("model") == model_id and not args.rewrite:
            status[stem] = {"state": "kept", "note": "unchanged", "check": old.get("check", [])}
            print(f"-- {stem}: unchanged, kept")
            continue
        ref = ("Figure" if kind == "fig" else "Table") + f"~\\ref{{{'fig' if kind == 'fig' else 'tab'}:{stem}}}"
        flagged = []
        if ask is None:
            analysis = r"\textit{[The analysis of this " + ("figure" if kind == "fig" else "table") + " is still to be written.]}"
            conclusion = r"\textit{[The conclusion is still to be written.]}"
        else:
            kind_word = "figure" if kind == "fig" else "table"
            user = (f"Study: {study}\n\nThe {kind_word}: {spec['title']} (sheet: {it.get('sheet_title', it['sheet'])}; {it.get('what', '')})\n\n"
                    f"Paragraph already written before the {kind_word}:\n{spec['about']}\n\n"
                    f"Data behind the {kind_word}:\n{ctx}\n\nMain information of the data set:\n{main_info}")
            print(f"-- {stem}: asking {args.model} ...", flush=True)
            try:
                ans, (n_in, n_out) = call_model(ask, args.model, key, user, image)
            except Fatal as e:
                print(f"STOPPED: {e}")
                save(manifest, status, checks)
                return 2
            except (RuntimeError, ValueError, KeyError) as e:
                status[stem] = {"state": "failed", "note": str(e)[:300]}
                print(f"   failed: {e}")
                continue
            used[0] += n_in
            used[1] += n_out
            flagged = unchecked(ans["analysis"] + " " + ans["conclusion"], ctx + "\n" + main_info + "\n" + spec["about"])
            analysis, conclusion = prose(ans["analysis"], ref), prose(ans["conclusion"], ref, add_ref=False)
        body = figure_tex(it, spec) if kind == "fig" else table_tex(it, spec)
        head = [f"% !TEX root = ../{root}", f"% {'Figure' if kind == 'fig' else 'Table'}: {it['sheet']}/{src.name}   (delete this file to drop it from the report)",
                f"% Written by {model_id} on {date.today().isoformat()}; the first paragraph is the application's own text."]
        if flagged:
            head.append("% CHECK: these numbers are not in the data the model was given (a sum or ratio it computed?): " + ", ".join(flagged))
        text = "\n".join(head) + f"\n\\subsection{{{esc(spec['title'])}}}\n\\label{{sec:{stem}}}\n\n{about_tex(spec['about'])}\n\n{body}\n{analysis}\n\n{conclusion}\n"
        out.write_text(text, encoding="utf-8")
        manifest[stem] = {"sha256": sha(text.encode("utf-8")), "inputs": inputs, "model": model_id, "when": datetime.now().isoformat(timespec="seconds"), "check": flagged}
        status[stem] = {"state": "written", "note": model_id, "check": flagged}
        if flagged:
            checks.append(f"{stem}: {', '.join(flagged)}")
        print(f"   written results/{stem}.tex" + (f" (numbers to check: {', '.join(flagged)})" if flagged else ""))

    write_chapter(cfg, items, root)
    save(manifest, status, checks)
    failed = [s for s, v in status.items() if v["state"] == "failed"]
    n = {k: sum(1 for v in status.values() if v["state"] == k) for k in ("written", "kept", "edited", "missing", "failed")}
    print(f"\nwritten {n['written']}, unchanged {n['kept']}, edited by you {n['edited']}, not generated yet {n['missing']}, failed {n['failed']}")
    if used[0]:
        print(f"tokens used: {used[0]:,} in, {used[1]:,} out")
    if checks:
        print(f"numbers to check in {len(checks)} files: see report_check.txt")
    if failed:
        print("FAILED: " + ", ".join(failed) + " (see report_status.json); press Write again to retry them")
        return 1
    return 0


def call_model(ask, model, key, user, image):
    try:
        return ask(model, key, user, image)
    except ValueError:                                       # an answer that was not JSON: one more try
        return ask(model, key, user + "\n\nAnswer with the JSON object only.", image)


def write_chapter(cfg, items, root):
    """results_chapter.tex: one \\result line per ticked item, under the heading of its group; \\result skips a file you deleted"""
    title = esc(cfg.get("project", "Report"))
    (HERE / "report_info.tex").write_text(f"\\providecommand{{\\reporttitle}}{{{title}}}\n\\providecommand{{\\reportdate}}{{{date.today().strftime('%d %B %Y')}}}\n", encoding="utf-8")
    lines = [f"% !TEX root = {root}", "% Written by make_report.py on every run: change the order or the headings in the application, or copy this file and \\input your copy.",
             r"\providecommand{\result}[1]{\IfFileExists{results/#1.tex}{\input{results/#1}}{}}",
             r"\ifdefined\chapter\chapter{Results and Discussion}\else\section*{Results and Discussion}\fi", r"\label{sec:results}"]
    group = None
    for it in items:
        if it.get("group") != group:
            group = it.get("group")
            if any((RESULTS / f"{x['stem']}.tex").exists() for x in items if x.get("group") == group):
                lines.append(f"\n\\section{{{esc(group)}}}")
        lines.append(f"\\result{{{it['stem']}}}")
    (HERE / "results_chapter.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def save(manifest, status, checks):
    MANIFEST.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    STATUS.write_text(json.dumps({"when": datetime.now().isoformat(timespec="seconds"), "items": status}, indent=1), encoding="utf-8")
    CHECK.write_text(("Numbers in the AI's text that were not found in the data it was given (a sum, difference or ratio it computed, or a mistake).\n"
                      "Check each one against the table of the sheet before you submit.\n\n" + "\n".join(checks) + "\n") if checks else
                     "No number to check: every number in the AI's text was found in the data it was given.\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
