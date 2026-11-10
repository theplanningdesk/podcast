"""Pull the scrobblers' starting pages into one digest the agents can read.

The scheduled scrobblers can't fetch these pages themselves while Jim sleeps
(each fetch waits for an approval nobody gives), but they can read GitHub
from their shell. This script runs in GitHub Actions, where the open web is
reachable, and writes:

  out/latest.json  every item: lane, source, title, link, published, summary, highlights
  out/latest.md    the same, grouped by lane and source, for reading
  out/status.json  per-source result, so a broken feed shows up

Four lanes, written to the digest in this order (reordered 10 Nov 2026, when the
briefs had drifted to about 70% freight news; see
claude/research/rebalance-proposal-2026-11-10.md in the Project):
  planning    planning, network design, AI and tech, and supply chain trade press
              whose items are sorted planning-first
  management  operations research, planning research, working capital, efficiency,
              supply chain management press and recurring surveys (added 29 Oct 2026)
  companies   quarterly reports and releases from a watchlist of Nordic companies,
              with the sentences on inventory, working capital, cash flow and cost
              programmes pulled out as highlights (added 29 Oct 2026)
  freight     the freight desk: carriers, shipping, rates, waterways and transport
              trade press, capped per source (FREIGHT_CAP non-planning items plus up
              to FREIGHT_PLANNING_CAP items that match planning terms). Read for the
              Freight dashboard, not as a source of routine items.

Within every lane, each source's items are sorted so those matching planning terms
(PLAN_SORT_WORDS) come first, and marked "[planning terms]" in latest.md.

Items found only as page links (no feed) are opened one by one to read the real
publish date and the opening text, so the agents don't have to search for them.

Usage: python tools/fetch_sources.py out/
"""
import datetime as dt
import email.utils
import html
import json
import re
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import feedparser
import requests

_ARXIV_TERMS = ['"supply chain"', 'inventory', '"lot sizing"', '"production planning"',
                '"production scheduling"', '"demand forecasting"', '"sales and operations"',
                '"job shop"', '"network design"', '"facility location"', 'replenishment',
                'newsvendor', '"safety stock"', '"capacity planning"', '"multi-echelon"', 'procurement']
ARXIV_API = ("https://export.arxiv.org/api/query?search_query="
             + urllib.parse.quote(" OR ".join(f"ti:{t}" for t in _ARXIV_TERMS))
             + "&sortBy=submittedDate&sortOrder=descending&max_results=60")

# (name, url) or (name, [url, fallback url, ...]); the first URL that yields entries wins.
# Dropped 10 Nov 2026 after failing every night (403 or timeout): SupplyChain247,
# Logistics Management, Dagens Infrastruktur, Gartner Newsroom, ASCM. The scrobbler
# reaches Gartner and ASCM through search.
SOURCES = [
    ("SupplyChainBrain", "https://www.supplychainbrain.com/rss/articles"),
    ("SCMR", "https://www.scmr.com/"),
    ("Supply Chain Dive", "https://www.supplychaindive.com/feeds/news/"),
    ("Supply Chain Digital", "https://supplychaindigital.com/news"),
    # Added 10 Nov 2026: planning, footprint and operations sources.
    ("Manufacturing Dive", "https://www.manufacturingdive.com/feeds/news/"),
    ("demand-planning.com (IBF)", ["https://demand-planning.com/feed/", "https://demand-planning.com/"]),
    ("Logistics Viewpoints", "https://logisticsviewpoints.com/"),
    ("SCM.dk", "https://scm.dk/feeds/articles"),
    ("SC Effect", "https://www.sceffect.se/en/category/nyheter/"),
    ("Osto&Logistiikka", "https://www.ostologistiikka.fi/"),
    ("BME", "https://www.bme.de/news/"),
    ("BVL", "https://www.bvl.de/"),
    ("produktion.de", ["https://www.produktion.de/rss", "https://www.produktion.de/"]),
    ("Ny Teknik", ["https://www.nyteknik.se/rss", "https://www.nyteknik.se/"]),
    ("Dagens Industri", ["https://www.di.se/rss", "https://www.di.se/"]),
    ("MIT Sloan Management Review", "https://sloanreview.mit.edu/feed/"),
    # arXiv search API (Atom): newest preprints whose title names a planning topic, any category.
    ("arXiv (planning and OR preprints)", ARXIV_API),
    ("NVIDIA Technical Blog (optimisation)", "https://developer.nvidia.com/blog/feed/"),
    ("Talking Logistics", "https://talkinglogistics.com/"),
    ("Supply Chain Shaman", "https://www.supplychainshaman.com/"),
    ("SAP News", "https://news.sap.com/"),
]

