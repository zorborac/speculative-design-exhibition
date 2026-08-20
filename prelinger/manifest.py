"""CSV manifests: candidates.csv (search pool) and clips.csv (curation list).

Both are git-tracked and hand-edited by the team, so reads must tolerate
extra columns and writes must preserve them.
"""

import csv
from pathlib import Path

CANDIDATE_FIELDS = ["identifier", "title", "year", "description", "url", "notes"]
CLIP_FIELDS = [
    "identifier",  # archive.org item id
    "start",       # HH:MM:SS(.ms) or seconds
    "end",
    "role",        # human-confirmed semantic role
    "suggested_roles",  # written by autotag: "role:score, role:score"
    "tags",
    "matte",       # yes (default) -> person matting; no -> passthrough asset
    "fit",         # pad (default) | fill (zoom-crop, for backgrounds)
    "status",      # curation state; "select" marks rows for master re-fetch
    "cut_tier",    # written by cut: proxy | master
    "clip_path",   # written by cut
    "notes",
]


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def write_rows(path: Path, rows: list[dict], base_fields: list[str]) -> None:
    fields = list(base_fields)
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def upsert(rows: list[dict], new: list[dict], key: str = "identifier") -> list[dict]:
    """Merge new rows into existing ones without clobbering hand-edits."""
    by_key = {r[key]: r for r in rows}
    for n in new:
        if n[key] in by_key:
            for k, v in n.items():
                if v and not by_key[n[key]].get(k):
                    by_key[n[key]][k] = v
        else:
            rows.append(n)
    return rows


def parse_ts(ts: str) -> float:
    """'90', '1:30' or '00:01:30.5' -> seconds."""
    parts = [float(p) for p in str(ts).strip().split(":")]
    sec = 0.0
    for p in parts:
        sec = sec * 60 + p
    return sec
