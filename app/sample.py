"""A made-up Scopus export to try the application with (standard library only): every paper, author, institution and source in it is invented.
It has the columns and formats of a real Scopus CSV export (with References and two merged searches, Query_IDs), and the things real data has: growth over
the years, a current year that is not complete and early-access papers dated next year, a few core journals that carry most papers (Bradford), many authors
with one paper (Lotka), duplicates and a record without authors for the cleaning to remove, institutes of a large parent organisation, and addresses
written without their country. The same seed gives the same file, apart from the years, which follow today's date.

    python3 the_data_app.py sample [--location FOLDER]       a project called "Sample project" with this data
    window: opening screen, "Try the sample project"
"""
import csv
import math
import random
from datetime import date
from pathlib import Path

from . import dataset, project as projects

COLUMNS = ["Authors", "Author full names", "Author(s) ID", "Title", "Year", "Source title", "Volume", "Issue", "Art. No.", "Page start", "Page end", "Cited by", "DOI",
           "Link", "Affiliations", "Authors with affiliations", "Abstract", "Author Keywords", "Index Keywords", "Funding Details", "Funding Texts", "References",
           "Correspondence Address", "Publisher", "ISSN", "Language of Original Document", "Abbreviated Source Title", "Document Type", "Publication Stage",
           "Open Access", "Source", "EID", "Query_IDs", "N_Queries"]

SURNAMES = ["Abara", "Bellini", "Chandra", "Dubois", "Eriksen", "Fong", "Garcia", "Haddad", "Ivanova", "Jensen", "Kowalski", "Li", "Moreau", "Nakamura", "Okafor",
            "Petrov", "Quispe", "Rossi", "Sato", "Tanaka", "Uddin", "Varga", "Wang", "Xu", "Yilmaz", "Zhang", "Kumar", "Silva", "Novak", "Hughes", "Mensah", "Larsen",
            "Romero", "Fischer", "Kim", "Park", "Sharma", "Ahmed", "Costa", "Schmidt", "Chen", "Liu", "Zhou", "Singh", "Patel", "Murphy", "Lopez", "Weber", "Ito", "Das"]
GIVEN = ["Amara", "Bruno", "Chen", "Dana", "Elif", "Farid", "Grace", "Hana", "Ivan", "Jun", "Kofi", "Lena", "Mateo", "Nadia", "Omar", "Priya", "Rui", "Sara", "Tomas",
         "Uma", "Vera", "Wei", "Yara", "Zoe", "Arjun", "Mei", "Jonas", "Ines", "Kenji", "Leila", "Marco", "Noor", "Pavel", "Rosa", "Sven", "Tara", "Yusuf", "Lin"]