# The freight desk (moved out of the main lane 10 Nov 2026). Nordic and DACH transport
# press stays here too, but its items that match planning terms are kept beyond the cap.
FREIGHT_SOURCES = [
    ("The Loadstar", "https://theloadstar.com/"),
    ("FreightWaves", "https://www.freightwaves.com/news"),
    ("Splash247", "https://splash247.com/"),
    ("DC Velocity", "https://www.dcvelocity.com/"),
    ("Sea-Intelligence", "https://www.sea-intelligence.com/press-room"),
    ("Xeneta", "https://www.xeneta.com/news"),
    ("VerkehrsRundschau", "https://www.verkehrsrundschau.de/nachrichten"),
    ("Logistik Journal", "https://www.logistik-journal.de/"),
    ("Dagens Logistik", "https://dagenslogistik.se/nyheter/"),
    ("MT Logistikk", "https://www.mtlogistikk.no/"),
]

# Added 29 Oct 2026 (claude/research/source-vetting-2026-10-29-management.md).
MANAGEMENT_SOURCES = [
    ("TechXplore (business)", "https://techxplore.com/rss-feed/business-tech-news/"),
    ("TechXplore (all)", "https://techxplore.com/rss-feed/"),
    ("Phys.org (economics and business)", "https://phys.org/rss-feed/science-news/economics-business/"),
    ("idw-online (DACH research)", "https://idw-online.de/de/pressreleasesrss"),
    ("KLU newsroom", "https://www.klu.org/newsroom"),
    ("The Conversation (business)", "https://theconversation.com/uk/business/articles.atom"),
    ("Consultancy.eu", "https://www.consultancy.eu/rss/consultancy_rssfeed.xml"),
    ("CFO Dive", "https://www.cfodive.com/feeds/news/"),
    ("Industriemagazin", "https://industriemagazin.at/rss.xml"),
    ("Placera (Swedish business news)", "https://www.placera.se/artiklar/rss.xml"),
    ("Teknikföretagen", "https://via.tt.se/rss/releases/latest?publisherId=2732851"),
    ("Swedbank PMI", "https://mfn.se/all/a/swedbank.rss"),
    ("STT Info (Finnish releases)", "https://www.sttinfo.fi/rss/releases/latest"),
    ("DACH ad hoc releases (finanznachrichten)", "https://www.finanznachrichten.de/rss-aktien-adhoc/"),
    # Added 10 Nov 2026: OR and planning-science journals' press releases.
    ("INFORMS newsroom", "https://www.informs.org/News-Room/INFORMS-Releases/News-Releases"),
]


def _mfn(slug):
    return f"https://mfn.se/all/a/{slug}.rss"


def _cision(slug):
    return f"https://news.cision.com/se/ListItems?n={slug}&m=Financial&pageIx=1&format=rss"


# Company watchlist: Nordic manufacturers and distributors. Edit freely.
COMPANIES = [
    ("SKF", [_mfn("skf"), _cision("skf")]),
    ("Sandvik", [_mfn("sandvik"), _cision("sandvik")]),
    ("Atlas Copco", [_mfn("atlas-copco"), _cision("atlas-copco")]),
    ("Epiroc", [_mfn("epiroc"), _cision("epiroc")]),
    ("Volvo Group", [_mfn("volvo"), _mfn("ab-volvo"), _cision("ab-volvo")]),
    ("Electrolux", [_mfn("electrolux")]),
    ("Alfa Laval", [_mfn("alfa-laval"), _cision("alfa-laval")]),
    ("Husqvarna", [_mfn("husqvarna")]),
    ("Essity", [_mfn("essity"), _cision("essity")]),
    ("Getinge", [_mfn("getinge"), _cision("getinge")]),
    ("Boliden", [_mfn("boliden"), _cision("boliden")]),
    ("SSAB", [_mfn("ssab"), _cision("ssab")]),
    ("Assa Abloy", [_mfn("assa-abloy"), _cision("assa-abloy")]),
    ("Trelleborg", [_mfn("trelleborg")]),
    ("SCA", [_mfn("sca"), _cision("sca")]),
    ("Holmen", [_mfn("holmen"), _cision("holmen")]),
    ("Billerud", [_mfn("billerud"), _cision("billerud-ab")]),
    ("Thule", [_mfn("thule-group")]),
    ("Axfood", [_mfn("axfood")]),
    ("ICA Gruppen", [_mfn("ica-gruppen")]),
    ("Kone", [_mfn("kone")]),
    ("Wärtsilä", [_mfn("wartsila")]),
    ("Valmet", [_mfn("valmet")]),
    ("UPM", [_mfn("upm-kymmene")]),
    ("Stora Enso", [_mfn("stora-enso")]),
    ("Orkla", [_mfn("orkla")]),
    ("Norsk Hydro", [_mfn("norsk-hydro")]),
    ("Carlsberg", [_mfn("carlsberg")]),
]

