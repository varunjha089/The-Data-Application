"use strict";
// The window of The Data Application. Plain JavaScript, no libraries, no internet needed.
// Two views: the opening screen (create or open a project) and the workspace: a left menu (Overview, Settings, Step 1 Clean data, then one page per sheet)
// and the page that is selected. Every sheet page has its data table and its plot buttons.
const $ = (id) => document.getElementById(id);
let state = null, sheetsInfo = null, polling = null, since = 0, settings = { font: 18, theme: "light" }, projectsInfo = null;
let page = "overview", curCsv = null, curPage = 0, afterJob = null;

async function api(path, body) {
  const opt = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const r = await fetch(path, opt);
  return r.json();
}
function setMsg(id, text, kind) { const e = $(id); if (!e) return; e.textContent = text || ""; e.className = "msg " + (kind || ""); }
function pill(id, text, kind) { const e = $(id); e.textContent = text; e.className = "pill " + (kind || ""); }
function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
function day(t) { return t ? t.replace("T", " ").slice(0, 16) : ""; }
const spec = (name) => (sheetsInfo ? sheetsInfo.sheets.find((s) => s.name === name) : null);

// ---------------------------------------------------------------- look: text size and theme (settings of the application, remembered)
function applyLook() { document.documentElement.style.fontSize = settings.font + "px"; document.documentElement.dataset.theme = settings.theme; }
function saveLook() { applyLook(); api("/api/settings", settings); }
$("font-up").onclick = () => { settings.font = Math.min(30, settings.font + 2); saveLook(); };
$("font-down").onclick = () => { settings.font = Math.max(14, settings.font - 2); saveLook(); };
$("theme").onclick = () => { settings.theme = settings.theme === "dark" ? "light" : "dark"; saveLook(); };

