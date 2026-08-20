"""Search the Prelinger collection and build the curation contact sheet."""

import html

import internetarchive as ia

from . import config
from .manifest import CANDIDATE_FIELDS, read_rows, upsert, write_rows


def search(query: str, limit: int = 40, sort: str = "downloads desc") -> list[dict]:
    q = f"collection:{config.COLLECTION} AND mediatype:movies AND ({query})"
    results = ia.search_items(
        q, fields=["identifier", "title", "year", "description"], sorts=[sort]
    )
    found = []
    for hit in results:
        desc = hit.get("description", "")
        if isinstance(desc, list):
            desc = " ".join(desc)
        found.append(
            {
                "identifier": hit["identifier"],
                "title": str(hit.get("title", "")),
                "year": str(hit.get("year", "")),
                "description": " ".join(str(desc).split())[:500],
                "url": f"https://archive.org/details/{hit['identifier']}",
                "query": query,
            }
        )
        if len(found) >= limit:
            break
    rows = upsert(read_rows(config.CANDIDATES_CSV), found)
    write_rows(config.CANDIDATES_CSV, rows, CANDIDATE_FIELDS)
    return found


def build_contact_sheet() -> None:
    """Static HTML of archive.org embeds so the team screens candidates
    in a browser without downloading anything."""
    rows = read_rows(config.CANDIDATES_CSV)
    cards = []
    for r in rows:
        ident = html.escape(r["identifier"])
        cards.append(f"""
    <div class="card">
      <iframe src="https://archive.org/embed/{ident}" loading="lazy"
              allowfullscreen webkitallowfullscreen mozallowfullscreen></iframe>
      <h3><a href="{html.escape(r.get('url', ''))}" target="_blank">{html.escape(r.get('title') or ident)}</a>
          <span class="year">{html.escape(r.get('year', ''))}</span></h3>
      <p class="id">{ident}</p>
      <p>{html.escape((r.get('description') or '')[:300])}</p>
    </div>""")
    page = f"""<!doctype html>
<meta charset="utf-8">
<title>Prelinger candidates — {len(rows)} items</title>
<style>
  body {{ font-family: -apple-system, sans-serif; background: #111; color: #eee; margin: 2rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); gap: 2rem; }}
  .card iframe {{ width: 100%; aspect-ratio: 4/3; border: 0; background: #000; }}
  .card h3 {{ margin: .5rem 0 0; font-size: 1rem; }}
  .card a {{ color: #8cf; text-decoration: none; }}
  .year {{ color: #999; font-weight: normal; margin-left: .5em; }}
  .id {{ color: #777; font-family: monospace; font-size: .8rem; margin: .2rem 0; }}
  .card p {{ font-size: .85rem; color: #bbb; line-height: 1.4; }}
</style>
<h1>Prelinger candidates ({len(rows)})</h1>
<p>Add selects to <code>data/clips.csv</code> with identifier + start/end timestamps.</p>
<div class="grid">{''.join(cards)}
</div>
"""
    config.CONTACT_SHEET.write_text(page)