PLANNING_WORDS = [
    "supply chain", "supply-chain", "inventor", "logistics", "scheduling", "demand forecast",
    "forecasting", "procurement", "suppliers", "operations research", "warehouse",
    "production planning", "working capital", "lean manufacturing", "factory planning",
    "sales and operations", "s&op", "optimization model", "mathematical optimization",
    "decision-making in operations", "order decisions", "spare parts", "stockpil",
]
GERMAN_WORDS = [
    "lieferkette", "supply chain", "supply-chain", "logistik", "lagerbestand", "bestände",
    "produktionsplanung", "beschaffung", "einkauf", "operations research", "wertschöpfungskette",
    "lieferengp", "materialmangel", "bedarfsprognose", "absatzprognose", "disposition",
]
# Planning terms used to sort every source's items planning-first, and to let
# planning items through the freight desk cap. Matched at word starts. An item counts
# as planning when a term is in its title, or two different terms are in title plus
# summary. English, Swedish, Norwegian, Danish, Finnish and German.
PLAN_SORT_WORDS = [
    "planning", "planner", "forecast", "s&op", "sales and operations", "integrated business planning",
    "inventor", "working capital", "safety stock", "replenish", "network design", "network redesign",
    "footprint", "distribution center", "distribution centre", "central warehouse", "nearshor",
    "reshor", "dual sourcing", "optimization", "optimisation", "solver", "digital twin",
    "decision intelligence", "agentic", "ai agent", "operations research", "scheduling",
    "capacity planning", "production plan", "plant closure", "closes plant", "close plant",
    "new plant", "factory", "factories", "consolidat", "procurement", "sourcing",
    "planering", "prognos", "varulager", "centrallager", "lagerstyrning", "lageroptim",
    "leveranskedj", "rörelsekapital", "fabrik", "produktionsplan", "nedläggning",
    "planlegging", "planlægning", "forsyningskæde", "forsyningskjede", "lagerstyring",
    "suunnittelu", "ennuste", "toimitusketju",
    "planung", "prognose", "lagerbestand", "bestände", "werksschließung", "standort",
    "lieferkette", "produktionsplanung", "disposition", "kapazitätsplanung", "beschaffung",
]
_PLAN_RE = [re.compile(r"(?<![a-zåäöæøüß])" + re.escape(w)) for w in PLAN_SORT_WORDS]
ARXIV_WORDS = [
    "supply chain", "inventory", "demand forecast", "lot sizing", "lot-sizing",
    "production planning", "production scheduling", "job shop", "job-shop", "flow shop",
    "sales and operations", "s&op", "supply chain network", "facility location", "procurement",
    "replenishment", "newsvendor", "safety stock", "capacity planning", "multi-echelon",
    "supply network", "bullwhip", "order picking", "spare parts", "network design",
]
SWEDISH_PLAN_WORDS = [
    "varulager", "lager", "centrallager", "logistikcenter", "fabrik", "produktion",
    "leveranskedj", "nedläggning", "flyttar produktion", "kapacitet", "inköp", "underleverantör",
]

# Sources matched on title and summary only (their full text is long and noisy).
TITLE_ONLY = {
    "TechXplore (business)", "TechXplore (all)", "Phys.org (economics and business)",
    "The Conversation (business)", "idw-online (DACH research)", "Industriemagazin",
    "Placera (Swedish business news)", "arXiv (planning and OR preprints)", "Ny Teknik", "Dagens Industri", "MIT Sloan Management Review",
}
# Sources matched on the title alone (arXiv abstracts mention "network design" for 6G and the like).
TITLE_STRICT = {"arXiv (planning and OR preprints)"}

# Sources whose feed is broad: keep only items whose title, summary or text matches.
KEYWORDS = {
    "NVIDIA Technical Blog (optimisation)": [
        "cuopt", "solver", "supply chain", "logistics", "vehicle routing", "linear program",
        "mixed integer", "mixed-integer", "operations research", "inventory", "demand forecast"],
    "TechXplore (business)": PLANNING_WORDS,
    "TechXplore (all)": PLANNING_WORDS,
    "Phys.org (economics and business)": PLANNING_WORDS,
    "The Conversation (business)": PLANNING_WORDS,
    "idw-online (DACH research)": GERMAN_WORDS + PLANNING_WORDS,
    "Consultancy.eu": PLANNING_WORDS + ["s&op", "cost reduction", "efficiency", "operating model"],
    "CFO Dive": ["inventor", "working capital", "supply chain", "cash conversion", "supplier",
                 "procurement", "cash flow"],
    "Industriemagazin": GERMAN_WORDS + [
        "effizienz", "stellenabbau", "restrukturierung", "sparprogramm", "kostensenkung",
        "werksschließung", "kurzarbeit", "auslastung", "lean"],
    "Placera (Swedish business news)": [
        "varulager", "lagret", "lagernivå", "rörelsekapital", "besparing", "sparprogram",
        "effektivis", "varsel", "omstrukturer", "leveranskedj", "produktionslinje", "fabrik",
        "kapacitet", "nedläggning"],
    "Teknikföretagen": ["konjunktur", "barometer", "order", "export", "industri", "kapacitet"],
    "Swedbank PMI": ["pmi", "inköpschef"],
    "STT Info (Finnish releases)": [
        "teknologiateollisuus", "toimitusketju", "tilauskanta", "varasto", "teollisuu"],
    "DACH ad hoc releases (finanznachrichten)": [
        "prognose", "restrukturierung", "effizienz", "stellenabbau", "sparprogramm",
        "kostensenkung", "quartal", "werk", "lieferkette"],
    "arXiv (planning and OR preprints)": ARXIV_WORDS,
    "INFORMS newsroom": ARXIV_WORDS + ["operations", "supply", "inventor", "manufactur", "retail", "logistic"],
    "Ny Teknik": SWEDISH_PLAN_WORDS,
    "Dagens Industri": SWEDISH_PLAN_WORDS,
    "MIT Sloan Management Review": PLANNING_WORDS + ["operations", "supplier", "manufactur"],
    "produktion.de": GERMAN_WORDS + ["werk", "standort", "fertigung", "kapazität", "verlager"],
}

