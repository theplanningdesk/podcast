#!/usr/bin/env python3
"""Weekly paper scout for the Wednesday research clip.

Searches OpenAlex for recent open-access papers on supply chain planning and design, ranks them for a
planner audience (Nordic/DACH authors and established journals first), and saves a shortlist plus the
full text of the top papers whose licence allows redistribution (Creative Commons or public domain).
The research writer reads the output from the "sources" branch:

  papers/shortlist.md      ranked candidates with abstract, authors, licence and links
  papers/shortlist.json    the same as data
  papers/<openalex id>.txt full text of the top candidates (licensed for redistribution only)

  python tools/paper_scout.py <out_dir>

Optional env: OPENALEX_API_KEY (free key; without one OpenAlex allows a small daily allowance, which a
weekly run fits in), SCOUT_DAYS (look-back window, default 75), SCOUT_TEXTS (full texts, default 8).
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

API = "https://api.openalex.org/works"
MAILTO = "theplanningdesk.podcast@gmail.com"
UA = f"ThePlanningDeskScout/1.0 (+https://theplanningdesk.github.io/podcast; mailto:{MAILTO})"
ROOT = Path(__file__).resolve().parents[1]

# One OpenAlex query per lane; title and abstract search, boolean OR.
LANES = {
    "Forecasting": '"demand forecasting" OR "probabilistic forecasting" OR "forecast accuracy" OR "demand sensing"',
    "Inventory": '"inventory management" OR "safety stock" OR "inventory optimization" OR "multi-echelon" OR "spare parts inventory"',
    "Production planning and scheduling": '"production planning" OR "production scheduling" OR "lot sizing" OR "master planning" OR "capacity planning"',
    "S&OP and IBP": '"sales and operations planning" OR "integrated business planning" OR "S&OP" OR "tactical planning"',
    "Network design": '"supply chain network design" OR "facility location" OR "distribution network design" OR "network optimization" OR "footprint"',
    "Resilience and risk": '"supply chain resilience" OR "supply chain disruption" OR "bullwhip" OR "supply chain risk"',
    "AI in planning": '"supply chain" AND ("large language model" OR "machine learning" OR "reinforcement learning" OR "artificial intelligence")',
}

# Licences that allow keeping and sharing the text with attribution.
OPEN_LICENCES = {"cc-by", "cc-by-sa", "cc0", "public-domain", "cc-by-nc", "cc-by-nc-sa", "cc-by-nd", "cc-by-nc-nd"}
NORDIC_DACH = {"SE", "NO", "DK", "FI", "IS", "DE", "AT", "CH"}
JOURNALS = [
    "international journal of production economics", "european journal of operational research",
    "international journal of production research", "international journal of operations & production management",
    "journal of operations management", "production and operations management", "manufacturing & service operations management",
    "management science", "operations research", "transportation science", "international journal of forecasting",
    "omega", "computers & operations research", "computers & industrial engineering", "transportation research part e",
    "supply chain management: an international journal", "journal of business logistics",
    "international journal of physical distribution & logistics management", "euro journal on transportation and logistics",
    "supply chain analytics", "decision support systems", "annals of operations research", "or spectrum",
    "flexible services and manufacturing journal", "journal of purchasing and supply management", "production planning & control",
    "journal of scheduling", "iise transactions", "naval research logistics", "foresight", "journal of the operational research society",
]
SKIP_PUBLISHERS = ("mdpi",)  # uneven peer review; the show wants authority
# Vendor and employer names: their papers are marketing, and the show stays clear of them.
SKIP_AFFILIATIONS = ("optilon", "toolsgroup", "o9 solutions", "kinaxis", "blue yonder", "relex", "slimstock",
                     "sap se", "oracle", "anaplan", "logility", "e2open", "optilogic", "coupa", "llamasoft")
# A paper must be about supply chains: two distinct domain terms in title and abstract, one in the title.
DOMAIN = ("supply chain", "inventor", "forecast", "demand planning", "production planning", "scheduling", "lot siz",
          "logistic", "warehous", "distribution network", "distribution center", "distribution centre", "procurement",
          "sourcing", "s&op", "sales and operations", "integrated business planning", "bullwhip", "safety stock",
          "facility location", "network design", "manufactur", "replenish", "spare part", "capacity planning",
          "master planning", "aggregate planning", "order fulfil", "lead time", "supplier", "retail")
SKIP_TITLE = ("sap ", "sap-", "kinaxis", "o9 ", "blue yonder", "oracle", "anaplan", "relex", "toolsgroup", "optilon")
SKIP_VENUES = ("zenodo",)
PRACTICE = ("case study", "case company", "industrial", "real-world", "real world", "empirical", "field", "practitioner",
            "company data", "retailer", "manufacturer", "we collaborate", "implementation", "sweden", "swedish", "germany",
            "german", "norway", "denmark", "finland", "austria", "switzerland")


def abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    words = sorted((pos, w) for w, ps in inv.items() for pos in ps)
    return " ".join(w for _, w in words)


def search(lane: str, query: str, since: str, key: str | None) -> list[dict]:
    params = {
        "filter": f"from_publication_date:{since},is_oa:true,type:article|preprint,title_and_abstract.search:{query}",
        "select": "id,doi,display_name,publication_date,type,authorships,primary_location,best_oa_location,locations,"
                  "abstract_inverted_index,cited_by_count,language",
        "sort": "publication_date:desc",
        "per_page": "50",
        "mailto": MAILTO,
    }
    if key:
        params["api_key"] = key
    for attempt in range(3):
        r = requests.get(API, params=params, headers={"User-Agent": UA}, timeout=60)
        if r.status_code == 200:
            return [dict(w, lane=lane) for w in r.json().get("results", [])]
        print(f"  {lane}: HTTP {r.status_code} {r.text[:200]}")
        time.sleep(5 * (attempt + 1))
    return []


def describe(w: dict) -> dict:
    best = w.get("best_oa_location") or {}
    prim = w.get("primary_location") or {}
    src = (prim.get("source") or best.get("source") or {})
    venue = src.get("display_name") or ""
    publisher = (src.get("host_organization_name") or "")
    authors, insts, countries = [], [], set()
    for a in w.get("authorships") or []:
        authors.append((a.get("author") or {}).get("display_name", ""))
        for i in a.get("institutions") or []:
            if i.get("display_name") and i["display_name"] not in insts:
                insts.append(i["display_name"])
            if i.get("country_code"):
                countries.add(i["country_code"])
        countries.update(a.get("countries") or [])
    pdfs = [l.get("pdf_url") for l in [best] + (w.get("locations") or []) if l and l.get("pdf_url")]
    lic = (best.get("license") or "").lower() or next(((l.get("license") or "").lower() for l in w.get("locations") or [] if l.get("license")), "")
    text = abstract(w.get("abstract_inverted_index"))
    return {
        "openalex": w["id"].rsplit("/", 1)[-1],
        "doi": w.get("doi") or "",
        "title": w.get("display_name") or "",
        "date": w.get("publication_date") or "",
        "type": "preprint" if w.get("type") == "preprint" else "article",
        "venue": venue,
        "publisher": publisher,
        "authors": authors,
        "institutions": insts[:8],
        "countries": sorted(countries),
        "licence": lic,
        "landing": best.get("landing_page_url") or prim.get("landing_page_url") or w.get("doi") or "",
        "pdfs": list(dict.fromkeys(pdfs)),
        "cited_by": w.get("cited_by_count") or 0,
        "language": w.get("language") or "",
        "abstract": text,
        "lanes": [w["lane"]],
    }


def score(p: dict) -> tuple[float, list[str]]:
    why, s = [], 0.0
    if NORDIC_DACH & set(p["countries"]):
        s += 3; why.append("Nordic/DACH authors (" + ", ".join(sorted(NORDIC_DACH & set(p["countries"]))) + ")")
    v = p["venue"].lower()
    if any(j in v for j in JOURNALS):
        s += 2; why.append("established journal")
    elif p["type"] == "preprint":
        why.append("preprint, not peer-reviewed")
    hay = (p["title"] + " " + p["abstract"]).lower()
    hits = sorted({k for k in PRACTICE if k in hay})
    if hits:
        s += min(2, len(hits) * 0.7); why.append("practice signals: " + ", ".join(hits[:4]))
    if re.search(r"\d+(\.\d+)?\s?%", p["abstract"]):
        s += 1; why.append("reports a quantified result")
    if p["licence"] in OPEN_LICENCES:
        s += 1
    if len(p["lanes"]) > 1:
        s += 0.5
    s += min(1.0, p["cited_by"] / 10)
    return round(s, 2), why


def keep(p: dict, used: set[str]) -> bool:
    if p["language"] and p["language"] != "en":
        return False
    if not p["abstract"] or len(p["abstract"]) < 400:
        return False
    if any(x in p["publisher"].lower() for x in SKIP_PUBLISHERS) or any(x in p["venue"].lower() for x in SKIP_VENUES):
        return False
    title, hay = p["title"].lower(), (p["title"] + " " + p["abstract"]).lower()
    if any(x in title + " " for x in SKIP_TITLE):
        return False
    if not any(d in title for d in DOMAIN) or len({d for d in DOMAIN if d in hay}) < 2:
        return False
    aff = " ".join(p["institutions"]).lower()
    if any(x in aff for x in SKIP_AFFILIATIONS):
        return False
    if (p["doi"] and p["doi"].lower() in used) or p["openalex"] in used:
        return False
    return True


def fetch_text(p: dict) -> str:
    from pypdf import PdfReader
    for url in p["pdfs"]:
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
            if r.status_code != 200 or not r.content.startswith(b"%PDF"):
                continue
            reader = PdfReader(io.BytesIO(r.content))
            text = "\n".join((pg.extract_text() or "") for pg in reader.pages[:60])
            text = re.sub(r"[ \t]+", " ", text)
            if len(text) > 5000:
                return text[:180_000]
        except Exception as err:  # noqa: BLE001
            print(f"  pdf failed {url}: {err}")
    return ""


def used_ids() -> set[str]:
    out = set()
    for f in (ROOT / "concepts").glob("*.json"):
        try:
            src = json.loads(f.read_text(encoding="utf-8")).get("source") or {}
        except Exception:  # noqa: BLE001
            continue
        for k in ("doi", "openalex"):
            if src.get(k):
                out.add(str(src[k]).lower())
    return out


def main(out_dir: str) -> int:
    out = Path(out_dir) / "papers"
    out.mkdir(parents=True, exist_ok=True)
    days = int(os.environ.get("SCOUT_DAYS", "75"))
    n_texts = int(os.environ.get("SCOUT_TEXTS", "8"))
    since = (date.today() - timedelta(days=days)).isoformat()
    key = os.environ.get("OPENALEX_API_KEY") or None
    used = used_ids()
    found: dict[str, dict] = {}
    status = {}
    for lane, q in LANES.items():
        rows = search(lane, q, since, key)
        status[lane] = len(rows)
        print(f"{lane}: {len(rows)} results")
        for w in rows:
            p = describe(w)
            if p["openalex"] in found:
                found[p["openalex"]]["lanes"].append(lane)
            else:
                found[p["openalex"]] = p
        time.sleep(1)
    cands = [p for p in found.values() if keep(p, used)]
    for p in cands:
        p["score"], p["why"] = score(p)
    cands.sort(key=lambda p: p["date"], reverse=True)
    cands.sort(key=lambda p: p["score"], reverse=True)
    cands = cands[:25]
    texts = 0
    for p in cands:
        p["text_file"] = ""
        if texts >= n_texts or p["licence"] not in OPEN_LICENCES:
            continue
        t = fetch_text(p)
        if t:
            head = (f"TITLE: {p['title']}\nAUTHORS: {', '.join(p['authors'])}\nVENUE: {p['venue']} ({p['date']})\n"
                    f"DOI: {p['doi']}\nLICENCE: {p['licence']}\nLINK: {p['landing']}\n\n")
            (out / f"{p['openalex']}.txt").write_text(head + t, encoding="utf-8")
            p["text_file"] = f"papers/{p['openalex']}.txt"
            texts += 1
    (out / "shortlist.json").write_text(json.dumps({"generated": date.today().isoformat(), "since": since,
                                                    "lanes": status, "papers": cands}, ensure_ascii=False, indent=1), encoding="utf-8")
    md = [f"# Paper shortlist, {date.today().isoformat()}", "",
          f"Open-access papers published since {since}, ranked for planners. Full text is saved only where the licence allows it "
          f"(Creative Commons or public domain); {texts} of {len(cands)} have it. Results per lane: "
          + ", ".join(f"{k} {v}" for k, v in status.items()) + ".", ""]
    for i, p in enumerate(cands, 1):
        md += [f"## {i}. {p['title']}", "",
               f"{', '.join(p['authors'][:6])}{' et al.' if len(p['authors']) > 6 else ''}. {p['venue'] or 'Repository'}, {p['date']}. "
               f"{p['type']}, licence {p['licence'] or 'unknown'}, cited {p['cited_by']}.",
               f"Institutions: {'; '.join(p['institutions'][:5]) or 'unknown'} ({', '.join(p['countries']) or '?'})",
               f"Lanes: {', '.join(p['lanes'])}. Score {p['score']}: {'; '.join(p['why']) or 'no signals'}.",
               f"Link: {p['doi'] or p['landing']}" + (f" · Full text: {p['text_file']}" if p['text_file'] else " · No full text saved"),
               "", p["abstract"][:1800], ""]
    (out / "shortlist.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Shortlist: {len(cands)} papers, {texts} full texts.")
    return 0 if cands else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "build/scout"))