# (institution, city, postcode, country, parent organisation or None)
INSTITUTIONS = [
    ("Wuhan University", "Wuhan", "430072", "China", None), ("Tsinghua University", "Beijing", "100084", "China", None),
    ("Institute of Geographic Sciences and Natural Resources Research, Chinese Academy of Sciences", "Beijing", "100101", "China", "CAS"),
    ("Aerospace Information Research Institute, Chinese Academy of Sciences", "Beijing", "100094", "China", "CAS"),
    ("Nanjing Institute of Geography and Limnology, Chinese Academy of Sciences", "Nanjing", "210008", "China", "CAS"),
    ("University of Chinese Academy of Sciences", "Beijing", "100049", "China", None), ("Hohai University", "Nanjing", "210098", "China", None),
    ("Indian Institute of Technology Bombay", "Mumbai", "400076", "India", None), ("Indian Institute of Science", "Bengaluru", "560012", "India", None),
    ("National Remote Sensing Centre, ISRO", "Hyderabad", "500037", "India", "ISRO"), ("National Institute of Technology Delhi", "Delhi", "110036", "India", None),
    ("University of Maryland", "College Park", "MD 20742", "United States", None), ("Stanford University", "Stanford", "CA 94305", "United States", None),
    ("NASA Goddard Space Flight Center", "Greenbelt", "MD 20771", "United States", "NASA"), ("U.S. Geological Survey", "Reston", "VA 20192", "United States", "USGS"),
    ("Delft University of Technology", "Delft", "2628 CD", "Netherlands", None), ("Wageningen University", "Wageningen", "6708 PB", "Netherlands", None),
    ("Université de Toulouse", "Toulouse", "31400", "France", None), ("CNRS, Laboratoire d'Etudes en Géophysique et Océanographie Spatiales", "Toulouse", "31400", "France", "CNRS"),
    ("German Aerospace Center", "Wessling", "82234", "Germany", None), ("Helmholtz Centre for Environmental Research - UFZ", "Leipzig", "04318", "Germany", "Helmholtz"),
    ("University of Bonn", "Bonn", "53115", "Germany", None), ("University of Bristol", "Bristol", "BS8 1SS", "United Kingdom", None),
    ("Imperial College London", "London", "SW7 2AZ", "United Kingdom", None), ("Politecnico di Milano", "Milan", "20133", "Italy", None),
    ("Consiglio Nazionale delle Ricerche, Istituto di Ricerca per la Protezione Idrogeologica", "Perugia", "06128", "Italy", "CNR"),
    ("Universidad Politécnica de Madrid", "Madrid", "28040", "Spain", None), ("University of Tokyo", "Tokyo", "113-8654", "Japan", None),
    ("Seoul National University", "Seoul", "08826", "South Korea", None), ("University of São Paulo", "São Paulo", "05508-000", "Brazil", None),
    ("University of Melbourne", "Melbourne", "VIC 3010", "Australia", None), ("CSIRO Land and Water", "Canberra", "ACT 2601", "Australia", "CSIRO"),
    ("University of Nairobi", "Nairobi", "00100", "Kenya", None), ("University of Cape Town", "Cape Town", "7701", "South Africa", None),
    ("McGill University", "Montreal", "H3A 0G4", "Canada", None), ("Tehran University", "Tehran", "14179", "Iran", None),
    ("Istanbul Technical University", "Istanbul", "34469", "Turkey", None), ("Universiti Teknologi Malaysia", "Johor Bahru", "81310", "Malaysia", None),
]
UNITS = ["Department of Civil Engineering", "School of Remote Sensing and Information Engineering", "Department of Geography", "State Key Laboratory of Water Resources",
         "Department of Earth Sciences", "Faculty of Geo-Information Science", "Department of Hydrology", "Centre for Water Research", ""]
SOURCES = [("Remote Sensing of Environment", "Remote Sens. Environ.", "Elsevier Inc."), ("Remote Sensing", "Remote Sens.", "MDPI"),
           ("Journal of Hydrology", "J. Hydrol.", "Elsevier B.V."), ("Water Resources Research", "Water Resour. Res.", "John Wiley and Sons Inc"),
           ("IEEE Transactions on Geoscience and Remote Sensing", "IEEE Trans Geosci Remote Sens", "Institute of Electrical and Electronics Engineers Inc."),
           ("International Geoscience and Remote Sensing Symposium (IGARSS)", "Int Geosci Remote Sens Symp (IGARSS)", "Institute of Electrical and Electronics Engineers Inc."),
           ("Hydrology and Earth System Sciences", "Hydrol. Earth Syst. Sci.", "Copernicus GmbH"), ("Science of the Total Environment", "Sci. Total Environ.", "Elsevier B.V."),
           ("ISPRS Journal of Photogrammetry and Remote Sensing", "ISPRS J. Photogramm. Remote Sens.", "Elsevier B.V."), ("Water (Switzerland)", "Water", "MDPI"),
           ("Natural Hazards", "Nat. Hazards", "Springer Science and Business Media B.V."), ("Journal of Flood Risk Management", "J. Flood Risk Manage.", "John Wiley and Sons Inc"),
           ("Environmental Modelling and Software", "Environ. Model. Softw.", "Elsevier Ltd"), ("Geophysical Research Letters", "Geophys. Res. Lett.", "John Wiley and Sons Inc")]
SOURCES += [(f"Sample Journal of Earth Data {i}", f"Sample J. Earth Data {i}", "Sample Publisher") for i in range(1, 37)]
TOPICS = ["flood mapping", "surface water extent", "river discharge", "soil moisture", "drought monitoring", "lake level", "snow cover", "evapotranspiration",
          "water quality", "groundwater storage", "urban flooding", "wetland change"]
METHODS = ["deep learning", "random forest", "Sentinel-1 SAR", "Landsat time series", "Google Earth Engine", "hydrological modelling", "uncertainty quantification",
           "data assimilation", "conformal prediction", "transfer learning", "optical and radar fusion", "change detection"]