# Link filters for sources read from page links: keep only article paths.
LINK_RULES = {
    "Xeneta": {"include": ["/news/", "/press/", "/blog/xeneta-weekly", "ocean-market-update"]},
    "Osto&Logistiikka": {"exclude": ["/mainos/"]},
    "KLU newsroom": {"include": ["/article/"]},
    "INFORMS newsroom": {"include": ["/News-Releases/"]},
}

# Company releases: skip routine notices; pull these words' sentences out as highlights.
COMPANY_NOISE = [
    "managers' transactions", "managers transactions", "johtohenkilöiden", "buyback", "buy-back",
    "återköp", "repurchase", "shareholder disclosure", "disclosure notification", "notification of",
    "holdings", "flaggning", "invitation", "inbjudan", "kutsu", "påminnelse", "reminder",
    "shares converted", "osakkeet", "status share", "major shareholding", "number of shares",
    "number of votes", "annual general", "årsstämma", "extraordinary", "nomination", "valberedning",
    "reporting schedule", "katsausten aikataulu", "taloudelliset raportit", "yhtiökokous",
    "financial calendar", "financial reports and annual general", "share capital", "incentive", "acquisition of carlsberg a/s sha",
]
HIGHLIGHT_WORDS = [
    "inventor", "working capital", "cash flow", "savings", "cost reduction", "cost-reduction",
    "efficiency", "restructuring", "rightsizing", "capacity", "supply chain", "headcount", "footprint",
    "tariff", "lager", "rörelsekapital", "kassaflöde", "besparing", "effektivis", "omstrukturer",
    "varsel", "kapacitet", "varasto", "käyttöpääoma", "kassavirta", "säästö", "tehostam",
    "lagerbest", "bestände", "vorräte", "working capital", "free cash", "kosten", "effizienz",
    "stellenabbau", "restrukturierung", "sparprogramm", "werk", "kapazität", "auftragseingang",
    "nachfrage", "lieferkette",
]
# Feed items whose feed text is only a teaser: open the article and pull highlights from it.
READ_FULL = {"DACH ad hoc releases (finanznachrichten)"}
ENGLISH_HINTS = [" report", "interim", "quarter", "results", "statement", "inside information",
                 "acquire", "announces", "to ", " the "]

# Live Rhine gauges from Pegelonline (WSV), the federal waterways data service.
RHINE_API = ("https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations.json"
             "?waters=RHEIN&includeTimeseries=true&includeCurrentMeasurement=true")
RHINE_GAUGES = ["MAXAU", "KAUB", "KÖLN", "DUISBURG-RUHRORT", "EMMERICH"]

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/130.0 Safari/537.36 ThePlanningDeskBot/1.0")
MAX_AGE_DAYS = 8
MAX_PER_SOURCE = 40          # per source, after keyword filtering
MAX_RAW_PER_FEED = 600       # read this many feed entries before filtering (arXiv is large)
PLANNING_LANE_CAP = 20       # per source in the planning lane, planning-first
FREIGHT_CAP = 5              # freight desk: non-planning items per source
FREIGHT_PLANNING_CAP = 10    # freight desk: planning-matched items per source, on top
ARTICLES_PER_SOURCE = 15
TIMEOUT = 25


def clean(text, limit=400):
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", text or "", flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


def get(url, timeout=TIMEOUT):
    r = requests.get(url, headers={"User-Agent": UA, "Accept": "*/*"}, timeout=timeout)
    r.raise_for_status()
    return r


def looks_like_feed(resp):
    ctype = resp.headers.get("content-type", "").lower()
    head = resp.text[:500].lstrip().lower()
    return ("xml" in ctype or "rss" in ctype or "atom" in ctype
            or head.startswith("<?xml") or head.startswith("<rss") or head.startswith("<feed"))


