"""The sheets of the analysis (the sheets of the reference workbook Biblioshiny_Analysis.xlsx): what each one is, what it needs, which plots it has.
The scripts are in steps/sheets/<Sheet>/<Sheet>.py (data) and <Sheet>_plot.py (plot); the application copies a script into the project's folder <Sheet>/ and runs it there."""

# name, group, title, what it is, sheets it needs, plots (id, title, files written)
_ROWS = [
    ("Authors", "Tables", "Authors", "One row per paper and author (the author is the Scopus Author ID, never the name).", [], []),
    ("Affiliations", "Tables", "Affiliations", "One row per paper and affiliation, with its country and institution.", [], []),
    ("Countries", "Tables", "Countries", "One row per paper and country (a paper counts once for each of its countries).", [], []),
    ("References", "Tables", "References", "One row per paper and cited reference. Needs a Scopus export made with the References option; without it this sheet is skipped.", [], []),
    ("Author_Summary", "Tables", "Author summary", "Per author: papers, fractional papers, citations, first year, h, g and m index.", ["Authors"], []),
    ("02_Main_Information", "Main information", "Main information", "The main numbers of the data set and the documents by type.", ["Authors", "Author_Summary", "Countries", "References"],
     [("document_types", "Documents by type", ["document_types"])]),
    ("Document_Types", "Main information", "Document types (pie)", "Papers of each document type, as a pie chart.", [], [("document_types_pie", "Document types: pie chart", ["document_types_pie"])]),
    ("Languages", "Main information", "Languages (pie)", "Papers by language of the original document, as a pie chart.", [], [("languages_pie", "Languages: pie chart", ["languages_pie"])]),
    ("Open_Access", "Main information", "Open access status (pie)", "Papers by open access class (Gold, Hybrid Gold, Bronze, Green, Closed / Unknown), as a pie chart.", [], [("open_access_pie", "Open access: pie chart", ["open_access_pie"])]),
    ("03_Annual_Production", "Production", "Annual production", "Documents and total citations per year.", [], [("annual_production", "Annual production", ["annual_production"])]),
    ("04_Avg_Citations", "Production", "Average citations per year", "Mean citations per paper and per year of age.", [], [("average_citations", "Average citations per year", ["average_citations_per_year"])]),
    ("05_Life_Cycle", "Production", "Life cycle", "Cumulative documents and a fitted logistic (S-shaped) growth curve.", [], [("life_cycle", "Life cycle", ["life_cycle"])]),
    ("07_Top_Sources", "Sources", "Top sources", "The most productive sources (journals, books, proceedings).", [], [("top_sources", "Top sources", ["top_sources"])]),
    ("09_Pivot", "Sources", "Documents per source", "The number of documents of every source (the base of Bradford's law).", [], []),
    ("09_Bradford", "Sources", "Bradford's law", "Sources ranked by productivity and divided into three zones.", ["09_Pivot"], [("bradford", "Bradford's law", ["bradford"])]),
    ("Bradford_Core", "Sources", "Bradford core: who publishes there", "Which countries, authors and institutions publish most in the Bradford core sources, and whether those papers are cited more than their other papers.", ["09_Bradford", "Authors", "Affiliations", "Countries"],
     [("core_countries", "Countries in the core sources", ["core_countries_bars", "core_countries_heatmap", "core_countries_cpp"]),
      ("core_authors", "Authors in the core sources", ["core_authors_bars", "core_authors_heatmap", "core_authors_cpp"]),
      ("core_institutions", "Institutions in the core sources", ["core_institutions_bars", "core_institutions_heatmap", "core_institutions_cpp"])]),
    ("10_Source_Impact", "Sources", "Source impact", "Papers, citations, h, g and m index of every source, and eight ways to see them (choose the plot that tells your story).", [],
     [("source_h_index", "Bars: sources by h-index", ["source_h_index"]),
      ("source_pyramid_papers_vs_cpp", "Pyramid: papers (left) and citations per paper (right)", ["source_pyramid_papers_vs_cpp"]),
      ("source_pyramid_h_vs_g", "Pyramid: h-index (left) and g-index (right)", ["source_pyramid_h_vs_g"]),
      ("source_bubble", "Bubbles: papers against citations (size = h-index)", ["source_bubble"]),
      ("source_dumbbell_h_g", "Dumbbell: h-index and g-index", ["source_dumbbell_h_g"]),
      ("source_heatmap", "Heat map: profile of the top sources", ["source_heatmap"]),
      ("source_cpp_bars", "Bars: citations per paper", ["source_cpp_bars"]),
      ("source_m_vs_year", "Scatter: m-index against first year", ["source_m_vs_year"])]),
    ("11_Sources_Over_Time", "Sources", "Sources over time", "Cumulative documents of the five most productive sources, and a timeline of the most productive sources.", [],
     [("sources_over_time", "Sources over time: cumulative lines (top 5)", ["sources_over_time"]), ("sources_timeline", "Sources over time: timeline (bubbles)", ["sources_timeline"])]),
    ("Author_Bursts", "Authors", "Author bursts", "The authors with the strongest bursts of publication (CiteSpace-style burst history): table, plot and HTML page.", ["Authors"],
     [("author_bursts", "Author bursts: strongest bursts of publication", ["author_bursts"])]),
    ("14_Author_Over_Time", "Authors", "Authors over time", "Papers per year of the ten most productive authors.", ["Authors", "Author_Summary"], [("authors_over_time", "Authors over time: heat map", ["authors_over_time"]),
      ("authors_timeline", "Authors over time: timeline (bubbles)", ["authors_timeline"])]),
    ("15_Lotka", "Authors", "Lotka's law", "How many authors wrote 1, 2, 3 ... papers.", ["Author_Summary"], [("lotka", "Lotka's law", ["lotka"])]),
    ("16_Author_Impact", "Authors", "Author impact", "The 20 authors with the highest h-index.", ["Author_Summary"], [("author_h_index", "Authors by h-index", ["author_h_index"])]),
    ("Institution_Bursts", "Affiliations", "Institution bursts", "The institutions with the strongest bursts of publication (CiteSpace-style burst history): table, plot and HTML page.", ["Affiliations"],
     [("institution_bursts", "Institution bursts: strongest bursts of publication", ["institution_bursts"])]),
    ("17_Top_Affiliations", "Affiliations", "Top affiliations", "The most productive institutions.", ["Affiliations"], [("top_affiliations", "Top affiliations", ["top_affiliations"])]),
    ("18_Affil_Over_Time", "Affiliations", "Affiliations over time", "Cumulative documents of the most productive institutions, and a timeline (bubbles) of the most productive institutions.", ["Affiliations"],
     [("affiliations_over_time", "Affiliations over time: cumulative lines (top 5)", ["affiliations_over_time"]), ("affiliations_timeline", "Affiliations over time: timeline (bubbles)", ["affiliations_timeline"])]),
    ("19_Corr_Countries", "Countries", "Corresponding authors' countries", "Papers by country of the corresponding author: single-country (SCP) and multi-country (MCP).", [],
     [("corresponding_countries", "Corresponding countries: stacked bars", ["corresponding_countries"]),
      ("pyramid_scp_vs_mcp", "Corresponding countries: pyramid (SCP left, MCP right)", ["pyramid_scp_vs_mcp"])]),
    ("21_Countries_Over_Time", "Countries", "Countries over time", "Papers per year of the most productive countries (heat map and timeline).", ["Countries"],
     [("countries_over_time", "Countries over time: heat map", ["countries_over_time"]), ("countries_timeline", "Countries over time: timeline (bubbles)", ["countries_timeline"])]),
    ("Country_Radar", "Countries", "Country radar", "Five indicators (documents, citations, citations per document, h-index, share of multi-country papers) of the most productive countries, as a radar chart.", ["Countries"],
     [("radar_countries", "Radar chart: countries on five indicators", ["radar_countries"])]),
    ("Country_Bursts", "Countries", "Country bursts", "The countries with the strongest bursts of publication (CiteSpace-style burst history): table, plot and HTML page.", ["Countries"],
     [("country_bursts", "Country bursts: strongest bursts of publication", ["country_bursts"])]),
    ("20_22_Countries", "Countries", "Countries' production and citations", "Documents and citations of the ten most productive countries.", ["Countries"],
     [("countries", "Countries: documents and citations", ["countries_production", "most_cited_countries"])]),
    ("World_Map", "Countries", "World map", "Documents of every country; the map shows the 15 most productive countries with name and number of documents.", ["Countries"],
     [("world_map_top15", "World map: 15 most productive countries", ["world_map_top15"])]),
    ("Country_Collaboration", "Countries", "Country collaboration", "Joint papers of every pair of countries, and the chord diagram of the six most productive countries and the rest of the world.", ["Countries"],
     [("top_country_pairs", "Country collaboration: pairs with most joint papers", ["top_country_pairs"]), ("chord_diagram", "Country collaboration: chord diagram", ["chord_diagram"])]),
    ("23_Top_Cited", "Documents", "Most cited documents", "The 20 most cited documents.", [], [("top_cited", "Most cited documents", ["top_cited"])]),
]
# options the user is asked for (saved in the project; the sheet's data script gets them as arguments): id, label, kind, default, limits, argument
_OPTIONS = {"11_Sources_Over_Time": [
    {"id": "top_sources", "label": "Number of sources in the timeline plot", "kind": "number", "default": 10, "min": 1, "max": 60, "arg": "--top-sources"},
    {"id": "keep_ties", "label": "Also show more sources when they tie with the last one; the number above is then only a minimum", "kind": "check", "default": False, "arg": "--keep-ties", "arg_off": "--cut-ties"}],
            "18_Affil_Over_Time": [
    {"id": "top_affiliations", "label": "Number of institutions in the timeline plot", "kind": "number", "default": 10, "min": 1, "max": 60, "arg": "--top-affiliations"},
    {"id": "keep_ties", "label": "Also show more institutions when they tie with the last one; the number above is then only a minimum", "kind": "check", "default": False, "arg": "--keep-ties", "arg_off": "--cut-ties"}],
            "Country_Radar": [{"id": "top_countries", "label": "Number of countries drawn on the radar (the most productive ones, 2 to 10; the scale is the largest of the top 10)", "kind": "number", "default": 5, "min": 2, "max": 10, "arg": "--top-countries"}],
            "Languages": [{"id": "top_languages", "label": "Number of languages with their own slice (the others are grouped as \"Other languages\")", "kind": "number", "default": 8, "min": 1, "max": 20, "arg": "--top-languages"}],
            "21_Countries_Over_Time": [
    {"id": "top_countries", "label": "Number of countries in the heat map and the timeline plot", "kind": "number", "default": 10, "min": 1, "max": 60, "arg": "--top-countries"},
    {"id": "keep_ties", "label": "Also show more countries when they tie with the last one; the number above is then only a minimum", "kind": "check", "default": False, "arg": "--keep-ties", "arg_off": "--cut-ties"}],
            "Bradford_Core": [{"id": "top", "label": "Number of countries, authors and institutions shown in each picture (those with most papers in the core sources)", "kind": "number", "default": 15, "min": 3, "max": 40, "arg": "--top"}],
            "10_Source_Impact": [{"id": "top_sources", "label": "Number of sources in the plots (those with the highest h-index)", "kind": "number", "default": 15, "min": 3, "max": 60, "arg": "--top-sources"}],
            "Country_Bursts": [
    {"id": "top", "label": "Number of countries shown (those with the strongest bursts)", "kind": "number", "default": 10, "min": 3, "max": 40, "arg": "--top"},
    {"id": "gamma", "label": "Cost of starting a burst, gamma (a smaller value finds more and longer bursts; 0.7 reproduces CiteSpace on this study's countries)", "kind": "number", "float": True, "step": 0.1, "default": 0.7, "min": 0.1, "max": 2.0, "arg": "--gamma"},
    {"id": "min_papers", "label": "Smallest number of papers an item needs to be tested for bursts", "kind": "number", "default": 5, "min": 2, "max": 30, "arg": "--min-papers"}],
            "Author_Bursts": [
    {"id": "top", "label": "Number of authors shown (those with the strongest bursts)", "kind": "number", "default": 10, "min": 3, "max": 40, "arg": "--top"},
    {"id": "gamma", "label": "Cost of starting a burst, gamma (a smaller value finds more and longer bursts; 0.7 reproduces CiteSpace on this study's countries)", "kind": "number", "float": True, "step": 0.1, "default": 0.7, "min": 0.1, "max": 2.0, "arg": "--gamma"},
    {"id": "min_papers", "label": "Smallest number of papers an item needs to be tested for bursts", "kind": "number", "default": 4, "min": 2, "max": 30, "arg": "--min-papers"}],
            "Institution_Bursts": [
    {"id": "top", "label": "Number of institutions shown (those with the strongest bursts)", "kind": "number", "default": 10, "min": 3, "max": 40, "arg": "--top"},
    {"id": "gamma", "label": "Cost of starting a burst, gamma (a smaller value finds more and longer bursts; 0.7 reproduces CiteSpace on this study's countries)", "kind": "number", "float": True, "step": 0.1, "default": 0.7, "min": 0.1, "max": 2.0, "arg": "--gamma"},
    {"id": "min_papers", "label": "Smallest number of papers an item needs to be tested for bursts", "kind": "number", "default": 5, "min": 2, "max": 30, "arg": "--min-papers"}],
            "World_Map": [{"id": "top_countries", "label": "Number of countries on the map (the most productive ones)", "kind": "number", "default": 15, "min": 1, "max": 60, "arg": "--top-countries"}],
            "14_Author_Over_Time": [
    {"id": "top_authors", "label": "Number of authors in the heat map and the timeline plot", "kind": "number", "default": 15, "min": 1, "max": 100, "arg": "--top-authors"},
    {"id": "keep_ties", "label": "Also show more authors when they tie with the last one (same number of papers); the number above is then only a minimum", "kind": "check", "default": False, "arg": "--keep-ties", "arg_off": "--cut-ties"}]}
