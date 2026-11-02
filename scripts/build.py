"""Build the static site into _site/ and refresh the list in README.md.

    python scripts/build.py                 # site for https://kooroshkz.github.io/housing-netherlands/
    BASE=/ python scripts/build.py          # local preview: python -m http.server -d _site
    python scripts/build.py --check         # only validate data/ (used in CI)

No dependencies beyond the Python standard library.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
BASE = os.environ.get("BASE", "/housing-netherlands/")
SITE_URL = os.environ.get("SITE_URL", "https://kooroshkz.github.io/housing-netherlands").rstrip("/")
REPO = "https://github.com/kooroshkz/housing-netherlands"
TODAY = date.today().isoformat()

ROLES = {
    "student": {"label": "Student", "seo": "Student housing", "phrase": "student housing"},
    "phd": {"label": "PhD", "seo": "PhD and researcher housing", "phrase": "PhD and researcher housing"},
    "work": {"label": "Working", "seo": "Expat and professional housing", "phrase": "expat and professional housing"},
}
ROLE_KEY = {"student": "student", "phd": "phd", "work": "worker"}  # url slug -> data role

CATEGORIES = {
    "managed": "Managed apartments",
    "student": "Student housing",
    "university": "University housing",
    "landlord": "Landlords",
    "agent": "Letting agents",
    "coliving": "Co-living",
    "newbuild": "New builds",
    "shortstay": "Short stay",
    "social": "Social & mid-rent",
    "portal": "Listing sites",
    "alerts": "Alerts",
    "expat": "Expat help",
    "help": "Rights & help",
    "scam": "Scam check",
}
ORDER = {
    "all": ["managed", "student", "university", "landlord", "agent", "coliving", "newbuild", "shortstay",
            "social", "portal", "alerts", "expat", "help", "scam"],
    "student": ["student", "university", "coliving", "managed", "shortstay", "portal", "social", "alerts",
                "expat", "help", "scam"],
    "phd": ["university", "managed", "student", "coliving", "landlord", "agent", "newbuild", "shortstay",
            "portal", "social", "alerts", "expat", "help", "scam"],
    "work": ["managed", "landlord", "agent", "newbuild", "coliving", "shortstay", "portal", "social", "alerts",
             "expat", "help", "scam"],
    "national": ["portal", "alerts", "help", "scam", "expat", "agent", "managed", "landlord", "social"],
}
ACCESS = {
    "first-come": "First come", "lottery": "Lottery", "waitlist": "Waitlist", "score": "Scored",
    "booking": "Book online", "university": "Via university", "varies": None, "info": None,
    "free": "Free", "paid": "Paid",
}
FAST = {"first-come", "booking"}

ICONS = {
    "managed": '<path d="M4 21V5l8-3 8 3v16M9 21v-4h6v4M8 8h.01M12 8h.01M16 8h.01M8 12h.01M12 12h.01M16 12h.01"/>',
    "student": '<path d="M2 9l10-5 10 5-10 5L2 9z"/><path d="M6 11v5c3 2 9 2 12 0v-5"/>',
    "university": '<path d="M3 21h18M5 21V10M19 21V10M9 21v-7M15 21v-7M2 10l10-6 10 6"/>',
    "landlord": '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 6l3 3M15 8l2 2"/>',
    "agent": '<path d="M4 7h16v12H4zM9 7V5h6v2M4 12h16"/>',
    "coliving": '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3 20c0-3.5 2.7-6 6-6s6 2.5 6 6M15 14c3 0 6 2 6 5"/>',
    "newbuild": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M6 18l2.5-2.5M15.5 8.5L18 6"/>',
    "shortstay": '<rect x="5" y="7" width="14" height="13" rx="2"/><path d="M9 7V4h6v3M9 12h6"/>',
    "social": '<path d="M3 11l9-7 9 7v10H3z"/><path d="M12 18s-3-1.8-3-4a1.6 1.6 0 013-1 1.6 1.6 0 013 1c0 2.2-3 4-3 4z"/>',
    "portal": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-5-5"/>',
    "alerts": '<path d="M6 16V11a6 6 0 1112 0v5l2 2H4l2-2zM10 21h4"/>',
    "expat": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>',
    "help": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M5.6 5.6l3.6 3.6M14.8 14.8l3.6 3.6M18.4 5.6l-3.6 3.6M9.2 14.8l-3.6 3.6"/>',
    "scam": '<path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17h.01"/>',
    "star": '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
    "github": '<path d="M9 19c-4 1.3-4-2-6-2.5M15 21v-3.4a3 3 0 00-.8-2.3c2.7-.3 5.6-1.3 5.6-6a4.7 4.7 0 00-1.3-3.2 4.3 4.3 0 00-.1-3.2s-1-.3-3.4 1.3a11.6 11.6 0 00-6 0C6.6 2.6 5.6 2.9 5.6 2.9a4.3 4.3 0 00-.1 3.2A4.7 4.7 0 004.2 9.3c0 4.6 2.9 5.7 5.6 6a3 3 0 00-.8 2.3V21"/>',
    "arrow": '<path d="M7 17L17 7M8 7h9v9"/>',
    "pin": '<path d="M12 21s-7-6.2-7-11.5A7 7 0 0112 2.5a7 7 0 017 7C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
}

SCHEMA = {
    "id": str, "name": str, "url": str, "category": str, "roles": list, "cities": list, "access": str,
    "note": str, "source": str, "confidence": str,
}


def icon(name: str, cls: str = "i") -> str:
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


def e(s) -> str:
    return html.escape(str(s), quote=True)


# ---------------------------------------------------------------- data

def load() -> tuple[list, list, dict, list]:
    resources = json.loads((ROOT / "data" / "resources.json").read_text())
    cities = json.loads((ROOT / "data" / "cities.json").read_text())
    nl_map = json.loads((ROOT / "data" / "map.json").read_text())
    facts_path = ROOT / "data" / "facts.json"
    facts = json.loads(facts_path.read_text()) if facts_path.exists() else []
    return resources, cities, nl_map, facts


def validate(resources: list, cities: list) -> list[str]:
    errors = []
    slugs = {c["slug"] for c in cities} | {"nl"}
    seen = set()
    for i, r in enumerate(resources):
        where = f"resources[{i}] {r.get('id', '?')}"
        for key, typ in SCHEMA.items():
            if not isinstance(r.get(key), typ):
                errors.append(f"{where}: '{key}' must be {typ.__name__}")
        if r.get("id") in seen:
            errors.append(f"{where}: duplicate id")
        seen.add(r.get("id"))
        if r.get("category") not in CATEGORIES:
            errors.append(f"{where}: unknown category {r.get('category')!r}")
        if r.get("access") not in ACCESS:
            errors.append(f"{where}: unknown access {r.get('access')!r}")
        if not set(r.get("roles") or []) <= {"student", "phd", "worker"} or not r.get("roles"):
            errors.append(f"{where}: roles must be a non-empty subset of student, phd, worker")
        bad = set(r.get("cities") or []) - slugs
        if bad or not r.get("cities"):
            errors.append(f"{where}: unknown cities {sorted(bad)}")
        if not str(r.get("url", "")).startswith("https://"):
            errors.append(f"{where}: url must start with https://")
        if len(r.get("note") or "") > 70:
            errors.append(f"{where}: note longer than 70 characters")
    return errors


def pick(resources: list, city: str | None, role: str | None) -> list:
    key = ROLE_KEY.get(role) if role else None
    out = []
    for r in resources:
        if city and city not in r["cities"] and "nl" not in r["cities"]:
            continue
        if not city and "nl" not in r["cities"]:
            continue
        if key and key not in r["roles"]:
            continue
        out.append(r)
    return out


def grouped(items: list, city: str | None, role: str | None) -> list[tuple[str, list]]:
    order = ORDER[role or ("all" if city else "national")]
    groups = []
    for cat in order:
        rows = [r for r in items if r["category"] == cat]
        rows.sort(key=lambda r: ("nl" in r["cities"] and bool(city), r.get("rank", 99), r["name"].lower()))
        if rows:
            groups.append((cat, rows))
    return groups


# ---------------------------------------------------------------- html parts

def url(path: str = "") -> str:
    return BASE + path


def domain(u: str) -> str:
    return urlparse(u).netloc.removeprefix("www.")


def short(text: str, limit: int = 24) -> str:
    """Card chips stay one short line; the full text is in the README and data."""
    text = re.split(r", | or |; | \(", text)[0].strip()
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def card(r: dict, names: dict | None = None) -> str:
    chips = []
    if names:
        where = [names[c] for c in r["cities"] if c in names]
        label = ", ".join(where) if len(where) <= 2 else f"{len(where)} cities"
        chips.append(f'<span class="chip" title="{e(", ".join(where))}">{e(label)}</span>')
    acc = ACCESS.get(r["access"])
    if acc:
        chips.append(f'<span class="chip{" on" if r["access"] in FAST else ""}">{e(acc)}</span>')
    roles = r["roles"]
    if roles == ["student"]:
        chips.append('<span class="chip">Students only</span>')
    elif "student" not in roles and "phd" in roles and r["category"] in ("student", "university"):
        chips.append('<span class="chip">PhD ok</span>')
    if r.get("furnished") == "yes":
        chips.append('<span class="chip">Furnished</span>')
    for key in ("price", "fee"):
        if r.get(key):
            chips.append(f'<span class="chip">{e(short(r[key]))}</span>')
    initial = re.sub(r"[^A-Za-z0-9]", "", r["name"])[:1].upper() or "·"
    roles_attr = " ".join(roles)
    return (
        f'<a class="card glass" href="{e(r["url"])}" target="_blank" rel="noopener" data-roles="{e(roles_attr)}">'
        f'<span class="card-top"><span class="avatar">{e(initial)}</span>'
        f'<span class="name">{e(r["name"])}</span>{icon("arrow", "i ext")}</span>'
        f'<span class="note">{e(r["note"])}</span>'
        f'<span class="chips">{"".join(chips)}</span>'
        f'<span class="domain">{e(domain(r["url"]))}</span></a>'
    )


def compact_html(groups: list) -> str:
    """Nationwide sites, the same on every city page: one line of small links per group."""
    rows = []
    for cat, items in groups:
        links = "".join(
            f'<a class="mini{" warn" if r["note"].lower().startswith("warning") else ""}" href="{e(r["url"])}" '
            f'target="_blank" rel="noopener" title="{e(r["note"])}" data-roles="{e(" ".join(r["roles"]))}">'
            f'{e(r["name"])}{icon("arrow", "i ext")}</a>'
            for r in items
        )
        rows.append(f'<div class="crow">{icon(cat)}<span class="clabel">{e(CATEGORIES[cat])}</span>'
                    f'<div class="minis">{links}</div></div>')
    return (f'<section class="everywhere glass"><h2>Everywhere in the Netherlands</h2>{"".join(rows)}</section>'
            if rows else "")


def groups_html(groups: list, names: dict | None = None) -> str:
    out = []
    for cat, rows in groups:
        out.append(
            f'<section class="group" data-cat="{cat}"><h2>{icon(cat)}<span>{e(CATEGORIES[cat])}</span>'
            f'<span class="count">{len(rows)}</span></h2>'
            f'<div class="grid">{"".join(card(r, names) for r in rows)}</div></section>'
        )
    return "".join(out)


def operators(resources: list) -> list[tuple[str, list]]:
    """Companies with homes you can rent from them directly, across cities (home page)."""
    rows = [r for r in resources if "nl" not in r["cities"] and (
        r["category"] in ("managed", "coliving")
        or (r["category"] in ("shortstay", "student") and len(r["cities"]) >= 2))]
    groups = []
    for cat in ("managed", "coliving", "shortstay", "student"):
        part = sorted((r for r in rows if r["category"] == cat),
                      key=lambda r: (r.get("rank", 99), -len(r["cities"]), r["name"].lower()))
        if part:
            groups.append((cat, part))
    return groups


def project(lat: float, lon: float, p: dict) -> tuple[float, float]:
    return (lon - p["lon_min"]) * p["kx"] * p["scale"], (p["lat_max"] - lat) * p["scale"]


def map_svg(nl_map: dict, cities: list, active: str | None, role: str | None, compact: bool = False) -> str:
    p = nl_map["projection"]
    paths = "".join(f'<path d="{pr["d"]}"><title>{e(pr["name"])}</title></path>' for pr in nl_map["provinces"])
    dots = []
    for c in cities:
        x, y = project(c["lat"], c["lon"], p)
        cls = "city on" if c["slug"] == active else "city"
        href = url(f'{c["slug"]}/' + (f"{role}/" if role else ""))
        side = c.get("label", "right")
        lx, ly, anchor = {
            "right": (x + 7, y + 3.5, "start"), "left": (x - 7, y + 3.5, "end"),
            "top": (x, y - 8, "middle"), "bottom": (x, y + 14, "middle"),
        }[side]
        dots.append(
            f'<a class="{cls}" href="{href}" data-slug="{c["slug"]}" aria-label="{e(c["name"])}">'
            f'<circle class="halo" cx="{x:.1f}" cy="{y:.1f}" r="9"/><circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="3.2"/>'
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}">{e(c["name"])}</text></a>'
        )
    cls = "nlmap compact" if compact else "nlmap"
    return (f'<svg class="{cls}" viewBox="{nl_map["viewBox"]}" role="img" aria-label="Map of the Netherlands">'
            f'<g class="land">{paths}</g><g class="cities">{"".join(dots)}</g></svg>')


def role_switch(city: str | None, role: str | None, with_all: bool) -> str:
    items = []
    if with_all:
        href = url(f"{city}/") if city else url()
        items.append(f'<a href="{href}" class="{"on" if not role else ""}" data-role="">All</a>')
    for slug, meta in ROLES.items():
        href = url(f"{city}/{slug}/") if city else url(f"?role={slug}")
        items.append(f'<a href="{href}" class="{"on" if role == slug else ""}" data-role="{slug}">{meta["label"]}</a>')
    return f'<nav class="seg glass" aria-label="Who are you">{"".join(items)}</nav>'


def city_picker(cities: list, active: str | None) -> str:
    chips = "".join(
        f'<a class="cchip{" on" if c["slug"] == active else ""}" href="{url(c["slug"] + "/")}" data-slug="{c["slug"]}" '
        f'data-q="{e((c["name"] + " " + c.get("name_nl", "") + " " + " ".join(c.get("nearby", []))).lower())}">{e(c["name"])}</a>'
        for c in cities
    )
    return (f'<div class="picker"><label class="search glass">{icon("portal")}'
            f'<input id="q" type="search" placeholder="City or town" autocomplete="off" aria-label="Search a city or town"></label>'
            f'<div class="cchips">{chips}</div></div>')


def facts_html(facts: list) -> str:
    shown = [f for f in facts if f.get("home")][:4]
    if not shown:
        return ""
    items = "".join(
        f'<a class="fact glass" href="{e(f["source"])}" target="_blank" rel="noopener">'
        f'<span class="v">{e(f.get("display") or f["value"])}</span><span class="l">{e(f["label"])}</span>'
        f'<span class="s">{e(short_source(f))} · {e(f.get("year", ""))}</span></a>'
        for f in shown
    )
    return f'<section class="facts">{items}</section>'


def short_source(f: dict) -> str:
    return f.get("source_short") or re.split(r"[,(/]", f.get("source_name") or domain(f["source"]))[0].strip()


def city_fact(facts: list, slug: str) -> str:
    f = next((f for f in facts if f.get("city") == slug), None)
    if not f:
        return ""
    return (f'<a class="pill glass" href="{e(f["source"])}" target="_blank" rel="noopener">'
            f'<b>{e(f.get("display") or f["value"])}</b> {e(f["label"])} · {e(short_source(f))} {e(f.get("year", ""))}</a>')


def page(title: str, desc: str, path: str, body: str, cities: list, jsonld: dict | None = None) -> str:
    canonical = SITE_URL + "/" + path
    city_json = json.dumps([{"s": c["slug"], "n": c["name"]} for c in cities], separators=(",", ":"))
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, separators=(",", ":"))}</script>' if jsonld else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canonical)}">
<meta name="theme-color" content="#050505">
<meta property="og:type" content="website">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:image" content="{e(SITE_URL)}/assets/og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{url('assets/favicon.svg')}" type="image/svg+xml">
<link rel="stylesheet" href="{url('assets/style.css')}">
{ld}
</head>
<body data-base="{e(BASE)}">
<div class="bg" aria-hidden="true"></div>
<header class="top">
  <a class="brand" href="{url()}"><span class="logo">{icon("pin")}</span><span>housing<b>netherlands</b></span></a>
  <a class="gh glass" href="{REPO}" target="_blank" rel="noopener">{icon("github")}<span>Star</span></a>
</header>
{body}
<footer class="foot">
  <span>Checked {TODAY} · Not affiliated with any site listed</span>
  <a href="{REPO}/blob/main/CONTRIBUTING.md" target="_blank" rel="noopener">Add or fix a link</a>
  <a href="{REPO}" target="_blank" rel="noopener">{icon("star")} Open source</a>
</footer>
<script>window.CITIES={city_json}</script>
<script src="{url('assets/app.js')}" defer></script>
</body>
</html>
"""