def discover_feeds(page_url, page_html):
    found = []
    for tag in re.findall(r"<link\b[^>]*>", page_html, flags=re.I):
        if re.search(r"""type=["']application/(rss|atom)\+xml""", tag, re.I):
            m = re.search(r"""href=["']([^"']+)""", tag, re.I)
            if m:
                href = urllib.parse.urljoin(page_url, html.unescape(m.group(1)))
                if "comments" not in href:
                    found.append(href)
    base = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(page_url))
    found += [page_url.rstrip("/") + "/feed/", base + "/feed/", base + "/rss"]
    seen, out = set(), []
    for f in found:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def entry_text(e):
    if e.get("content"):
        return " ".join(c.get("value", "") for c in e["content"])
    return e.get("summary") or e.get("description") or ""


def parse_feed(source, feed_url, content, cutoff):
    parsed = feedparser.parse(content)
    items = []
    for e in parsed.entries:
        stamp = e.get("published_parsed") or e.get("updated_parsed")
        published = dt.datetime(*stamp[:6], tzinfo=dt.timezone.utc) if stamp else None
        if published and published < cutoff:
            continue
        items.append({
            "source": source,
            "title": clean(e.get("title"), 300),
            "link": e.get("link", ""),
            "published": published.isoformat() if published else None,
            "summary": clean(e.get("summary") or e.get("description")),
            "_text": clean(entry_text(e), 60000),
            "via": "feed",
        })
    return items, len(parsed.entries)


def parse_mfn(source, content, cutoff):
    """MFN feeds keep the release text in <x:content type="text"> and tag the language."""
    text = content.decode("utf-8", "replace") if isinstance(content, bytes) else content
    items, total = [], 0
    for block in re.findall(r"<item>(.*?)</item>", text, re.S):
        total += 1
        def tag(name):
            m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", block, re.S)
            return re.sub(r"^<!\[CDATA\[|\]\]>$", "", m.group(1).strip()) if m else ""
        try:
            published = email.utils.parsedate_to_datetime(tag("pubDate")).astimezone(dt.timezone.utc)
        except (TypeError, ValueError):
            published = None
        if published and published < cutoff:
            continue
        m = re.search(r"""<x:content type="text"><!\[CDATA\[(.*?)\]\]></x:content>""", block, re.S)
        body = html.unescape(m.group(1)) if m else ""
        items.append({
            "source": source, "title": clean(tag("title"), 300), "link": clean(tag("link"), 500),
            "published": published.isoformat() if published else None,
            "summary": clean(body, 400), "_text": body[:60000], "_lang": tag("x:language"),
            "via": "feed",
        })
    return items, total


def scrape_links(source, page_url, page_html):
    """Last resort for pages without a feed: article-looking links on the page."""
    host = urllib.parse.urlparse(page_url).netloc.replace("www.", "")
    include = LINK_RULES.get(source, {}).get("include")
    items, seen = [], set()
    for href, text in re.findall(r"""<a\b[^>]*href=["']([^"'#]+)["'][^>]*>(.*?)</a>""", page_html, re.I | re.S):
        link = urllib.parse.urljoin(page_url, html.unescape(href))
        parts = urllib.parse.urlparse(link)
        title = clean(text, 300)
        wanted = include and any(k in link for k in include)
        if host not in parts.netloc or link in seen or (len(title) < 25 and not wanted):
            continue
        path = parts.path.strip("/")
        if path.count("/") < 1 and not re.search(r"\d{4,}|-[a-z]+-[a-z]+-[a-z]+", path):
            continue
        seen.add(link)
        items.append({"source": source, "title": title, "link": link,
                      "published": None, "summary": "", "via": "page links"})
    return items


def fetch_source(source, urls, cutoff):
    urls = [urls] if isinstance(urls, str) else urls
    status = {"source": source, "url": urls[0], "ok": False, "method": None, "items": 0, "error": None}
    errors = []
    for url in urls:
        try:
            resp = get(url)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{url}: {type(exc).__name__}: {exc}"[:200])
            continue
        if looks_like_feed(resp):
            if "mfn.se/" in url:
                items, total = parse_mfn(source, resp.content, cutoff)
            else:
                items, total = parse_feed(source, url, resp.content, cutoff)
            if total:
                items = items[:MAX_RAW_PER_FEED]
                status.update(ok=True, url=url, method=f"feed {url}", items=len(items), raw_items=len(items))
                return items, status
            errors.append(f"{url}: empty feed")
            continue
        for feed_url in discover_feeds(url, resp.text):
            try:
                fresp = get(feed_url)
                if not looks_like_feed(fresp):
                    continue
                items, total = parse_feed(source, feed_url, fresp.content, cutoff)
                if total:
                    items = items[:MAX_RAW_PER_FEED]
                    status.update(ok=True, url=url, method=f"feed {feed_url}", items=len(items), raw_items=len(items))
                    return items, status
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{feed_url}: {type(exc).__name__}")
        items = scrape_links(source, url, resp.text)[:MAX_PER_SOURCE]
        if items:
            status.update(ok=True, url=url, method="page links (articles opened for dates)", items=len(items), raw_items=len(items))
            return items, status
        errors.append(f"{url}: no feed and no article links")
    status["error"] = "; ".join(errors)[:300] or "nothing read"
    return [], status


