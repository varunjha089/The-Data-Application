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
  $("folder").textContent = "The Data Application " + (state.version || "") + "  |  application folder: " + state.folder;
  api("/api/update").then(renderUpdateFooter).catch(() => {});
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
$("sample").onclick = async () => {
  setMsg("sample-msg", "Making the sample data ...", "warn");
  const r = await api("/api/project/sample", { location: $("new-loc").value });
  if (r.ok) { setMsg("sample-msg", ""); boot("settings"); } else setMsg("sample-msg", r.message, "bad");
};
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
  const items = [["Project", [["overview", "Overview", null], ["settings", "Settings", state.project.env.can_clean && state.project.data.exists ? "done" : "stale"], ["report", "Report", null]]],
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
  for (const id of ["overview", "settings", "clean", "sheet", "report"]) $("page-" + id).classList.toggle("hidden", id !== kind);
  if (kind === "overview") renderOverview();
  else if (kind === "settings") renderSettings();
  else if (kind === "report") renderReport();
  else if (kind === "clean") renderClean();
  else renderSheet(page.slice(6));
}

// ---------------------------------------------------------------- overview
function renderOverview() {
  const p = state.project, ready = p.clean.exists;
  $("ov-notice").classList.toggle("hidden", ready);
  $("ov-notice").innerHTML = ready ? "" : 'The data has not been cleaned yet: do <b>Step 1: Clean the data</b> first. <button id="ov-go-clean">Go to Step 1</button>';
  if (!ready) $("ov-go-clean").onclick = () => selectPage(p.env.can_clean && p.data.exists ? "clean" : "settings");
  $("ov-years").innerHTML = "<b>Years in the plots:</b> " + esc(yearsText(p.years)) + ' (<a href="#settings" id="ov-go-years">change in Settings</a>)';
  $("ov-go-years").onclick = (e) => { e.preventDefault(); selectPage("settings"); };
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
  renderYears();
  renderLook();
  renderAI();
}
function yearsText(y) {
  if (!y) return "";
  const range = !y.from && !y.to ? "all years" : (y.from || "start") + "\u2013" + (y.to || "last year");
  return y.presets[y.preset] + ": " + range;
}
function renderYears() {
  const y = state.project.years;
  $("years-preset").innerHTML = Object.entries(y.presets).map(([k, label]) => '<option value="' + k + '"' + (k === y.preset ? " selected" : "") + ">" + esc(label) + "</option>").join("");
  const custom = y.preset === "custom";
  for (const id of ["years-from", "years-to"]) { $(id).disabled = !custom; }
  if (document.activeElement !== $("years-from")) $("years-from").value = y.from || "";
  if (document.activeElement !== $("years-to")) $("years-to").value = y.to || "";
  pill("years-pill", !y.from && !y.to ? "all years" : (y.from || "start") + "\u2013" + (y.to || "end"), "ok");
  const bits = ["Chosen on " + esc(y.set_on) + "; it stays the same until you change it."];
  if (y.data) bits.push("The data has papers from " + y.data[0] + " to " + y.data[1] + ".");
  if (y.preset === "last10" || y.preset === "last5") bits.push("A complete year is a year that has ended: the current year is still being indexed and early-access papers carry next year's date.");
  if (y.can_roll) bits.push("<b>Today this choice gives " + y.today[0] + "\u2013" + y.today[1] + ":</b> press Roll forward to use it.");
  $("years-info").innerHTML = bits.join(" ");
  $("years-roll").classList.toggle("hidden", !y.can_roll);
}
async function saveYears(body) {
  const r = await api("/api/years", body);
  state.project.years = r.years;
  renderYears();
  setMsg("years-msg", r.ok ? "Saved. Generate the plots again to use it." : r.message, r.ok ? "ok" : "bad");
}
$("years-preset").onchange = () => saveYears({ preset: $("years-preset").value, from: Number($("years-from").value) || 0, to: Number($("years-to").value) || 0 });
$("years-from").onchange = $("years-to").onchange = () => saveYears({ preset: "custom", from: Number($("years-from").value) || 0, to: Number($("years-to").value) || 0 });
$("years-roll").onclick = () => saveYears({ roll: true });
function renderLook() {
  const lk = state.project.look, ch = state.project.look_choices;
  const pct = (v) => Math.round(v * 100) + "%";
  const sizes = [0.8, 1, 1.2, 1.4, 1.6, 1.8, 2];
  const fill = (id, items, cur) => { $(id).innerHTML = items.map(([v, label]) => '<option value="' + v + '"' + (String(v) === String(cur) ? " selected" : "") + ">" + esc(label) + "</option>").join(""); };
  fill("look-text", sizes.map((v) => [v, pct(v) + (v === 1 ? " (normal)" : "")]), lk.text);
  fill("look-size", sizes.map((v) => [v, pct(v) + (v === 1 ? " (normal)" : "")]), lk.size);
  fill("look-dpi", ch.dpi.map((v) => [v, v ? v + " dpi" : "as each plot chooses (150 dpi)"]), lk.dpi);
  fill("look-palette", Object.entries(ch.palettes), lk.palette);
  $("look-pdf").checked = lk.pdf; $("look-tiff").checked = lk.tiff;
  if (document.activeElement !== $("look-rows")) $("look-rows").value = lk.table_rows;
  const changed = lk.text !== 1 || lk.size !== 1 || lk.dpi || lk.pdf || lk.tiff || lk.palette !== "standard";
  pill("look-pill", changed ? "changed" : "standard", changed ? "warn" : "ok");
}
for (const id of ["look-text", "look-size", "look-dpi", "look-palette", "look-pdf", "look-tiff", "look-rows"]) $(id).onchange = async () => {
  const values = { text: Number($("look-text").value), size: Number($("look-size").value), dpi: Number($("look-dpi").value), palette: $("look-palette").value, pdf: $("look-pdf").checked, tiff: $("look-tiff").checked, table_rows: Math.max(0, Math.min(1000, Math.round(Number($("look-rows").value) || 0))) };
  const r = await api("/api/look", { values });
  state.project.look = r.look; renderLook();
  setMsg("look-msg", id === "look-rows" ? "Saved. Generate the data again to redraw the table pictures." : "Saved. Generate the plots again to see it.", "ok");
};
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
  if (document.activeElement !== $("clean-exclude")) $("clean-exclude").value = c.exclude_only_queries || "";
  $("clean-fallback").checked = c.country_fallback !== false;
  if (c.exists && c.current) { pill("clean-pill", "done", "ok"); $("clean-info").textContent = "Made " + day(c.made) + ". Results and log are in the project's folder 01_Clean_Data."; }
  else if (c.exists) { pill("clean-pill", "out of date", "warn"); $("clean-info").textContent = "The cleaned file belongs to an earlier main data or to other search settings: clean again."; }
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
$("clean-exclude").onchange = async () => {
  const r = await api("/api/clean/options", { exclude_only_queries: $("clean-exclude").value });
  $("clean-exclude").value = r.exclude_only_queries || "";
  setMsg("clean-exclude-msg", r.error || "saved: clean the data again to use it", r.error ? "bad" : "ok");
  await refreshAll();
};
$("clean-fallback").onchange = async () => {
  const r = await api("/api/clean/options", { country_fallback: $("clean-fallback").checked });
  setMsg("clean-fallback-msg", r.error || "saved: clean the data again to use it", r.error ? "bad" : "ok");
  await refreshAll();
};
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
  renderInput(name, s.input);
  s.options = s.options || [];                      // an older server process sends no options
  $("sh-options").classList.toggle("hidden", !s.options.length);
  const yearsNote = (o) => o.id === "years" && s.plot_years ? " <span class=\"info\">(now: " + (s.plot_years[0] || s.plot_years[1] ? (s.plot_years[0] || "start") + "\u2013" + (s.plot_years[1] || "last year") : "all years") + ")</span>" : "";
  const control = (o) => o.kind === "number" ?
    '<input type="number" data-opt="' + esc(o.id) + '" min="' + o.min + '" max="' + o.max + '" step="' + (o.step || 1) + '" value="' + o.value + '" style="width:6em">' :
    o.kind === "select" ? '<select data-opt="' + esc(o.id) + '">' + o.choices.map(([v, label]) => '<option value="' + esc(v) + '"' + (v === o.value ? " selected" : "") + ">" + esc(label) + "</option>").join("") + "</select>" :
    '<input type="checkbox" data-opt="' + esc(o.id) + '"' + (o.value ? " checked" : "") + ">";
  $("sh-options").innerHTML = s.options.length ? "<b>Your choices</b> (saved in this project until you change them)" + s.options.map((o) =>
    '<label class="opt" data-row="' + esc(o.id) + '">' + esc(o.label) + " " + control(o) + yearsNote(o) + "</label>").join("") + ' <span id="sh-opt-msg" class="msg"></span>' : "";
  const showRows = () => s.options.forEach((o) => {
    if (!o.show_if) return;
    const ctl = document.querySelector('#sh-options [data-opt="' + o.show_if[0] + '"]'), row = document.querySelector('#sh-options [data-row="' + o.id + '"]');
    if (ctl && row) row.classList.toggle("hidden", ctl.value !== o.show_if[1]);
  });
  showRows();
  document.querySelectorAll("#sh-options [data-opt]").forEach((el) => el.onchange = async () => {
    const values = {};
    document.querySelectorAll("#sh-options [data-opt]").forEach((x) => values[x.dataset.opt] = x.type === "checkbox" ? x.checked : (x.tagName === "SELECT" ? x.value : Number(x.value)));
    const r = await api("/api/sheet/options", { name, values });
    s.options.forEach((o) => { if (r.values) o.value = r.values[o.id]; });
    if (r.values) document.querySelectorAll("#sh-options [data-opt]").forEach((x) => { if (x.type === "checkbox") x.checked = r.values[x.dataset.opt]; else x.value = r.values[x.dataset.opt]; });
    showRows();
    setMsg("sh-opt-msg", r.values ? "saved: generate the data or the plot to use it" : (r.error || "not saved"), r.values ? "ok" : "bad");
    if (r.values) { sheetsInfo = await api("/api/sheets"); const msg = $("sh-opt-msg").textContent; renderSheet(name); setMsg("sh-opt-msg", msg, "ok"); }
  });
  $("sh-plot-buttons").innerHTML = s.plots.map((pl) => '<button data-plot="' + esc(pl.id) + '"' + (canRun && p.env.can_plot ? "" : " disabled") + ">" +
    (pl.files.every((f) => f.exists) ? "Generate the plot again: " : "Generate plot: ") + esc(pl.title) + "</button>").join(" ");
  document.querySelectorAll("#sh-plot-buttons [data-plot]").forEach((b) => b.onclick = () => runJob("/api/sheet/plot", { name, plot: b.dataset.plot }, "sh-msg"));
  const stamp = "?v=" + Date.now();
  const tables = s.csvs.filter((c) => c.exists && c.picture);             // the table pictures are shown with the plots
  $("sh-plots-title").classList.toggle("hidden", !s.plots.some((pl) => pl.files.some((f) => f.exists)) && !tables.length);
  $("sh-plots-title").textContent = s.plots.length ? "Plots and tables" : "Tables";
  const refName = (r) => r ? '<label class="ref"><input type="checkbox" data-rp="' + esc(r.stem) + '"' + (r.selected ? " checked" : "") + ' title="Tick to put this in the report"> ' +
    (r.kind === "fig" ? "Figure: " : "Table: ") + esc(r.title) + ' <span class="stem">(report file ' + esc(r.stem) + ".tex)</span></label>" : "";
  $("sh-plots").innerHTML = '<div class="plots">' + s.plots.map((pl) => pl.files.filter((f) => f.exists).map((f) =>
    '<div class="plot">' + refName(f.report) + '<img src="/files/' + esc(name) + "/" + esc(f.name) + ".png" + stamp + '" alt="' + esc(pl.title) + '"><div class="caption">' + esc(pl.title) +
    ' &nbsp; <a href="/files/' + esc(name) + "/" + esc(f.name) + '.png?download=1">PNG</a><a href="/files/' + esc(name) + "/" + esc(f.name) + '.svg?download=1">SVG</a>' +
    (f.extra || []).map((x) => '<a href="/files/' + esc(name) + "/" + esc(f.name) + "." + x + '?download=1">' + (x === "tif" ? "TIFF" : x.toUpperCase()) + "</a>").join("") + "</div></div>").join("")).join("") +
    tables.map((c) => { const t = c.file.replace(/\.csv$/, "") + "_table";
      return '<div class="plot">' + refName(c.report) + '<img src="/files/' + esc(name) + "/" + esc(t) + ".png" + stamp + '" alt="Table ' + esc(c.file) + '"><div class="caption">Table: ' + esc(c.file.replace(/\.csv$/, "")) +
        ' &nbsp; <a href="/files/' + esc(name) + "/" + esc(t) + '.png?download=1">PNG</a><a href="/files/' + esc(name) + "/" + esc(t) + '.svg?download=1">SVG</a></div></div>'; }).join("") + "</div>";
  bindTicks();
  $("sh-explain").classList.toggle("hidden", !s.explain);
  $("sh-explain").innerHTML = s.explain || "";
  const first = s.csvs[0];
  $("sh-dl").classList.toggle("hidden", !first.exists);
  $("sh-dl").href = "/files/" + name + "/" + first.file + "?download=1";
  $("sh-downloads").innerHTML = (s.downloads || []).filter((d) => d.exists).map((d) => '<a class="button" href="/files/' + esc(name) + "/" + esc(d.file) + '?download=1">' + esc(d.label) + "</a>").join(" ");
  $("sh-dl-log").classList.toggle("hidden", !s.log);
  $("sh-dl-log").href = "/files/" + name + "/" + name + "_log.txt?download=1";
  $("sh-dl-info").classList.toggle("hidden", !s.run_info);
  $("sh-dl-info").href = "/files/" + name + "/run_info.json?download=1";
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
// a file of the user's that the sheet reads (the Scopus Source List): which one is in use, and a button to choose another
function renderInput(name, inp) {
  $("sh-input").classList.toggle("hidden", !inp);
  if (!inp) return;
  $("sh-input").innerHTML = "<b>" + esc(inp.label) + ":</b> " + (inp.file ? "using <b>" + esc(inp.file) + "</b> (" + inp.mb + " MB, chosen " + day(inp.when) + ")."
      : '<span style="color: var(--bad)">none chosen yet</span>: without it this sheet is skipped.') +
    ' <button id="sh-input-choose">' + (inp.file ? "Choose another file" : "Choose the " + esc(inp.label)) + "</button>" +
    '<p class="info">' + esc(inp.help) + ' <a href="' + esc(inp.link) + '" target="_blank" rel="noopener">Elsevier: Scopus content and the Source List</a></p>' +
    '<span id="sh-input-msg" class="msg"></span>';
  $("sh-input-file").accept = inp.accept.join(",");
  $("sh-input-choose").onclick = () => $("sh-input-file").click();
  $("sh-input-file").onchange = async () => {
    const f = $("sh-input-file").files[0];
    if (!f) return;
    setMsg("sh-input-msg", "Copying " + f.name + " (" + (f.size / 1048576).toFixed(1) + " MB) ...", "warn");
    setBusy(true);
    let r;
    try { r = await (await fetch("/api/sheet/input?sheet=" + encodeURIComponent(name) + "&name=" + encodeURIComponent(f.name), { method: "POST", body: f })).json(); }
    catch (e) { r = { ok: false, message: "The copy failed: " + e }; }
    $("sh-input-file").value = "";
    setBusy(false);
    if (r.ok) { sheetsInfo = await api("/api/sheets"); renderSheet(name); }
    setMsg("sh-input-msg", r.message, r.ok ? "ok" : "bad");
  };
}
// a tick box above every plot and table: put it in the report or leave it out (the same choice as on the Report page)
function bindTicks() {
  document.querySelectorAll("[data-rp]").forEach((box) => box.onchange = async () => {
    const r = await api("/api/report/tick", { stem: box.dataset.rp, on: box.checked });
    document.querySelectorAll('[data-rp="' + box.dataset.rp + '"]').forEach((b) => b.checked = r.selected);
    for (const sh of sheetsInfo.sheets) for (const x of sh.plots.flatMap((pl) => pl.files).concat(sh.csvs)) if (x.report && x.report.stem === box.dataset.rp) x.report.selected = r.selected;
  });
}
async function loadTable(name) {
  const t = await api("/api/sheet/table?name=" + encodeURIComponent(name) + "&csv=" + encodeURIComponent(curCsv) + "&page=" + curPage + "&size=50");
  document.querySelectorAll("#sh-csvs .tabbtn").forEach((b) => b.classList.toggle("active", b.dataset.csv === curCsv));
  const c = ((spec(name) || {}).csvs || []).find((x) => x.file === curCsv), stem = curCsv.replace(/\.csv$/, "") + "_table";
  $("sh-tablepic").innerHTML = (c && c.report ? '<label class="ref"><input type="checkbox" data-rp="' + esc(c.report.stem) + '"' + (c.report.selected ? " checked" : "") + ' title="Tick to put this in the report"> Table: ' +
    esc(c.report.title) + ' <span class="stem">(report file ' + esc(c.report.stem) + ".tex)</span></label> " : "") + (c && c.picture ? 'Download the table as a picture: <a class="button" href="/files/' + esc(name) + "/" + esc(stem) + '.png?download=1">PNG</a> <a class="button" href="/files/' + esc(name) + "/" + esc(stem) + '.svg?download=1">SVG</a>' : "");
  const sp = spec(name);
  if (sp && c && c.picture) {
    $("sh-tablepic").innerHTML += ' &nbsp; <label>Rows in the picture <input type="number" id="sh-rows" min="0" max="1000" step="1" value="' + sp.table_rows + '" style="width:6em"></label>' +
      ' <button id="sh-rows-go">Redraw</button> <span class="info">(0 = all; ' + (sp.table_rows_own ? 'this sheet\'s own number, <a href="#" id="sh-rows-reset">use the project\'s</a>' : "the project's number from Settings") + ")</span>";
    $("sh-rows-go").onclick = () => runJob("/api/sheet/table_rows", { name, rows: Math.max(0, Math.min(1000, Math.round(Number($("sh-rows").value) || 0))) }, "sh-msg");
    $("sh-rows").onkeydown = (e) => { if (e.key === "Enter") $("sh-rows-go").click(); };
    if ($("sh-rows-reset")) $("sh-rows-reset").onclick = (e) => { e.preventDefault(); runJob("/api/sheet/table_rows", { name, rows: null }, "sh-msg"); };
  }
  bindTicks();
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

// ---------------------------------------------------------------- AI writing (Settings): provider, key (never shown again), model
let aiInfo = null;
async function renderAI() {
  aiInfo = await api("/api/ai");
  const cur = aiInfo.provider, pv = aiInfo.providers[cur];
  $("ai-provider").innerHTML = Object.entries(aiInfo.providers).map(([k, v]) => '<option value="' + k + '"' + (k === cur ? " selected" : "") + ">" + esc(v.label) + "</option>").join("");
  $("ai-key-info").innerHTML = pv.has_key ? "<b>Key:</b> saved (ending in <code>" + esc(pv.ending) + "</code>; " + esc(pv.where === "keychain" ? "in the macOS Keychain" : pv.where === "file" ? "in the settings folder, readable by you only" : "from the " + pv.where) + ")."
    : "<b>Key:</b> none yet. Paste one below; it is kept " + (navigator.platform.startsWith("Mac") ? "in the macOS Keychain" : "in your settings folder") + ", never in a project or a log.";
  $("ai-key-del").classList.toggle("hidden", !pv.has_key || pv.where.startsWith("environment"));
  $("ai-key-page").href = pv.keys_page;
  if (!$("ai-model").dataset.loadedFor || $("ai-model").dataset.loadedFor !== cur) {
    $("ai-model").innerHTML = pv.model ? '<option value="' + esc(pv.model) + '" selected>' + esc(pv.model) + "</option>" : '<option value="">(load the list of models)</option>';
  }
  $("ai-images").checked = aiInfo.images;
  pill("ai-pill", pv.has_key && pv.model ? "ready" : (pv.has_key ? "choose a model" : "no key"), pv.has_key && pv.model ? "ok" : "warn");
}
async function loadModels() {
  const prov = $("ai-provider").value, pv = aiInfo.providers[prov];
  setMsg("ai-msg", "Asking " + pv.label + " for its models ...", "warn");
  const r = await api("/api/ai/models", { provider: prov });
  if (!r.ok) { setMsg("ai-msg", r.message, "bad"); return; }
  const want = pv.model || pv.suggested;
  $("ai-model").innerHTML = '<option value="">(choose a model)</option>' + r.models.map((m) => '<option value="' + esc(m.id) + '"' + (m.id === want ? " selected" : "") + ">" + esc(m.label + (m.label !== m.id ? "  (" + m.id + ")" : "")) + "</option>").join("");
  $("ai-model").dataset.loadedFor = prov;
  if ($("ai-model").value && $("ai-model").value !== pv.model) await api("/api/ai/settings", { model: $("ai-model").value });
  setMsg("ai-msg", r.models.length + " models. " + ($("ai-model").value ? "In use: " + $("ai-model").value + "." : "Choose one."), "ok");
  renderAI();
}
$("ai-provider").onchange = async () => { await api("/api/ai/settings", { provider: $("ai-provider").value }); $("ai-model").dataset.loadedFor = ""; setMsg("ai-msg", ""); renderAI(); };
$("ai-model").onchange = async () => { await api("/api/ai/settings", { model: $("ai-model").value }); setMsg("ai-msg", "Saved: " + ($("ai-model").value || "no model"), "ok"); renderAI(); };
$("ai-models").onclick = loadModels;
$("ai-images").onchange = () => api("/api/ai/settings", { images: $("ai-images").checked });
$("ai-key-save").onclick = async () => {
  const k = $("ai-key").value.trim();
  if (!k) { setMsg("ai-msg", "Paste the key first.", "warn"); return; }
  setMsg("ai-msg", "Saving and testing the key ...", "warn");
  const r = await api("/api/ai/key", { provider: $("ai-provider").value, key: k });
  $("ai-key").value = "";                                   // the key is never kept in the page
  setMsg("ai-msg", r.message, r.ok ? "ok" : "bad");
  await renderAI();
  if (r.ok && !aiInfo.providers[aiInfo.provider].model) loadModels();
};
$("ai-key-del").onclick = async () => { const r = await api("/api/ai/key", { provider: $("ai-provider").value, delete: true }); setMsg("ai-msg", r.message, "ok"); renderAI(); };

// ---------------------------------------------------------------- the report: template, figures and tables, write with or without AI, build the PDF
let rp = null;
async function renderReport() {
  rp = await api("/api/report/state");
  if (rp.error) return;
  const a = rp.ai, ready = a.has_key && a.model;
  $("rp-ai").innerHTML = "<b>AI model:</b> " + (ready ? esc(a.label) + ", <code>" + esc(a.model) + "</code>" + (a.images ? ", with the plot pictures" : "") : '<span style="color: var(--bad)">' + (a.has_key ? "no model chosen" : "no API key") + "</span>") +
    ' (<a href="#settings" id="rp-go-settings">Settings, AI writing</a>)';
  $("rp-go-settings").onclick = (e) => { e.preventDefault(); selectPage("settings"); };
  if (document.activeElement !== $("rp-study")) $("rp-study").value = rp.options.study || "";
  $("rp-template").innerHTML = "<b>Template:</b> " + (rp.options.template === "default" ? "the default report" : "<code>" + esc(rp.options.template) + "</code>") +
    "; main file <code>Report/" + esc(rp.options.main) + "</code>" + (rp.main_exists ? "" : " (made when you first write)") + ".";
  const n = rp.items.filter((it) => it.selected).length, e = rp.estimate;
  $("rp-estimate").innerHTML = "<b>" + n + "</b> figures and tables ticked. Writing with AI now asks the model <b>" + e.calls + "</b> times (about " +
    Math.round(e.tokens_in / 1000) + " thousand tokens in and " + Math.round(e.tokens_out / 1000) + " thousand out; the files that are unchanged or edited by you are not asked again).";
  $("rp-write").disabled = !ready || !n || !!polling;
  $("rp-write").title = ready ? "" : "Add an API key and choose a model in Settings, AI writing";
  $("rp-write-plain").disabled = !n || !!polling;
  $("rp-build").disabled = !rp.main_exists || !rp.tex || !!polling;
  $("rp-build").title = rp.tex ? "" : "No LaTeX on this computer: install MacTeX, MiKTeX or TeX Live, or upload the Report folder to Overleaf";
  $("rp-pdf").classList.toggle("hidden", !rp.pdf);
  $("rp-pdf").href = "/files/Report/" + encodeURIComponent(rp.options.main.replace(/\.tex$/, ".pdf")) + "?download=1";
  $("rp-check").classList.toggle("hidden", !rp.check_file);
  $("rp-check").href = "/files/Report/report_check.txt?download=1";
  $("rp-log").classList.toggle("hidden", !rp.exists);
  $("rp-log").href = "/files/Report/report_log.txt?download=1";
  const written = rp.items.filter((it) => it.file_state === "written" || it.file_state === "edited").length;
  pill("rp-pill", written ? written + " written" : "not written yet", written ? "ok" : "warn");
  $("rp-count").textContent = "(" + n + " ticked of " + rp.items.filter((it) => it.exists).length + " that exist; " + rp.items.length + " possible)";
  let html = "<thead><tr><th></th><th>Figure or table</th><th>Sheet</th><th>State</th></tr></thead><tbody>";
  for (const g of rp.groups) {
    const rows = rp.items.filter((it) => it.group === g);
    if (!rows.length) continue;
    html += '<tr><td colspan="4"><b>' + esc(g) + "</b></td></tr>" + rows.map((it) => {
      const note = it.failed ? '<span style="color: var(--bad)">failed: ' + esc(it.failed) + "</span>" : esc(it.note) + (it.check.length ? ' &mdash; <span style="color: var(--warn)">numbers to check: ' + esc(it.check.join(", ")) + "</span>" : "");
      return '<tr' + (it.exists ? "" : ' class="info"') + '><td><input type="checkbox" data-stem="' + esc(it.stem) + '"' + (it.selected ? " checked" : "") + (it.exists ? "" : " disabled") + "></td><td>" +
        '<a href="#sheet:' + esc(it.sheet) + '" data-go="' + esc(it.sheet) + '" title="Open the sheet with this ' + (it.kind === "fig" ? "plot" : "table") + '">' + (it.kind === "fig" ? "Figure: " : "Table: ") + esc(it.title) + "</a></td><td>" + esc(it.sheet_title) + "</td><td>" + note + "</td></tr>";
    }).join("");
  }
  $("rp-items").innerHTML = html + "</tbody>";
  document.querySelectorAll("#rp-items [data-stem]").forEach((c) => c.onchange = () => saveItems());
  document.querySelectorAll("#rp-items [data-go]").forEach((a) => a.onclick = (e) => { e.preventDefault(); selectPage("sheet:" + a.dataset.go); });
}
async function saveItems(list) {
  const items = list || Array.from(document.querySelectorAll("#rp-items [data-stem]")).filter((c) => c.checked).map((c) => c.dataset.stem);
  await api("/api/report/options", { items });
  renderReport();
}
$("rp-all").onclick = () => saveItems(rp.items.filter((it) => it.exists && it.file_state !== "deleted").map((it) => it.stem));
$("rp-none").onclick = () => saveItems([]);
$("rp-study").onchange = async () => { await api("/api/report/options", { study: $("rp-study").value }); setMsg("rp-study-msg", "saved", "ok"); };
$("rp-tpl").onclick = async () => {
  const r = await api("/api/browse", { kind: "folder", title: "template" });
  if (!r.path) { if (r.error) setMsg("rp-msg", r.error, "warn"); return; }
  const t = await api("/api/report/template", { path: r.path });
  setMsg("rp-msg", t.message, t.ok ? "ok" : "bad");
  renderReport();
};
$("rp-tpl-default").onclick = async () => { const t = await api("/api/report/default", {}); setMsg("rp-msg", t.message, t.ok ? "ok" : "bad"); renderReport(); };
$("rp-write").onclick = () => runJob("/api/report/write", { ai: true, rewrite: $("rp-rewrite").checked }, "rp-msg");
$("rp-write-plain").onclick = () => runJob("/api/report/write", { ai: false, rewrite: $("rp-rewrite").checked }, "rp-msg");
$("rp-build").onclick = () => runJob("/api/report/build", {}, "rp-msg");
$("rp-folder").onclick = () => api("/api/open", { which: "report" });

// ---------------------------------------------------------------- jobs (set-up, install, clean, sheets, plots): poll the log while one runs
const BUSY_BUTTONS = ["env-go", "env-install", "env-fix", "browse", "choose", "clean", "switch", "ov-all", "ov-plots", "sh-run", "rp-write", "rp-write-plain", "rp-build", "rp-tpl", "rp-tpl-default"];
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
      setBusy(false);                                              // the buttons work again (Choose the Scopus CSV after setting up the venv)
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
// ---------------------------------------------------------------- updates (like a desktop program: a window when a newer release exists)
let upd = null;
function showUpdate(u) {
  upd = u;
  const lt = u.latest;
  $("upd-what").innerHTML = "<b>The Data Application " + esc(lt.version) + "</b> (you have " + esc(u.current) + ")" + (lt.published ? ", published " + esc(lt.published) : "") + ".";
  $("upd-notes").textContent = lt.notes || "(no notes)";
  $("upd-how").textContent = u.method === "git" ? "It is updated with git (your copy is a git clone)." : "The new files are downloaded; the current ones are backed up first.";
  $("upd-page").href = lt.url;
  $("upd-log").classList.add("hidden"); $("upd-log").textContent = ""; setMsg("upd-result", "");
  for (const id of ["upd-install", "upd-later", "upd-skip"]) $(id).disabled = false;
  $("upd-install").textContent = "Install and restart";
  $("upd-dialog").classList.remove("hidden");
}
function renderUpdateFooter(u) { $("upd-auto").checked = u.enabled !== false; }
async function checkUpdate(force) {
  const u = force ? await api("/api/update/check", {}) : await api("/api/update");
  renderUpdateFooter(u);
  if (u.installed) return u;
  if (force) {
    if (u.error) setMsg("upd-msg", u.error, "warn");
    else if (u.available) showUpdate(u);
    else setMsg("upd-msg", "You have the latest version (" + u.current + ").", "ok");
  } else if (u.show) showUpdate(u);
  return u;
}
$("upd-check").onclick = (e) => { e.preventDefault(); setMsg("upd-msg", "Checking ...", ""); checkUpdate(true); };
$("upd-auto").onchange = () => api("/api/update/settings", { enabled: $("upd-auto").checked });
$("upd-later").onclick = () => $("upd-dialog").classList.add("hidden");
$("upd-skip").onclick = async () => { await api("/api/update/skip", { version: upd.latest.version }); $("upd-dialog").classList.add("hidden"); };
$("upd-install").onclick = async () => {
  for (const id of ["upd-install", "upd-later", "upd-skip"]) $(id).disabled = true;
  $("upd-install").textContent = "Installing ...";
  const r = await api("/api/update/install", {});
  if (!r.started) { setMsg("upd-result", r.message || "Another task is still running.", "warn"); $("upd-later").disabled = false; return; }
  $("upd-log").classList.remove("hidden");
  let from = 0;
  const t = setInterval(async () => {
    const j = await api("/api/job?since=" + from);
    if (j.log.length) { $("upd-log").textContent += j.log.join("\n") + "\n"; $("upd-log").scrollTop = $("upd-log").scrollHeight; from = j.next; }
    if (j.state === "running") return;
    clearInterval(t);
    if (j.state !== "done") { setMsg("upd-result", j.message, "bad"); $("upd-later").disabled = false; $("upd-install").textContent = "Not installed"; return; }
    setMsg("upd-result", j.message + " A new window opens in a moment; this one closes.", "ok");
    await api("/api/update/restart", {});
    setTimeout(() => { document.body.innerHTML = "<main><h2>The Data Application was updated.</h2><p>It opens again in a new window. You can close this one.</p></main>"; window.close(); }, 2500);
  }, 800);
};
setTimeout(() => checkUpdate(false).catch(() => {}), 2500);       // after the background check at start-up has had time to answer

boot(location.hash.replace("#", "") || undefined);
