"""common/names.py : shared name rules for countries, institutions and parent organisations (used by 01_clean_data.py and Affiliations.py).

Scopus writes an affiliation as "Department, Institution, City, Postcode, Country". The old rule "country = text after the last comma" gave
non-countries whenever the address had no country or an old style one ("FRG", "Fr", "MA 02125", "Seoul National University"). The rules here keep a
token only when it is a known country name (after aliases), look for a country elsewhere in the address when the last token is not one, and
otherwise return None (the address has no country; the paper is then not counted for any country because of it).
"""
import re
import unicodedata

COUNTRIES = {
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh",
    "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei Darussalam", "Bulgaria",
    "Burkina Faso", "Burundi", "Cambodia", "Cameroon", "Canada", "Cape Verde", "Central African Republic", "Chad", "Chile", "China", "Colombia", "Comoros",
    "Congo", "Costa Rica", "Cote d'Ivoire", "Croatia", "Cuba", "Cyprus", "Czech Republic", "Democratic Republic Congo", "Denmark", "Djibouti", "Dominica",
    "Dominican Republic", "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini", "Ethiopia", "Fiji", "Finland", "France",
    "French Guiana", "French Polynesia", "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Greece", "Greenland", "Guadeloupe", "Guatemala", "Guinea", "Guyana",
    "Haiti", "Honduras", "Hong Kong", "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy", "Jamaica", "Japan", "Jordan",
    "Kazakhstan", "Kenya", "Kosovo", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania",
    "Luxembourg", "Macao", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Martinique", "Mauritania", "Mauritius", "Mexico", "Moldova",
    "Monaco", "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar", "Namibia", "Nepal", "Netherlands", "New Caledonia", "New Zealand", "Nicaragua",
    "Niger", "Nigeria", "North Korea", "North Macedonia", "Norway", "Oman", "Pakistan", "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru",
    "Philippines", "Poland", "Portugal", "Puerto Rico", "Qatar", "Reunion", "Romania", "Russian Federation", "Rwanda", "Saudi Arabia", "Senegal", "Serbia",
    "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Somalia", "South Africa", "South Korea", "South Sudan", "Spain", "Sri Lanka", "Sudan",
    "Suriname", "Sweden", "Switzerland", "Syrian Arab Republic", "Taiwan", "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo", "Trinidad and Tobago",
    "Tunisia", "Turkey", "Turkmenistan", "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States", "Uruguay", "Uzbekistan", "Vanuatu",
    "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe",
}
ALIASES = {
    "usa": "United States", "u.s.a.": "United States", "us": "United States", "u.s.": "United States", "united states of america": "United States",
    "frg": "Germany", "fr": "France", "uk": "United Kingdom", "u.k.": "United Kingdom", "england": "United Kingdom", "scotland": "United Kingdom",
    "wales": "United Kingdom", "northern ireland": "United Kingdom", "great britain": "United Kingdom",
    "russia": "Russian Federation", "korea": "South Korea", "republic of korea": "South Korea", "korea, republic of": "South Korea",
    "south korea (republic of korea)": "South Korea", "czechia": "Czech Republic", "macau": "Macao", "turkiye": "Turkey", "türkiye": "Turkey",
    "viet nam": "Vietnam", "p.r. china": "China", "pr china": "China", "people's republic of china": "China", "people’s republic of china": "China",
    "peoples republic of china": "China", "china (people's republic of china)": "China", "iran, islamic republic of": "Iran", "islamic republic of iran": "Iran",
    "côte d'ivoire": "Cote d'Ivoire", "côte d’ivoire": "Cote d'Ivoire", "ivory coast": "Cote d'Ivoire", "brunei": "Brunei Darussalam",
    "democratic republic of the congo": "Democratic Republic Congo", "burma": "Myanmar", "holland": "Netherlands", "the netherlands": "Netherlands",
    "swaziland": "Eswatini", "macedonia": "North Macedonia", "syria": "Syrian Arab Republic", "lao pdr": "Laos", "palestinian territory": "Palestine",
}
_LOOKUP = {c.lower(): c for c in COUNTRIES} | ALIASES
US_ZIP = re.compile(r"^[A-Z]{2}\s?\d{5}(-\d{4})?$")          # "MA 02125", "NY 10027": a US state and ZIP code, no country written


def country_name(token):
    """the country a single token stands for, or None when it is not a country (a city, an institute, a postcode, ...)"""
    if not isinstance(token, str):
        return None
    t = token.strip()
    if US_ZIP.match(t):
        return "United States"
    return _LOOKUP.get(t.lower())