def keep(source, items):
    words = KEYWORDS.get(source)
    if words:
        def hay(i):
            if source in TITLE_STRICT:
                return i["title"].lower()
            extra = "" if source in TITLE_ONLY else " " + i.get("_text", "")
            return (i["title"] + " " + i["summary"] + extra).lower()
        items = [i for i in items if any(w in hay(i) for w in words)]
    rules = LINK_RULES.get(source, {})
    if rules.get("include"):
        items = [i for i in items if any(k in i["link"] for k in rules["include"])]
    if rules.get("exclude"):
        items = [i for i in items if not any(k in i["link"] for k in rules["exclude"])]
    return items


def plan_match(item):
    title = item["title"].lower()
    hay = title + " " + (item["summary"] or "").lower()
    if any(r.search(title) for r in _PLAN_RE):
        return 2
    return 1 if sum(1 for r in _PLAN_RE if r.search(hay)) >= 2 else 0


def plan_sort_and_cap(lane, items):
    """Planning-first order within one source, then the lane's cap."""
    for it in items:
        it["planning_terms"] = plan_match(it) > 0
    items = sorted(items, key=lambda i: (not i["planning_terms"], -(parse_date(i["published"]).timestamp() if i["published"] else 0)))
    if lane == "freight":
        plan = [i for i in items if i["planning_terms"]][:FREIGHT_PLANNING_CAP]
        rest = [i for i in items if not i["planning_terms"]][:FREIGHT_CAP]
        return plan + rest
    if lane == "planning":
        return items[:PLANNING_LANE_CAP]
    return items[:MAX_PER_SOURCE]


# --- reading single articles (for page-link items) --------------------------------

DATE_PATTERNS = [
    r"""<meta[^>]+(?:property|name|itemprop)=["'](?:article:published_time|og:published_time|datePublished|date|pubdate|publishdate|dc\.date|DC\.date\.issued)["'][^>]*content=["']([^"']+)""",
    r"""<meta[^>]+content=["']([^"']+)["'][^>]*(?:property|name|itemprop)=["'](?:article:published_time|datePublished|date|pubdate)["']""",
    r'''"datePublished"\s*:\s*"([^"]+)"''',
    r"""<time[^>]+datetime=["']([^"']+)""",
]


def parse_date(text):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?", text or "")
    if m:
        y, mo, d, h, mi = m.groups()
        return dt.datetime(int(y), int(mo), int(d), int(h or 0), int(mi or 0), tzinfo=dt.timezone.utc)
    m = re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? (\d{1,2}), (\d{4})\b", text or "")
    if m:
        mo = "JanFebMarAprMayJunJulAugSepOctNovDec".index(m.group(1)) // 3 + 1
        return dt.datetime(int(m.group(3)), mo, int(m.group(2)), tzinfo=dt.timezone.utc)
    m = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b", text or "")
    if m:
        d, mo, y = m.groups()
        return dt.datetime(int(y), int(mo), int(d), tzinfo=dt.timezone.utc)
    return None


def read_article(url):
    """Return (published datetime or None, opening text) for one article page."""
    resp = get(url, timeout=15)
    page = resp.text
    published = None
    for pat in DATE_PATTERNS:
        m = re.search(pat, page, re.I)
        if m and parse_date(m.group(1)):
            published = parse_date(m.group(1))
            break
    m = re.search(r"""<meta[^>]+property=["']og:title["'][^>]*content=["']([^"']+)""", page, re.I)
    title = clean(m.group(1), 300) if m else ""
    desc = ""
    for pat in (r"""<meta[^>]+property=["']og:description["'][^>]*content=["']([^"']*)""",
                r"""<meta[^>]+name=["']description["'][^>]*content=["']([^"']*)"""):
        m = re.search(pat, page, re.I)
        if m and len(m.group(1)) > 40:
            desc = clean(m.group(1), 300)
            break
    body = re.sub(r"<(script|style|nav|header|footer|aside)\b.*?</\1>", " ", page, flags=re.I | re.S)
    paras = [clean(p, 600) for p in re.findall(r"<p\b[^>]*>(.*?)</p>", body, re.I | re.S)]
    paras = [p for p in paras if len(p) > 80 and "cookie" not in p.lower()]
    it_text = " ".join(paras)
    opening = " ".join(paras[:3])
    text = (desc + " " + opening).strip() if desc and desc[:60] not in opening else (opening or desc)
    return published, clean(text, 500), title, it_text