# ---------------------------------------------------------------- pages

def home(resources, cities, nl_map, facts) -> str:
    national = grouped(pick(resources, None, None), None, None)
    n_sites = len(resources)
    body = f"""
<main>
  <section class="hero">
    <div class="hero-text">
      <h1>Find a home in<br>the Netherlands</h1>
      <p class="sub">{n_sites} websites that actually help. Pick who you are and a city.</p>
      {role_switch(None, None, False)}
      {city_picker(cities, None)}
    </div>
    <div class="hero-map glass">{map_svg(nl_map, cities, None, None)}</div>
  </section>
  {facts_html(facts)}
  <div class="section-title"><h2>Homes you can book</h2></div>
  <div class="groups">{groups_html(operators(resources), {c["slug"]: c["name"] for c in cities})}</div>
  <div class="section-title gap"><h2>Everywhere in the Netherlands</h2></div>
  <div class="groups">{groups_html(national)}</div>
</main>"""
    title = "Housing in the Netherlands: every website to find a room or home"
    desc = ("Find housing in the Netherlands. Pick your city and whether you are a student, PhD or working, and see "
            "every website that helps: student housing, managed apartments, landlords and alerts.")
    ld = {"@context": "https://schema.org", "@type": "WebSite", "name": "housing-netherlands", "url": SITE_URL + "/",
          "description": desc}
    return page(title, desc, "", body, cities, ld)