def country_of_affiliation(affiliation):
    """country of ONE Scopus affiliation string: the last comma part when it is a country, otherwise the nearest earlier part that is one, otherwise None"""
    if not isinstance(affiliation, str):
        return None
    for part in reversed([p.strip() for p in affiliation.split(",")]):
        c = country_name(part)
        if c:
            return c
    return None


# ---------------------------------------------------------------- institutions
# a part that names a unit inside an institution, not the institution
UNIT = re.compile(r"^(the\s+)?(dep(t|artment|artamento|artement)?\b|faculty|facultad|fakultät|division|div\b|group|section|unit\b|chair|lab\b|school of|college of|"
                  r"centre? for|institute of (the )?\w+ (science|engineering)s?$|key lab|state key lab|laboratory of|graduate school)", re.I)
TRUNC = {"univ", "univ.", "univ of", "university", "university of", "universidad de", "universidade de", "università di", "universität", "université de"}
KEYS = ["institut", "academy", "cnrs", "cnes", "nasa", "noaa", "consiglio", "council", "agency", "ministry", "survey", "observator", "laborator", "college",
        "polytechn", "school of", "center", "centre", "research"]


def institution_of_affiliation(affiliation):
    """institution of ONE affiliation: the first part containing 'univ' (a cut name such as 'Univ of, Delaware' is joined with the next part), otherwise the first
    part with an institution keyword that is not a department-like unit, otherwise the first part that is not a unit (the old rule took 'Department of Civil
    Engineering' as the institution)."""
    if affiliation.strip().lower().startswith("equal contrib"):          # a Scopus note, not an address
        return None
    parts = [p.strip() for p in affiliation.split(",") if p.strip()]
    for i, p in enumerate(parts):
        if "univ" in p.lower():
            if p.lower().rstrip(".") in {t.rstrip(".") for t in TRUNC} and i + 1 < len(parts):
                return f"{p.rstrip('.')} {parts[i + 1]}"
            return p
    keyed = [p for p in parts if any(k in p.lower() for k in KEYS) and not UNIT.match(p)]
    if keyed:
        return keyed[0]
    plain = [p for p in parts if not UNIT.match(p) and country_name(p) is None]
    if not plain:                                       # the address is only a country ("Spain") or a note ("Equal contributor"): no institution
        return None if country_name(parts[0]) or parts[0].lower().startswith("equal contrib") else parts[0]
    i = parts.index(plain[0])
    if i > 0 and i == max(parts.index(q) for q in plain) and UNIT.match(parts[i - 1]):   # only a city is left after the unit: "College of Engineering, Pune"
        return f"{parts[i - 1]}, {plain[0]}"
    return plain[0]


def institution_key(name):
    """the spelling-free key of an institution name: accents, case, 'The', 'Univ.'/'University', hyphens, apostrophes and spaces do not matter"""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = re.sub(r"^the\s+", "", s)
    s = re.sub(r"\buniv(ersity|\.)?(?=\W|$)", "univ", s)
    s = re.sub(r"\bsciences?\b", "science", s)
    key = re.sub(r"[^a-z0-9]", "", s)
    if "chineseacademy" in key and "univ" in key and "graduate" not in key:     # University of (the) Chinese Academy of Science(s) and its misspellings
        key = "univchineseacademyscience"
    return key


def canonical_names(names):
    """map every spelling to the most frequent spelling of its key (ties: the longest), so one institution has one name"""
    from collections import Counter, defaultdict
    groups = defaultdict(Counter)
    for n in names:
        groups[institution_key(n)][n] += 1
    best = {k: sorted(c.items(), key=lambda kv: (-kv[1], -len(kv[0]), kv[0]))[0][0] for k, c in groups.items()}
    return {n: re.sub(r"^[Tt]he\s+", "", best[institution_key(n)]) for n in set(names)}


# ---------------------------------------------------------------- a country from the same institution elsewhere in the data
def learn_institution_countries(affiliations, least=2, share=2 / 3):
    """{institution key: (country, institution name, votes)} learned from the affiliations of the data that DO name their country. An institution gets the
    country written in at least `least` of its addresses and in at least `share` of them; an institution seen in two countries about equally gets none.
    It gives a country to an address written without one ("Wuhan University, Wuhan" when other papers write "Wuhan University, Wuhan, China")."""
    from collections import Counter, defaultdict
    votes, names = defaultdict(Counter), {}
    for a in affiliations:
        c = country_of_affiliation(a)
        inst = institution_of_affiliation(a) if c and isinstance(a, str) else None
        if inst:
            k = institution_key(inst)
            votes[k][c] += 1
            names.setdefault(k, inst)
    out = {}
    for k, cnt in votes.items():
        c, n = cnt.most_common(1)[0]
        if n >= least and n >= share * sum(cnt.values()):
            out[k] = (c, names[k], n)
    return out