def enrich(items, cutoff):
    """Open page-link items to read their real date and opening text; drop old ones."""
    todo, counts = [], {}
    for it in items:
        if it["source"] in READ_FULL and it["via"] == "feed":
            todo.append(it)
            continue
        if it["via"] != "page links":
            continue
        counts[it["source"]] = counts.get(it["source"], 0) + 1
        if counts[it["source"]] <= ARTICLES_PER_SOURCE:
            todo.append(it)

    def work(it):
        try:
            published, text, title, full = read_article(it["link"])
        except Exception:  # noqa: BLE001
            published, text, title, full = None, "", "", ""
        if it["source"] in READ_FULL:
            it["highlights"] = highlights(full)
            return it, None, text
        if not published:
            published = parse_date(it["title"]) or parse_date(text[:200])
        if title and len(it["title"]) < 25:
            it["title"] = title
        return it, published, text

    with ThreadPoolExecutor(max_workers=8) as pool:
        for it, published, text in pool.map(work, todo):
            it["via"] = "feed, article read" if it["via"] == "feed" else "page links, article read"
            if published:
                it["published"] = published.isoformat()
            if text:
                it["summary"] = text
    kept = []
    for it in items:
        if it["via"] == "page links":
            continue  # beyond the per-source article cap: not read, not kept
        if it["published"] and parse_date(it["published"]) < cutoff:
            continue
        kept.append(it)
    return kept


# --- company releases ---------------------------------------------------------------

def highlights(text, limit=1200):
    # Re-join lines wrapped mid-sentence (no closing punctuation, next line not a bullet).
    text = re.sub(r"(?<![.!?:])[ \t]*\n[ \t]*(?![*•·\-\n])", " ", text or "")
    sentences = re.split(r"(?<=[.!?])\s+|\n+\s*[*•·-]?\s*", text)
    picked, total = [], 0
    for s in sentences:
        s = s.strip()
        s = s.lstrip("*•·- ").strip()
        if any(b in s.lower() for b in ("insiderinformation", "schlagwort", "eqs news", "eqs-ad-hoc",
                                        "pta-adhoc", "artikel 17", "market abuse regulation")):
            continue
        if 25 <= len(s) <= 450 and any(w in s.lower() for w in HIGHLIGHT_WORDS):
            if any(s in q for q in picked):
                continue
            shorter = [q for q in picked if q in s]
            for q in shorter:
                picked.remove(q)
                total -= len(q)
            picked.append(s)
            total += len(s)
            if total > limit or len(picked) >= 8:
                break
    return " ".join(picked)


def company_items(name, items):
    items = [i for i in items if not any(n in i["title"].lower() for n in COMPANY_NOISE)]
    # MFN publishes each release in two languages at the same minute: keep one, preferring English.
    by_time = {}
    for it in items:
        key = (it["published"] or "")[:16] or it["link"]
        by_time.setdefault(key, []).append(it)
    kept = []
    for group in by_time.values():
        group.sort(key=lambda i: (i.get("_lang") != "en", -sum(h in i["title"].lower() for h in ENGLISH_HINTS)))
        it = group[0]
        it["company"] = name
        it["highlights"] = highlights(it.get("_text", ""))
        kept.append(it)
    english = [parse_date(i["published"]) for i in kept if i.get("_lang") == "en" and i["published"]]
    def twin(i):
        if i.get("_lang") in ("en", "", None) or not i["published"]:
            return False
        t = parse_date(i["published"])
        return any(abs((t - e).total_seconds()) <= 900 for e in english)
    kept = [i for i in kept if not twin(i)]
    for i in kept:
        i.pop("_lang", None)
    kept.sort(key=lambda i: i["published"] or "", reverse=True)
    return kept


# --- Rhine ----------------------------------------------------------------------------

def fetch_rhine():
    """Current water level (cm) at the Rhine gauges that matter for barge loads."""
    status = {"source": "Rhine gauges (Pegelonline)", "url": RHINE_API, "ok": False,
              "method": "json api", "items": 0, "error": None, "lane": "freight"}
    try:
        stations = get(RHINE_API).json()
    except Exception as exc:  # noqa: BLE001
        status["error"] = f"{type(exc).__name__}: {exc}"[:200]
        return [], status
    rows = []
    for st in stations:
        name = st.get("shortname", "").upper()
        if name not in RHINE_GAUGES:
            continue
        for ts in st.get("timeseries", []):
            m = ts.get("currentMeasurement")
            if ts.get("shortname") == "W" and m:
                rows.append({"gauge": st["shortname"], "km": st.get("km"),
                             "level_cm": m.get("value"), "trend": m.get("trend"),
                             "measured_at": m.get("timestamp"), "unit": ts.get("unit")})
    rows.sort(key=lambda r: r["km"] or 0)
    status.update(ok=bool(rows), items=len(rows), error=None if rows else "no gauge data")
    return rows, status


# --- main -----------------------------------------------------------------------------

LANE_TITLES = {
    "planning": "Planning, network design, AI and tech sources (items matching planning terms first)",
    "freight": "Freight desk (capped: for the Freight dashboard and genuine score-5 events, not routine items)",
    "management": "Management, operations research and planning research sources",
    "companies": "Company releases (watchlist: quarterly reports, programmes, restructurings)",
}


