"""Sheet "Country_Collaboration": collaboration between countries, in two tables (the two Excel queries Chord_Pairs and Chord_Others, joined into one task).
1. Country_Collaboration.csv = Chord_Pairs: the number of joint papers of every pair of countries.
   Excel: reference of Countries; keep EID and Country; join the table with itself on EID (inner); keep the rows with from_country < to_country (alphabetical, so every pair once); group by the pair and count the papers.
2. Country_Collaboration_chord.csv = Chord_Others: the chord diagram made readable: the 6 countries with most documents stay, every other country becomes "Rest of the World".
   Excel: reference of Chord_Pairs; add from_node / to_node; put the two nodes of a link in alphabetical order; Group By with the SUM of papers; the Rest-Rest row is kept but is not drawn.
Input : Countries/Countries.csv (run Countries.py first)        Output: Country_Collaboration.csv (from_country, to_country, papers), Country_Collaboration_chord.csv (from_node, to_node, links)
Run   : python3 Country_Collaboration.py
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SHEETS = HERE.parent                                         # the folder that holds 01_Clean_Data and one folder per sheet
CLEAN = SHEETS / "01_Clean_Data" / "clean_main_data.csv"     # result of the cleaning step
OUT = HERE / "Country_Collaboration.csv"
TEXT = {"Author(s) ID": str, "Author ID": str, "PubMed ID": str, "ISSN": str, "ISBN": str}


def read_csv(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype=TEXT, **kw)


def write(df, path=OUT):
    df = df.round(2).apply(lambda c: c.map(lambda v: round(v, 2) if isinstance(v, float) else v) if c.dtype == object else c)
                                                             # every decimal number with at most 2 decimal places, also in mixed text/number columns
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"written {path.name}: {len(df)} rows, {df.shape[1]} columns")


c = read_csv(SHEETS / "Countries" / "Countries.csv")[["EID", "Country"]].drop_duplicates()
m = c.merge(c, on="EID")
m = m[m["Country_x"] < m["Country_y"]]
pairs = m.groupby(["Country_x", "Country_y"]).size().rename("papers").reset_index().rename(columns={"Country_x": "from_country", "Country_y": "to_country"})
pairs = pairs.sort_values(["papers", "from_country", "to_country"], ascending=[False, True, True], kind="stable").reset_index(drop=True)
print(f"{len(pairs)} pairs of countries, {pairs['papers'].sum()} links (a paper with n countries gives n(n-1)/2 links)")
write(pairs)

# 2. the chord table (uses the pairs above)
countries = read_csv(SHEETS / "Countries" / "Countries.csv")[["EID", "Country"]].drop_duplicates()
top = countries["Country"].value_counts().head(6).index.tolist()
REST = "Rest of the World"
node = lambda c: c if c in top else REST
a = pairs["from_country"].map(node)
b = pairs["to_country"].map(node)
pairs["from_node"] = [min(x, y) for x, y in zip(a, b)]
pairs["to_node"] = [max(x, y) for x, y in zip(a, b)]
others = pairs.groupby(["from_node", "to_node"])["papers"].sum().rename("links").reset_index()
others = others.sort_values(["links", "from_node", "to_node"], ascending=[False, True, True], kind="stable").reset_index(drop=True)
print("top 6 countries:", ", ".join(top), f"| total links {others['links'].sum()} (equals the sum over all pairs: {pairs['papers'].sum()})")
write(others, HERE / "Country_Collaboration_chord.csv")