def country_with_fallback(affiliation, learned):
    """(country, how): the country written in the address ("address"), else the one learned for its institution ("institution"), else (None, None)"""
    c = country_of_affiliation(affiliation)
    if c:
        return c, "address"
    inst = institution_of_affiliation(affiliation) if isinstance(affiliation, str) and learned else None
    hit = learned.get(institution_key(inst)) if inst else None
    return (hit[0], "institution") if hit else (None, None)


# ---------------------------------------------------------------- parent organisations
# Large research organisations made of many institutes. Scopus names the institute ("Aerospace Information Research Institute, Chinese Academy of Sciences,
# Beijing, China"), so each institute is counted on its own; the parent lets them be counted together as well. A part of the address is matched, never the
# whole address, and a university that only carries the name ("University of Chinese Academy of Sciences", "Leibniz University Hannover") is not a member.
PARENTS = [(re.compile(rx, re.I), name) for rx, name in [
    (r"^(the )?chinese academy of sciences?$|^cas$|\b(institute|institutes|center|centre|station|observatory) of .*chinese academy of sciences?$|, cas$|\bof cas\b", "Chinese Academy of Sciences"),
    (r"chinese academy of agricultural sciences|\bcaas\b", "Chinese Academy of Agricultural Sciences"),
    (r"chinese academy of forestry", "Chinese Academy of Forestry"),
    (r"\bcnrs\b|centre national de la recherche scientifique", "CNRS (France)"),
    (r"\binrae?\b|institut national de (la )?recherche (pour l'agriculture|agronomique)", "INRAE (France)"),
    (r"institut de recherche pour le d[ée]veloppement|^ird$", "IRD (France)"),
    (r"\bcsic\b|consejo superior de investigaciones cient[ií]ficas|spanish national research council", "CSIC (Spain)"),
    (r"consiglio nazionale delle ricerche|national research council of italy|^cnr$|\bcnr[- ]", "CNR (Italy)"),
    (r"max[- ]planck", "Max Planck Society"),
    (r"helmholtz", "Helmholtz Association"),
    (r"fraunhofer", "Fraunhofer Society"),
    (r"leibniz[- ]?(institut|institute|centre|center|zentrum)", "Leibniz Association"),
    (r"russian academy of sciences|^ras$", "Russian Academy of Sciences"),
    (r"polish academy of sciences", "Polish Academy of Sciences"),
    (r"czech academy of sciences|academy of sciences of the czech republic", "Czech Academy of Sciences"),
    (r"academia sinica", "Academia Sinica"),
    (r"council of scientific (and|&) industrial research|^csir[- ]|\bcsir-", "CSIR (India)"),
    (r"council for scientific (and|&) industrial research", "CSIR (South Africa)"),
    (r"indian council of agricultural research|\bicar\b", "ICAR (India)"),
    (r"indian space research organi[sz]ation|\bisro\b", "ISRO (India)"),
    (r"defen[cs]e research (and|&) development organi[sz]ation|\bdrdo\b", "DRDO (India)"),
    (r"\bcsiro\b|commonwealth scientific and industrial research organi[sz]ation", "CSIRO (Australia)"),
    (r"^nasa\b|\bnasa\b", "NASA"),
    (r"\bnoaa\b|national oceanic and atmospheric administration", "NOAA"),
    (r"\busgs\b|u\.? ?s\.? geological survey|united states geological survey", "U.S. Geological Survey"),
    (r"\busda\b|agricultural research service|(united states|u\.? ?s\.?) department of agriculture", "U.S. Department of Agriculture"),
    (r"\briken\b", "RIKEN (Japan)"),
]]
_MEMBER_OF_NAME_ONLY = re.compile(r"^(the )?(univ|university|universit)", re.I)


def parent_of_affiliation(affiliation):
    """the parent organisation named in ONE affiliation (see PARENTS), or None"""
    if not isinstance(affiliation, str):
        return None
    for part in (p.strip() for p in affiliation.split(",")):
        if not part or _MEMBER_OF_NAME_ONLY.match(part):
            continue
        for rx, name in PARENTS:
            if rx.search(part):
                return name
    return None