def run_lane(lane, sources, cutoff, all_items, statuses):
    for source, urls in sources:
        items, status = fetch_source(source, urls, cutoff)
        status["lane"] = lane
        if lane == "companies":
            items = company_items(source, items)
            status["items"] = len(items)
            if status["ok"] and not items:
                status["error"] = "no releases in the window (normal off-season)"
        elif source in KEYWORDS or source in LINK_RULES:
            items = keep(source, items)[:MAX_PER_SOURCE]
            status["items"] = len(items)
            if not items and source in LINK_RULES and status["ok"]:
                status.update(ok=False, error="no article links after filtering")
            elif not items and status["ok"]:
                status["error"] = "no matching posts in the window (normal for this source)"
        for it in items:
            it["lane"] = lane
        print(f"{'OK ' if status['ok'] else 'ERR'} [{lane}] {source}: {status['items']} items "
              f"via {status['method'] or '-'} {status['error'] or ''}", flush=True)
        all_items += items
        statuses.append(status)


def main(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=MAX_AGE_DAYS)
    all_items, statuses = [], []
    run_lane("planning", SOURCES, cutoff, all_items, statuses)
    run_lane("management", MANAGEMENT_SOURCES, cutoff, all_items, statuses)
    run_lane("companies", COMPANIES, cutoff, all_items, statuses)
    run_lane("freight", FREIGHT_SOURCES, cutoff, all_items, statuses)

    all_items = enrich(all_items, cutoff)
    # Planning-first sort and per-lane caps, after dates are known (companies keep their order).
    capped = []
    for s in statuses:
        mine = [i for i in all_items if i["source"] == s["source"]]
        capped += mine if s["lane"] == "companies" else plan_sort_and_cap(s["lane"], mine)
    all_items = capped
    for s in statuses:
        if s["lane"] != "companies":
            s["items"] = sum(1 for i in all_items if i["source"] == s["source"])
    for it in all_items:
        it.pop("_text", None)

    rhine, rhine_status = fetch_rhine()
    print(f"{'OK ' if rhine_status['ok'] else 'ERR'} Rhine gauges: {len(rhine)} {rhine_status['error'] or ''}")
    statuses.append(rhine_status)

    meta = {"fetched_at": now.isoformat(), "window_days": MAX_AGE_DAYS,
            "sources_ok": sum(s["ok"] for s in statuses), "sources_total": len(statuses)}
    (out / "latest.json").write_text(json.dumps({**meta, "items": all_items, "rhine_gauges": rhine}, ensure_ascii=False, indent=1))
    (out / "status.json").write_text(json.dumps({**meta, "sources": statuses}, ensure_ascii=False, indent=1))

    lines = [f"# Source digest, fetched {now:%Y-%m-%d %H:%M} UTC",
             f"{meta['sources_ok']} of {meta['sources_total']} sources read. Items from the last "
             f"{MAX_AGE_DAYS} days. Items from page links were opened to read their date and opening "
             "text; 'no date' means the article page didn't show one.", ""]
    counts = {lane: sum(1 for i in all_items if i["lane"] == lane) for lane in LANE_TITLES}
    lines += ["Items per lane: " + ", ".join(f"{k} {v}" for k, v in counts.items()), ""]
    for lane in ("planning", "management", "companies", "freight"):
        lines += [f"# {LANE_TITLES[lane]}", ""]
        for s in (s for s in statuses if s["lane"] == lane and s is not rhine_status):
            lines.append(f"## {s['source']}")
            if not s["ok"]:
                lines += [f"(failed: {s['error']})", ""]
                continue
            listed = [i for i in all_items if i["source"] == s["source"]]
            if not listed:
                lines += ["(nothing in the window)", ""]
                continue
            for it in listed:
                when = it["published"][:16].replace("T", " ") if it["published"] else "no date"
                tag = " [planning terms]" if it.get("planning_terms") and lane != "companies" else ""
                lines.append(f"- {when} | {it['title']} | {it['link']}{tag}")
                if it.get("highlights"):
                    lines.append(f"  Highlights: {it['highlights']}")
                elif it["summary"]:
                    lines.append(f"  {it['summary']}")
            lines.append("")
    lines.append("## Rhine gauges (Pegelonline, live; freight desk)")
    if rhine:
        lines.append("Water level in cm; trend 1 rising, 0 steady, -1 falling. Kaub needs about 77 cm for a 1.90 m channel.")
        for r in rhine:
            lines.append(f"- {r['gauge']} (Rhine km {r['km']}): {r['level_cm']} {r['unit']}, "
                         f"{'trend ' + str(r['trend']) + ', ' if r['trend'] is not None else ''}measured {r['measured_at']}")
    else:
        lines.append(f"(failed: {rhine_status['error']})")
    lines.append("")
    (out / "latest.md").write_text("\n".join(lines))
    if meta["sources_ok"] == 0:
        sys.exit("No source could be read")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "out")