def city_page(resources, cities, nl_map, facts, c, role: str | None) -> str:
    items = pick(resources, c["slug"], role)
    local = [r for r in items if "nl" not in r["cities"]]
    national = [r for r in items if "nl" in r["cities"]]
    groups = grouped(local, c["slug"], role)
    national_groups = grouped(national, None, None)
    who = ROLES[role]["label"] if role else "Everyone"
    near = ", ".join(c.get("nearby", []))
    body = f"""
<main>
  <section class="head">
    <div class="head-text">
      <p class="crumb"><a href="{url()}">Netherlands</a> / <a href="{url(c['slug'] + '/')}">{e(c['name'])}</a></p>
      <h1>{e(c['name'])} <span class="muted">· {e(who)}</span></h1>
      <p class="sub">{len(items)} websites for {e(ROLES[role]['phrase'] if role else 'housing')} in {e(c['name'])}{(' · also ' + e(near)) if near else ''}</p>
      {role_switch(c['slug'], role, True)}
      {city_fact(facts, c['slug'])}
    </div>
    <div class="head-map glass">{map_svg(nl_map, cities, c['slug'], role, compact=True)}</div>
  </section>
  <div class="groups">{groups_html(groups)}</div>
  {compact_html(national_groups)}
  <section class="more">{city_picker(cities, c['slug'])}</section>
</main>"""
    name = c["name"] + (f" ({c['name_nl']})" if c.get("name_nl") else "")
    top = [r["name"] for _, rows in groups for r in rows][:3]
    if role:
        title = f"{ROLES[role]['seo']} in {c['name']}: every website"
        desc = (f"{ROLES[role]['seo']} in {name}: {len(items)} websites, from "
                f"{', '.join(top)} to alerts and tenant help. Who can rent and how to get in.")
    else:
        title = f"Housing in {c['name']}: student, PhD and expat rental websites"
        desc = (f"Every website to find a room or apartment in {name}: student housing, managed apartments, landlords, "
                f"agents and alerts, filtered for students, PhDs and working people.")
    path = f"{c['slug']}/" + (f"{role}/" if role else "")
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": title,
          "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": r["name"], "url": r["url"]}
                              for i, r in enumerate(items[:50])]}
    return page(title, desc[:300], path, body, cities, ld)


