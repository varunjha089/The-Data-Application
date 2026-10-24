"""common/names.py : shared name rules for countries and institutions (used by 01_clean_data.py and Affiliations.py).

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