# an explanation shown at the bottom of a task page (HTML), before the Activity box
_EXPLAIN = {"09_Bradford": """<h3>How the core sources are calculated</h3>
<ol>
<li><b>Rank.</b> The sources are sorted by their number of documents, the largest first: rank 1 is the most productive source. Papers without a Source title are left out.</li>
<li><b>Cumulative share.</b> Going down the list, the documents are added up (Cumulative Documents). Cumulative share = Cumulative Documents / all documents of the ranked sources.</li>
<li><b>Three zones with about one third of the documents each.</b> <b>Zone 1 is the core</b>: the top-ranked sources, as long as the cumulative share has not passed 1/3. Zone 2 goes on up to 2/3, Zone 3 holds the rest. The core is therefore a few sources that give a third of all documents; Zone 2 needs many more sources for the next third, and Zone 3 very many for the last third.</li>
<li><b>The source on the border.</b> In the <i>table</i> (the Excel method) a source belongs to Zone 1 only while its cumulative share is at most 1/3, so the source that crosses the line starts Zone 2. In the <i>plot</i> (the method of the study) the source that crosses the line completes the zone, so the core usually has one source more than in the table. The ranked list is the same in both.</li>
<li><b>Bradford multiplier k.</b> k is the geometric mean of (sources of Zone 2 / sources of Zone 1) and (sources of Zone 3 / sources of Zone 2). Bradford's law says these two ratios are about equal. The plot also fits C(r) = a + b ln(r) to the cumulative documents against ln(rank) (least squares) and shows R&sup2;.</li>
</ol>
<h3>How to read the plot</h3>
<p>Horizontal axis: ln(rank) of the source (rank 1 is at 0, the less productive sources lie further right). Vertical axis: the cumulative number of documents up to that rank. The two dotted vertical lines are the zone borders; the three shaded bands are Core (Zone 1), Zone 2 and Zone 3, each labelled with its number of sources.</p>
<ul>
<li><b>The numbered box (top left).</b> It lists the sources of the core zone, in rank order: number 1 is the most productive source, number 2 the next, and so on up to the last source of Zone 1. The same numbers stand next to the blue dots on the curve, so a dot can be matched to its source name. The box therefore has as many lines as the core has sources, whatever the data. Long journal names are shortened to fit (the country in brackets is dropped, known long titles get their usual abbreviation); the table always has the full name.</li>
<li><b>Empirical cumulative curve (black line).</b> The real data: for every rank, the documents of that source and of all more productive sources added up. It rises steeply at first (the core gives many documents with few sources) and then more and more slowly.</li>
<li><b>C(r) = a + b ln(r), R&sup2; (red dashed line).</b> The straight line that fits the curve best when rank is on the logarithmic axis (least squares). <i>C(r)</i> is the cumulative number of documents at rank <i>r</i>; <i>b</i> (the slope) is the number of documents added each time the rank is multiplied by e (about 2.72) and <i>a</i> (the intercept) is where the line cuts the vertical axis at ln(r) = 0. <i>R&sup2;</i> says how well the line fits, from 0 (not at all) to 1 (perfectly): the closer to 1, the better the data follow Bradford's law. The title above the plot repeats k, R&sup2;, the number of sources and the number of documents used.</li>
</ul>"""}
_PER_PLOT = {"10_Source_Impact", "Bradford_Core"}        # the plot script makes only the plot asked for (--only ID)
_DOWNLOADS = {n: [{"file": f"{n}.html", "label": "Download the HTML page"}] for n in ("Country_Bursts", "Author_Bursts", "Institution_Bursts")}      # extra files a task page offers
_EXTRA_CSV = {"Country_Bursts": ["Country_Bursts_yearly.csv"], "Author_Bursts": ["Author_Bursts_yearly.csv"], "Institution_Bursts": ["Institution_Bursts_yearly.csv"], "Country_Radar": ["Country_Radar_scaled.csv"], "18_Affil_Over_Time": ["18_Affil_Timeline.csv"], "11_Sources_Over_Time": ["11_Source_Timeline.csv"], "21_Countries_Over_Time": ["21_Country_Timeline.csv"], "Country_Collaboration": ["Country_Collaboration_chord.csv"], "14_Author_Over_Time": ["14_Author_Timeline.csv"], "05_Life_Cycle": ["05_Life_Cycle_parameters.csv"], "09_Bradford": ["09_Bradford_zones.csv"], "Bradford_Core": ["Bradford_Core_baseline.csv", "Bradford_Core_matrix.csv"], "15_Lotka": ["15_Lotka_parameters.csv"]}