def not_found(cities) -> str:
    body = f"""<main><section class="head"><div class="head-text"><h1>Not found</h1>
<p class="sub"><a href="{url()}">Back to the map</a></p></div></section></main>"""
    return page("Not found · housing-netherlands", "Page not found.", "404.html", body, cities)


# ---------------------------------------------------------------- README

def readme_list(resources, cities) -> str:
    lines = ["<!-- list:start -->", "", "## The list", "",
             f"{len(resources)} websites, last checked {TODAY}. Roles: 🎓 student · 🔬 PhD · 💼 working.", ""]
    mark = {"student": "🎓", "phd": "🔬", "worker": "💼"}

    def row(r):
        acc = ACCESS.get(r["access"])
        bits = [b for b in (acc, r.get("price")) if b]
        meta = f" · {' · '.join(bits)}" if bits else ""
        return f"- [{r['name']}]({r['url']}) {''.join(mark[x] for x in ('student', 'phd', 'worker') if x in r['roles'])} {r['note']}{meta}"

    lines += ["### Everywhere in the Netherlands", ""]
    for cat, rows in grouped(pick(resources, None, None), None, None):
        lines += [f"**{CATEGORIES[cat]}**", ""] + [row(r) for r in rows] + [""]
    for c in cities:
        local = [r for r in resources if c["slug"] in r["cities"]]
        if not local:
            continue
        lines += [f"<details><summary><b>{c['name']}</b> ({len(local)})</summary>", ""]
        for cat, rows in grouped(local, c["slug"], None):
            lines += [f"**{CATEGORIES[cat]}**", ""] + [row(r) for r in rows] + [""]
        lines += ["</details>", ""]
    lines.append("<!-- list:end -->")
    return "\n".join(lines)