// ---------------------------------------------------------------- views
function show(view) {
  $("welcome").classList.toggle("hidden", view !== "welcome");
  $("workspace").classList.toggle("hidden", view !== "workspace");
  $("switch").classList.toggle("hidden", view !== "workspace");
  $("proj-badge").classList.toggle("hidden", view !== "workspace");
}
async function loadState() {
  state = await api("/api/status");
  sheetsInfo = state.project ? await api("/api/sheets") : null;
}
async function boot(target) {
  await loadState();
  const ui = state.ui || {};
  if (ui.font) settings.font = ui.font;
  settings.theme = ui.theme || (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  applyLook();
  $("folder").textContent = "Application folder: " + state.folder;
  if (!state.project) { await renderWelcome(); show("welcome"); return; }
  show("workspace");
  const p = state.project, needSetup = !p.env.can_clean || !p.data.chosen || !p.data.exists;
  page = target || (needSetup ? "settings" : "overview");
  renderAll();
}
async function refreshAll() { await loadState(); if (state.project) renderAll(); }

// ---------------------------------------------------------------- opening screen
async function renderWelcome() {
  projectsInfo = await api("/api/projects");
  const list = projectsInfo.projects;
  if (!$("new-loc").value) $("new-loc").value = projectsInfo.location;
  showWhere();
  if (!list.length) { $("project-list").innerHTML = '<p class="info">There is no project in the list yet. Create the first one above, or open a project folder below.</p>'; return; }
  $("project-list").innerHTML = list.map((p) => {
    if (!p.exists) {
      return '<div class="project"><div class="grow"><div class="title">' + esc(p.name) + ' <em>(folder not found)</em></div><div class="detail">' + esc(p.path) +
        '</div></div><button data-forget="' + esc(p.path) + '">Remove from list</button></div>';
    }
    const bits = [p.records ? p.records + " records" : "no data yet", p.cleaned ? "cleaned " + day(p.cleaned) : "not cleaned", p.has_python ? "environment set" : "no environment"];
    return '<div class="project"><div class="grow"><div class="title">' + esc(p.name) + (p.path === projectsInfo.last ? " <em>(last opened)</em>" : "") + '</div>' +
      '<div class="detail">' + esc(bits.join("  |  ")) + '</div><div class="detail">' + esc(p.path) + '</div><div class="detail">created ' + esc(day(p.created)) + ", opened " + esc(day(p.opened)) + '</div></div>' +
      '<button class="primary" data-open="' + esc(p.path) + '">Open</button></div>';
  }).join("");
  document.querySelectorAll("[data-open]").forEach((b) => b.onclick = async () => {
    const r = await api("/api/project/open", { path: b.dataset.open });
    if (r.ok) boot(); else setMsg("open-msg", r.message, "bad");
  });
  document.querySelectorAll("[data-forget]").forEach((b) => b.onclick = async () => { await api("/api/project/forget", { path: b.dataset.forget }); renderWelcome(); });
}
function showWhere() {
  const name = $("new-name").value.trim(), loc = $("new-loc").value.trim();
  $("new-where").textContent = name && loc ? "The project folder will be created inside: " + loc : "";
}
$("new-name").oninput = showWhere;
$("new-loc").oninput = showWhere;
$("loc-browse").onclick = async () => {
  const r = await api("/api/browse", { kind: "folder", title: "project" });
  if (r.path) { $("new-loc").value = r.path; showWhere(); } else if (r.error) setMsg("create-msg", r.error, "warn");
};
$("create").onclick = async () => {
  const r = await api("/api/project/create", { name: $("new-name").value, location: $("new-loc").value });
  if (r.ok) { $("new-name").value = ""; setMsg("create-msg", ""); boot("settings"); } else setMsg("create-msg", r.message, "bad");
};
$("new-name").onkeydown = (e) => { if (e.key === "Enter") $("create").click(); };
async function addFolder(path) {
  const r = await api("/api/project/add", { path });
  if (r.ok) boot(); else setMsg("open-msg", r.message, "bad");
}
$("add-browse").onclick = async () => {
  const r = await api("/api/browse", { kind: "folder", title: "existing" });
  if (r.path) { $("add-path").value = r.path; addFolder(r.path); } else if (r.error) setMsg("open-msg", r.error, "warn");
};
$("add-go").onclick = () => addFolder($("add-path").value);
$("switch").onclick = async () => {
  const r = await api("/api/project/close", {});
  if (r.ok) boot(); else setMsg("ov-msg", r.message, "warn");
};

// ---------------------------------------------------------------- the menu on the left (a slider that can be hidden)
$("sb-toggle").onclick = () => $("workspace").classList.toggle("collapsed");
function renderNav() {
  const items = [["Project", [["overview", "Overview", null], ["settings", "Settings", state.project.env.can_clean && state.project.data.exists ? "done" : "stale"]]],
                 ["Step 1", [["clean", "Clean the data", state.project.clean.current ? "done" : (state.project.clean.exists ? "stale" : null)]]]];
  for (const g of sheetsInfo.groups) items.push([g, sheetsInfo.sheets.filter((s) => s.group === g).map((s) => ["sheet:" + s.name, s.title, s.done ? (s.stale ? "stale" : "done") : null])]);
  $("nav").innerHTML = items.map(([title, rows]) => '<div class="nav-title">' + esc(title) + "</div>" +
    rows.map(([id, label, st]) => {
      const mark = (sheetsInfo.bookmarks || {})[id];
      return '<div class="nav-row"><button class="nav-item' + (id === page ? " active" : "") + '" data-page="' + esc(id) + '"><span class="dot-space"></span><span>' + esc(label) + "</span></button>" +
        '<span class="mark" tabindex="0" title="Hover: choose a coloured star to mark this task">' + (mark ? '<span class="star ' + mark + '">&#9733;</span>' : '<span class="dot ' + (st || "") + '"></span>') + "</span>" +
        '<span class="picker" data-id="' + esc(id) + '">' + ["red", "green", "violet", "orange"].map((c) => '<button class="star ' + c + (mark === c ? " on" : "") + '" data-color="' + c + '" title="' + c + ' star">&#9733;</button>').join("") +
        (mark ? '<button class="clear" data-color="" title="remove the star">&times;</button>' : "") + "</span></div>";
    }).join("")).join("");
  document.querySelectorAll(".nav-item").forEach((b) => b.onclick = () => selectPage(b.dataset.page));
  document.querySelectorAll(".nav-row .mark").forEach((m) => m.onclick = () => m.parentElement.classList.toggle("open"));
  document.querySelectorAll(".picker button").forEach((b) => b.onclick = async (e) => {
    e.stopPropagation();
    const id = b.parentElement.dataset.id, now = (sheetsInfo.bookmarks || {})[id], color = b.dataset.color;
    const r = await api("/api/bookmark", { page: id, color: color && color !== now ? color : null });      // the same colour again removes the star
    if (r.bookmarks) { sheetsInfo.bookmarks = r.bookmarks; renderNav(); }
  });
}
function selectPage(p) { if (p !== page) { curCsv = null; curPage = 0; } page = p; history.replaceState(null, "", "#" + p); renderAll(); window.scrollTo(0, 0); }
function renderAll() {
  const p = state.project;
  $("proj-badge").textContent = p.name; $("proj-badge").title = p.dir;
  renderNav();
  const kind = page.startsWith("sheet:") ? "sheet" : page;
  for (const id of ["overview", "settings", "clean", "sheet"]) $("page-" + id).classList.toggle("hidden", id !== kind);
  if (kind === "overview") renderOverview();
  else if (kind === "settings") renderSettings();
  else if (kind === "clean") renderClean();
  else renderSheet(page.slice(6));
}

// ---------------------------------------------------------------- overview
function renderOverview() {
  const p = state.project, ready = p.clean.exists;
  $("ov-notice").classList.toggle("hidden", ready);
  $("ov-notice").innerHTML = ready ? "" : 'The data has not been cleaned yet: do <b>Step 1: Clean the data</b> first. <button id="ov-go-clean">Go to Step 1</button>';
  if (!ready) $("ov-go-clean").onclick = () => selectPage(p.env.can_clean && p.data.exists ? "clean" : "settings");
  $("ov-all").disabled = !ready || !p.env.can_clean;
  $("ov-plots").disabled = !ready || !p.env.can_plot;
  $("ov-plots").title = p.env.can_plot ? "" : "The package matplotlib is missing: Settings, Install the missing packages";
  $("ov-table").innerHTML = "<thead><tr><th>Task</th><th>Group</th><th>Data</th><th>Plot</th><th></th></tr></thead><tbody>" + sheetsInfo.sheets.map((s) => {
    const plotDone = s.plots.length && s.plots.every((pl) => pl.files.every((f) => f.exists));
    return "<tr><td>" + esc(s.title) + "</td><td>" + esc(s.group) + "</td><td>" + (s.done ? (s.stale ? "out of date" : "done " + day(s.made)) : "not generated") + "</td><td>" +
      (s.plots.length ? (plotDone ? "done" : "not generated") : "-") + '</td><td><button data-open="' + esc(s.name) + '">Open</button></td></tr>';
  }).join("") + "</tbody>";
  document.querySelectorAll("#ov-table [data-open]").forEach((b) => b.onclick = () => selectPage("sheet:" + b.dataset.open));
}
$("ov-all").onclick = () => runJob("/api/sheets/run_all", { plots: false }, "ov-msg");
$("ov-plots").onclick = () => runJob("/api/sheets/run_all", { plots: true }, "ov-msg");

// ---------------------------------------------------------------- settings
function renderSettings() {
  const p = state.project, env = p.env, d = p.data;
  $("project-info").innerHTML = "<b>Name:</b> " + esc(p.name) + "<br><b>Folder:</b> <code>" + esc(p.dir) + "</code><br><b>Created:</b> " + esc(day(p.created));
  if (env.ok) { pill("env-pill", "ready", "ok"); $("env-info").innerHTML = "<b>In use:</b> <code>" + esc(env.python) + "</code> (" + esc(env.message) + ")"; }
  else if (env.configured) { pill("env-pill", env.can_clean ? "packages missing" : "problem", env.can_clean ? "warn" : "bad"); $("env-info").innerHTML = "<b>Saved:</b> <code>" + esc(env.python) + "</code> &mdash; " + esc(env.message); }
  else { pill("env-pill", "not set up", "warn"); $("env-info").textContent = env.venv_here ? "A venv from an earlier start exists in this project; choose 'Set up' to use it." : ""; }
  $("env-fix").classList.toggle("hidden", !(env.configured && env.missing && env.missing.length));
  if (d.chosen && d.exists) {
    pill("data-pill", d.records + " records", "ok");
    $("data-info").innerHTML = "<b>Copy:</b> <code>" + esc(d.file) + "</code><br>copied " + esc(day(d.copied)) + (d.original ? "<br><b>Original:</b> " + esc(d.original) : "");
  } else if (d.chosen) { pill("data-pill", "copy missing", "bad"); $("data-info").textContent = "The copy " + d.file + " is gone: choose the file again."; }
  else { pill("data-pill", "none chosen", "warn"); $("data-info").textContent = ""; }
  fillOtherVenvs();
}
function envMode() { return document.querySelector("input[name=env]:checked").value; }
document.querySelectorAll("input[name=env]").forEach((r) => r.onchange = () => {
  $("use-box").classList.toggle("hidden", envMode() !== "use");
  $("other-box").classList.toggle("hidden", envMode() !== "other");
});
async function fillOtherVenvs() {
  const info = await api("/api/projects");
  const others = info.projects.filter((p) => p.path !== state.project.path && p.python_abs);
  $("other-choice").classList.toggle("hidden", !others.length);
  $("other-venv").innerHTML = others.map((p) => '<option value="' + esc(p.python_abs) + '">' + esc(p.name) + "</option>").join("");
}
$("browse").onclick = async () => {
  const r = await api("/api/browse", { kind: "folder" });
  if (r.path) $("venv-path").value = r.path; else if (r.error) setMsg("env-msg", r.error, "warn");
};
async function useVenv(path, install) {
  const r = await api("/api/env/use", { path, install });
  if (r.started) return startPolling("env-msg");
  setMsg("env-msg", r.message, r.ok ? "ok" : (r.needs_install ? "warn" : "bad"));
  $("env-install").classList.toggle("hidden", !r.needs_install);
  if (r.ok) refreshAll();
}
$("env-go").onclick = async () => {
  setMsg("env-msg", "");
  if (envMode() === "create") await runJob("/api/env/create", {}, "env-msg");
  else if (envMode() === "use") await useVenv($("venv-path").value, false);
  else await useVenv($("other-venv").value, false);
};
$("env-install").onclick = () => useVenv(envMode() === "use" ? $("venv-path").value : $("other-venv").value, true);
$("env-fix").onclick = () => runJob("/api/env/install", {}, "env-msg");
$("choose").onclick = () => $("file").click();
$("file").onchange = async () => {
  const f = $("file").files[0];
  if (!f) return;
  setMsg("data-msg", "Copying " + f.name + " (" + (f.size / 1048576).toFixed(1) + " MB) ...", "warn");
  setBusy(true);
  try {
    const r = await (await fetch("/api/data/upload?name=" + encodeURIComponent(f.name), { method: "POST", body: f })).json();
    setMsg("data-msg", r.message, r.ok ? "ok" : "bad");
  } catch (e) { setMsg("data-msg", "The copy failed: " + e, "bad"); }
  $("file").value = "";
  await refreshAll();
  setBusy(false);
};
$("open-raw").onclick = () => api("/api/open", { which: "raw" });
$("open-project").onclick = () => api("/api/open", { which: "project" });

// ---------------------------------------------------------------- step 1: clean data
function renderClean() {
  const p = state.project, env = p.env, d = p.data, c = p.clean;
  const missing = [];
  if (!env.can_clean) missing.push("the Python environment");
  if (!d.chosen || !d.exists) missing.push("the main data");
  $("clean-needs").classList.toggle("hidden", !missing.length);
  $("clean-needs").innerHTML = missing.length ? "Before cleaning, set up " + missing.join(" and ") + ' in <b>Settings</b>. <button id="goto-settings">Go to Settings</button>' : "";
  if (missing.length) $("goto-settings").onclick = () => selectPage("settings");
  if (c.exists && c.current) { pill("clean-pill", "done", "ok"); $("clean-info").textContent = "Made " + day(c.made) + ". Results and log are in the project's folder 01_Clean_Data."; }
  else if (c.exists) { pill("clean-pill", "out of date", "warn"); $("clean-info").textContent = "The cleaned file belongs to an earlier main data: clean again."; }
  else { pill("clean-pill", "not done", "warn"); $("clean-info").textContent = ""; }
  $("dl-csv").classList.toggle("hidden", !c.exists);
  $("dl-report").classList.toggle("hidden", !c.exists);
  $("dl-log").classList.toggle("hidden", !c.log);
  $("open-clean").classList.toggle("hidden", !c.exists && !c.log);
  $("clean").disabled = missing.length > 0;
  if (c.exists) loadResult(); else $("result").classList.add("hidden");
}
async function loadResult() {
  const [rep, pv] = await Promise.all([api("/api/report"), api("/api/preview")]);
  $("report").textContent = rep.text || "";
  if (pv.exists) {
    $("preview-note").textContent = "(" + pv.rows.length + " of " + pv.total + " papers, " + pv.columns.length + " of " + pv.all_columns + " columns; the CSV has all)";
    $("preview").innerHTML = "<thead><tr>" + pv.columns.map((x) => "<th>" + esc(x) + "</th>").join("") + "</tr></thead><tbody>" +
      pv.rows.map((r) => "<tr>" + r.map((x) => "<td>" + esc(x) + "</td>").join("") + "</tr>").join("") + "</tbody>";
    $("result").classList.remove("hidden");
  }
}
$("clean").onclick = () => runJob("/api/clean", {}, "clean-msg");
$("open-clean").onclick = () => api("/api/open", { which: "clean" });

// ---------------------------------------------------------------- one sheet: data table and plot buttons
function renderSheet(name) {
  const s = spec(name), p = state.project;
  if (!s) { selectPage("overview"); return; }
  $("sh-title").textContent = s.title;
  $("sh-what").textContent = s.what + (s.needs.length ? "  Needs: " + s.needs.map((n) => (spec(n) || { title: n }).title).join(", ") + "." : "");
  const notes = [];
  if (!sheetsInfo.clean_ready) notes.push('Clean the data first (<a href="#clean" id="sh-go-clean">Step 1</a>).');
  else if (!p.env.can_clean) notes.push('The Python environment needs setting up (<a href="#settings" id="sh-go-settings">Settings</a>).');
  if (s.plots.length && !p.env.can_plot && p.env.configured) notes.push('Plots need the package matplotlib: <a href="#settings" id="sh-go-settings2">Settings, Install the missing packages</a>.');
  $("sh-notice").classList.toggle("hidden", !notes.length);
  $("sh-notice").innerHTML = notes.join("<br>");
  for (const [id, target] of [["sh-go-clean", "clean"], ["sh-go-settings", "settings"], ["sh-go-settings2", "settings"]]) if ($(id)) $(id).onclick = (e) => { e.preventDefault(); selectPage(target); };
  const canRun = sheetsInfo.clean_ready && p.env.can_clean;
  pill("sh-pill", s.done ? (s.stale ? "out of date" : "generated") : "not generated", s.done ? (s.stale ? "warn" : "ok") : "warn");
  $("sh-info").textContent = s.done ? "Data generated " + day(s.made) + (s.stale ? " (the cleaned data is newer: generate again)." : ".") : "";
  $("sh-run").textContent = s.done ? "Generate the data again" : "Generate data";
  $("sh-run").disabled = !canRun;
  $("sh-run").onclick = () => runJob("/api/sheet/run", { name }, "sh-msg");
  s.options = s.options || [];                      // an older server process sends no options
  $("sh-options").classList.toggle("hidden", !s.options.length);
  $("sh-options").innerHTML = s.options.length ? "<b>Your choices</b> (saved in this project until you change them)<br>" + s.options.map((o) => "<label>" + esc(o.label) + " " + (o.kind === "number" ?
    '<input type="number" data-opt="' + esc(o.id) + '" min="' + o.min + '" max="' + o.max + '" step="' + (o.step || 1) + '" value="' + o.value + '" style="width:5em">' :
    '<input type="checkbox" data-opt="' + esc(o.id) + '"' + (o.value ? " checked" : "") + ">") + "</label>").join("<br>") + ' <span id="sh-opt-msg" class="msg"></span>' : "";
  document.querySelectorAll("#sh-options [data-opt]").forEach((el) => el.onchange = async () => {
    const values = {};
    document.querySelectorAll("#sh-options [data-opt]").forEach((x) => values[x.dataset.opt] = x.type === "checkbox" ? x.checked : Number(x.value));
    const r = await api("/api/sheet/options", { name, values });
    s.options.forEach((o) => { if (r.values) o.value = r.values[o.id]; });
    if (r.values) document.querySelectorAll("#sh-options [data-opt]").forEach((x) => { if (x.type === "checkbox") x.checked = r.values[x.dataset.opt]; else x.value = r.values[x.dataset.opt]; });
    setMsg("sh-opt-msg", r.values ? "saved: generate the data or the plot to use it" : (r.error || "not saved"), r.values ? "ok" : "bad");
  });
  $("sh-plot-buttons").innerHTML = s.plots.map((pl) => '<button data-plot="' + esc(pl.id) + '"' + (canRun && p.env.can_plot ? "" : " disabled") + ">" +
    (pl.files.every((f) => f.exists) ? "Generate the plot again: " : "Generate plot: ") + esc(pl.title) + "</button>").join(" ");
  document.querySelectorAll("#sh-plot-buttons [data-plot]").forEach((b) => b.onclick = () => runJob("/api/sheet/plot", { name, plot: b.dataset.plot }, "sh-msg"));
  const stamp = "?v=" + Date.now();
  $("sh-plots-title").classList.toggle("hidden", !s.plots.some((pl) => pl.files.some((f) => f.exists)));
  $("sh-plots").innerHTML = '<div class="plots">' + s.plots.map((pl) => pl.files.filter((f) => f.exists).map((f) =>
    '<div class="plot"><img src="/files/' + esc(name) + "/" + esc(f.name) + ".png" + stamp + '" alt="' + esc(pl.title) + '"><div class="caption">' + esc(pl.title) +
    ' &nbsp; <a href="/files/' + esc(name) + "/" + esc(f.name) + '.png?download=1">PNG</a><a href="/files/' + esc(name) + "/" + esc(f.name) + '.svg?download=1">SVG</a></div></div>').join("")).join("") + "</div>";
  $("sh-explain").classList.toggle("hidden", !s.explain);
  $("sh-explain").innerHTML = s.explain || "";
  const first = s.csvs[0];
  $("sh-dl").classList.toggle("hidden", !first.exists);
  $("sh-dl").href = "/files/" + name + "/" + first.file + "?download=1";
  $("sh-downloads").innerHTML = (s.downloads || []).filter((d) => d.exists).map((d) => '<a class="button" href="/files/' + esc(name) + "/" + esc(d.file) + '?download=1">' + esc(d.label) + "</a>").join(" ");
  $("sh-dl-log").classList.toggle("hidden", !s.log);
  $("sh-dl-log").href = "/files/" + name + "/" + name + "_log.txt?download=1";
  $("sh-folder").classList.toggle("hidden", !s.done);
  $("sh-folder").onclick = () => api("/api/open", { sheet: name });
  $("sh-data").classList.toggle("hidden", !s.done);
  if (s.done) {
    $("sh-csvs").innerHTML = s.csvs.filter((c) => c.exists).map((c) => '<button class="tabbtn" data-csv="' + esc(c.file) + '">' + esc(c.file.replace(".csv", "")) + " (" + c.rows + " rows)</button>").join(" ");
    document.querySelectorAll("#sh-csvs [data-csv]").forEach((b) => b.onclick = () => { curCsv = b.dataset.csv; curPage = 0; loadTable(name); });
    if (!curCsv || !s.csvs.some((c) => c.file === curCsv)) curCsv = first.file;
    loadTable(name);
  }
}
async function loadTable(name) {
  const t = await api("/api/sheet/table?name=" + encodeURIComponent(name) + "&csv=" + encodeURIComponent(curCsv) + "&page=" + curPage + "&size=50");
  document.querySelectorAll("#sh-csvs .tabbtn").forEach((b) => b.classList.toggle("active", b.dataset.csv === curCsv));
  if (!t.exists) { $("sh-table").innerHTML = ""; return; }
  $("sh-total").textContent = "(" + t.total + " rows, " + t.columns.length + " columns)";
  $("sh-table").innerHTML = "<thead><tr>" + t.columns.map((x) => "<th>" + esc(x) + "</th>").join("") + "</tr></thead><tbody>" +
    t.rows.map((r) => "<tr>" + r.map((x) => "<td>" + esc(x) + "</td>").join("") + "</tr>").join("") + "</tbody>";
  const pages = Math.max(1, Math.ceil(t.total / t.size));
  $("sh-pager").className = "row pager" + (pages > 1 ? "" : " hidden");
  $("sh-pager").innerHTML = '<button id="pg-prev"' + (curPage === 0 ? " disabled" : "") + '>Previous</button> page ' + (curPage + 1) + " of " + pages + ' <button id="pg-next"' + (curPage + 1 >= pages ? " disabled" : "") + ">Next</button>";
  $("pg-prev").onclick = () => { curPage--; loadTable(name); };
  $("pg-next").onclick = () => { curPage++; loadTable(name); };
}

// ---------------------------------------------------------------- jobs (set-up, install, clean, sheets, plots): poll the log while one runs
const BUSY_BUTTONS = ["env-go", "env-install", "env-fix", "browse", "choose", "clean", "switch", "ov-all", "ov-plots", "sh-run"];
function setBusy(busy) { for (const id of BUSY_BUTTONS) if ($(id)) $(id).disabled = busy; document.querySelectorAll("#sh-plot-buttons button").forEach((b) => b.disabled = busy); }
async function runJob(url, body, msgId) {
  setMsg(msgId, "");
  const r = await api(url, body);
  if (r.started) startPolling(msgId); else setMsg(msgId, "Another task is still running.", "warn");
}
function startPolling(msgId) {
  since = 0; $("log").textContent = ""; pill("job-pill", "running", "busy"); setBusy(true);
  polling = setInterval(async () => {
    const j = await api("/api/job?since=" + since);
    if (j.log.length) { $("log").textContent += j.log.join("\n") + "\n"; $("log").scrollTop = $("log").scrollHeight; since = j.next; }
    $("job-pill").textContent = "running " + j.seconds + " s";
    if (j.state !== "running") {
      clearInterval(polling); polling = null;
      const ok = j.state === "done";
      pill("job-pill", ok ? "finished" : "stopped", ok ? "ok" : "bad");
      setMsg(msgId, j.message, ok ? "ok" : "bad");
      $("env-install").classList.add("hidden");
      await refreshAll();
      setMsg(msgId, j.message, ok ? "ok" : "bad");
    }
  }, 700);
}

// ---------------------------------------------------------------- the application ends when this window is closed
setInterval(() => { fetch("/api/ping", { method: "POST" }).catch(() => {}); }, 5000);
$("quit").onclick = async () => {
  await api("/api/quit", {});
  document.body.innerHTML = "<main><h2>The Data Application has stopped.</h2><p>You can close this window.</p></main>";
  setTimeout(() => window.close(), 400);
};
boot(location.hash.replace("#", "") || undefined);