PLACES = ["the Yangtze basin", "the Ganges delta", "the Mississippi river", "East Africa", "the Rhine", "the Mekong", "Central Europe", "southern Brazil", "Australia", "global scale"]
OPEN_ACCESS = ["", "", "", "All Open Access; Gold Open Access", "All Open Access; Green Open Access", "All Open Access; Hybrid Gold Open Access",
               "All Open Access; Bronze Open Access", "All Open Access; Gold Open Access; Green Open Access"]
DOC_TYPES = ["Article"] * 70 + ["Conference paper"] * 16 + ["Review"] * 7 + ["Book chapter"] * 4 + ["Letter", "Editorial", "Note"]
LANGUAGES = ["English"] * 46 + ["Chinese", "Chinese", "Spanish", "Portuguese"]


def _papers_per_year(first, last):
    """logistic growth from `first` to `last`; the current year holds about 3/4 of a year, the early-access year only a few papers"""
    out = {}
    for y in range(first, last + 1):
        out[y] = max(1, round(4 + 70 / (1 + math.exp(-0.28 * (y - (last - 9))))))
    out[last + 1] = max(2, round(out[last] * 0.75))             # the current year: not complete yet
    out[last + 2] = 4                                            # early access: next year's date
    return out


def make_rows(seed=7, n_years=32, today=None):
    rng = random.Random(seed)
    this = (today or date.today()).year
    first, last = this - n_years, this - 1
    authors = []
    for i in range(2000):                                         # an author: name, Scopus ID, home institutions (most have one, some two)
        homes = [rng.randrange(len(INSTITUTIONS))]
        if rng.random() < 0.12:
            homes.append(rng.randrange(len(INSTITUTIONS)))
        authors.append((rng.choice(SURNAMES), rng.choice(GIVEN) + (" " + rng.choice(GIVEN)[0] + "." if rng.random() < 0.3 else ""), str(57000000000 + rng.randrange(10 ** 9)), homes))
    weight = [1 / (k + 30) ** 1.05 for k in range(len(authors))]     # a few authors write many papers (about 3% of all), half write one (Lotka)
    src_weight = [1 / (k + 1) ** 1.25 for k in range(len(SOURCES))]  # a few sources carry most papers (Bradford)
    refs = []
    for i in range(320):
        a = rng.sample(SURNAMES, rng.randint(1, 3))
        refs.append(f"{'; '.join(x + ' ' + rng.choice(GIVEN)[0] + '.' for x in a)}, {rng.choice(METHODS).capitalize()} for {rng.choice(TOPICS)}, "
                    f"{rng.choice(SOURCES[:14])[0]}, {rng.randint(1, 600)}, pp. {rng.randint(1, 900)}-{rng.randint(901, 990)}, ({rng.randint(first - 15, last)})")
    rows, n = [], 0
    for year, count in _papers_per_year(first, last).items():
        for _ in range(count):
            n += 1
            team = []
            for k in rng.choices(range(len(authors)), weight, k=rng.choice([1, 2, 2, 3, 3, 3, 4, 4, 5, 6, 8])):
                if k not in team:
                    team.append(k)
            topic, method, place = rng.choice(TOPICS), rng.choice(METHODS), rng.choice(PLACES)
            src = SOURCES[rng.choices(range(len(SOURCES)), src_weight)[0]]
            age = max(this - year, 0)
            cited = int(rng.lognormvariate(0.6, 1.1) * (age ** 1.1)) if age else rng.randint(0, 2)
            affs, with_affs = [], []
            for k in team:
                sur, giv, aid, homes = authors[k]
                mine = []
                for h in homes:
                    inst, city, post, country, _ = INSTITUTIONS[h]
                    unit = rng.choice(UNITS)
                    parts = ([unit] if unit else []) + [inst, city, post]
                    if not (h == 0 and rng.random() < 0.3):              # some addresses of Wuhan University are written without their country
                        parts.append(country)
                    mine.append(", ".join(parts))
                with_affs.append(f"{sur} {giv[0]}., " + ", ".join(mine))
                for m in mine:
                    if m not in affs:
                        affs.append(m)
            lead = authors[team[0]]
            kw = sorted({topic, method, place.replace("the ", "")} | set(rng.sample(TOPICS + METHODS, 2)))
            stage = "Article in press" if year > this else "Final"
            queries = ["Q01"] + (["Q02"] if rng.random() < 0.3 else []) + (["Q03"] if "conformal" in method or "uncertainty" in method else [])
            rows.append({
                "Authors": "; ".join(f"{authors[k][0]} {authors[k][1][0]}." for k in team),
                "Author full names": "; ".join(f"{authors[k][0]}, {authors[k][1]} ({authors[k][2]})" for k in team),
                "Author(s) ID": "; ".join(authors[k][2] for k in team),
                "Title": f"{method.capitalize()} for {topic} in {place}: a sample study {n}",
                "Year": str(year), "Source title": src[0], "Volume": str(rng.randint(1, 300)), "Issue": str(rng.randint(1, 12)), "Art. No.": str(100000 + n),
                "Page start": "", "Page end": "", "Cited by": str(cited) if cited else "", "DOI": f"10.9999/sample.{year}.{n:05d}",
                "Link": f"https://www.example.org/sample/{n}", "Affiliations": "; ".join(affs), "Authors with affiliations": "; ".join(with_affs),
                "Abstract": f"This made-up abstract describes how {method} is used for {topic} in {place}. It exists only to try The Data Application.",
                "Author Keywords": "; ".join(kw), "Index Keywords": "; ".join(sorted({topic, "remote sensing", method})),
                "Funding Details": "Sample Science Foundation, (SSF-0001)" if rng.random() < 0.4 else "", "Funding Texts": "",
                "References": "; ".join(rng.sample(refs, rng.randint(5, 30))),
                "Correspondence Address": f"{lead[1][0]}. {lead[0]}; {affs[0]}; email: author{n}@example.org" if rng.random() < 0.85 else "",
                "Publisher": src[2], "ISSN": f"{rng.randint(1000, 9999)}{rng.randint(1000, 9999)}", "Language of Original Document": rng.choice(LANGUAGES),
                "Abbreviated Source Title": src[1], "Document Type": rng.choice(DOC_TYPES), "Publication Stage": stage, "Open Access": rng.choice(OPEN_ACCESS),
                "Source": "Scopus", "EID": f"2-s2.0-{85000000000 + n}", "Query_IDs": ";".join(queries), "N_Queries": str(len(queries))})
    rows.append({**rows[5], "EID": "2-s2.0-84999999998", "Cited by": "1"})             # the same paper twice (other EID): the cleaning keeps one
    rows.append({**rows[6], "EID": "2-s2.0-84999999999", "Authors": "", "Author full names": "", "Author(s) ID": "", "Title": "A record without authors"})
    return rows