def update_readme(resources, cities) -> None:
    path = ROOT / "README.md"
    if not path.exists():
        return
    text = path.read_text()
    new = re.sub(r"<!-- list:start -->.*<!-- list:end -->", lambda _: readme_list(resources, cities), text, flags=re.S)
    if new != text:
        path.write_text(new)


# ---------------------------------------------------------------- main

def write(rel: str, content: str) -> None:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def main() -> None:
    resources, cities, nl_map, facts = load()
    errors = validate(resources, cities)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(1)
    if "--check" in sys.argv:
        print(f"data ok: {len(resources)} resources, {len(cities)} cities")
        return
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "site", OUT)
    paths = [""]
    write("index.html", home(resources, cities, nl_map, facts))
    for c in cities:
        write(f"{c['slug']}/index.html", city_page(resources, cities, nl_map, facts, c, None))
        paths.append(f"{c['slug']}/")
        for role in ROLES:
            write(f"{c['slug']}/{role}/index.html", city_page(resources, cities, nl_map, facts, c, role))
            paths.append(f"{c['slug']}/{role}/")
    write("404.html", not_found(cities))
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          + "".join(f"<url><loc>{SITE_URL}/{p}</loc><lastmod>{TODAY}</lastmod></url>" for p in paths) + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    write(".nojekyll", "")
    update_readme(resources, cities)
    print(f"built {len(paths)} pages, {len(resources)} resources -> {OUT}")


if __name__ == "__main__":
    main()
