"""Generate data/credits.md for the exhibition placard from clips.csv."""

from . import config
from .manifest import read_rows


def build_credits() -> int:
    clips = read_rows(config.CLIPS_CSV)
    candidates = {r["identifier"]: r for r in read_rows(config.CANDIDATES_CSV)}
    idents = sorted({r["identifier"] for r in clips if r.get("identifier")})
    lines = [
        "# Footage credits",
        "",
        "All source films from the Prelinger Archives via archive.org.",
        "",
    ]
    for ident in idents:
        meta = candidates.get(ident, {})
        title = meta.get("title") or ident
        year = f" ({meta['year']})" if meta.get("year") else ""
        lines.append(f"- *{title}*{year} — https://archive.org/details/{ident}")
    config.CREDITS_MD.write_text("\n".join(lines) + "\n")
    return len(idents)