SHEETS = [{"name": n, "group": g, "title": t, "what": w, "needs": needs, "csvs": [f"{n}.csv"] + _EXTRA_CSV.get(n, []),
           "options": _OPTIONS.get(n, []), "per_plot": n in _PER_PLOT, "downloads": _DOWNLOADS.get(n, []), "explain": _EXPLAIN.get(n, ""), "plots": [{"id": i, "title": pt, "files": files} for i, pt, files in plots]} for n, g, t, w, needs, plots in _ROWS]
BY_NAME = {s["name"]: s for s in SHEETS}
GROUPS = list(dict.fromkeys(s["group"] for s in SHEETS))


def option_values(project, name):
    """the options of a sheet with the values saved in the project (the defaults where nothing was saved)"""
    saved = (project.load().get("sheet_options") or {}).get(name, {})
    out = {}
    for o in BY_NAME[name]["options"]:
        v = saved.get(o["id"], o["default"])
        if o["kind"] == "number":
            try:
                v = min(max(float(v) if o.get("float") else int(v), o["min"]), o["max"])
                v = round(v, 2) if o.get("float") else v
            except (TypeError, ValueError):
                v = o["default"]
        else:
            v = bool(v)
        out[o["id"]] = v
    return out


def save_options(project, name, values):
    """validate and save the values the user typed; returns the values as saved"""
    cfg = project.load().get("sheet_options") or {}
    cfg[name] = {**cfg.get(name, {}), **{k: v for k, v in values.items() if k in {o["id"] for o in BY_NAME[name]["options"]}}}
    project.update(sheet_options=cfg)
    return option_values(project, name)


def option_args(project, name):
    args = []
    for o in BY_NAME[name]["options"]:
        v = option_values(project, name)[o["id"]]
        if o["kind"] == "number":
            args += [o["arg"], str(v)]
        elif (o["arg"] if v else o.get("arg_off")):
            args.append(o["arg"] if v else o["arg_off"])
    return args


def get(name):
    return BY_NAME.get(name)