def write_csv(path, seed=7, today=None):
    rows = make_rows(seed, today=today)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


# made-up ASJC codes for the sources of the sample (the real ones are in Elsevier's Scopus Source List); the last sources are left out on purpose
SAMPLE_ASJC = ["1903; 2305", "1903; 1900", "2312", "2312; 2305", "1900; 2208", "2208; 1903", "1904; 2312", "2304; 2310", "1903; 1706", "2312; 1105",
               "1902; 2305", "2305; 3305", "1706; 2302", "1900"] + ["1700; 2600", "2200", "1100; 2303", "3100", "1800; 1700", "3300", "2500; 2200"] * 4


def write_source_list(path):
    """a small made-up stand-in for the Scopus Source List (its column headings, made-up ISSNs and ASJC codes), for the sheet Subject_Areas"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Source Title", "ISSN", "EISSN", "All Science Journal Classification Codes (ASJC)"])
        for k, (title, _, _) in enumerate(SOURCES[:len(SOURCES) - 4]):
            w.writerow([title, f"9{k:07d}", "", SAMPLE_ASJC[k % len(SAMPLE_ASJC)]])
    return path


def create_sample_project(location=None):
    """a new project "Sample project" (or "Sample project 2", ...) with the made-up export as its main data; returns (Project, None) or (None, error)"""
    names = {p["name"].lower() for p in projects.list_projects() if p["exists"]}
    name, k = "Sample project", 1
    while name.lower() in names:
        k += 1
        name = f"Sample project {k}"
    pr, err = projects.create(name, location)
    if pr is None:
        return None, err
    dst = pr.raw / "sample_scopus_export.csv"
    n = write_csv(dst)
    dataset.register(pr, dst, "made up by The Data Application (app/sample.py)", n)
    write_source_list(pr.dir / "data" / "source_list" / "sample_source_list.csv")
    return pr, None
