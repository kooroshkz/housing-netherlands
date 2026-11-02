# Contributing

Thanks for helping people find a home. Small fixes are the most valuable thing you can
send: a dead link, a changed rule, a new building.

## Quick way: open an issue

[Add a website](../../issues/new?template=add-a-site.yml) or
[fix one](../../issues/new?template=fix-a-site.yml). No code needed.

## Edit the data yourself

Everything lives in [`data/resources.json`](data/resources.json). One entry:

```json
{
  "id": "duwo",
  "name": "DUWO",
  "url": "https://www.duwo.nl/en/",
  "category": "student",
  "roles": ["student", "phd"],
  "cities": ["delft", "leiden", "den-haag", "amsterdam"],
  "access": "waitlist",
  "furnished": "both",
  "price": "€400–800",
  "fee": "€35 registration",
  "note": "Register early: waiting time counts",
  "source": "https://www.duwo.nl/en/...",
  "confidence": "verified"
}
```

| Field | Values |
|---|---|
| `category` | `managed`, `student`, `university`, `landlord`, `agent`, `coliving`, `newbuild`, `shortstay`, `social`, `portal`, `alerts`, `expat`, `help`, `scam` |
| `roles` | who may rent there: any of `student`, `phd`, `worker` |
| `cities` | slugs from [`data/cities.json`](data/cities.json), or `["nl"]` for the whole country |
| `access` | `first-come`, `lottery`, `waitlist`, `score`, `booking`, `university`, `varies`, `info`, `free`, `paid` |
| `note` | at most 60 characters: the one thing to know |
| `source` | a page that shows the rules you describe |
| `rank` | optional; lower shows first in its group |

Then check and preview:

```bash
python scripts/build.py --check
BASE=/ python scripts/build.py
python -m http.server -d _site
```

Open http://localhost:8000. The build also refreshes the list in the README.

## What belongs here

* Websites that list homes or rooms, or that help people get one (rights, alerts,
  expat and student help).
* No single private listings, no paid "guaranteed housing" schemes, no scams. If you
  are unsure about a site, open an issue instead.
* Keep the tone neutral; facts with a source.

## Add a city

Add it to [`data/cities.json`](data/cities.json) with its coordinates; the map,
pages and sitemap follow automatically.
