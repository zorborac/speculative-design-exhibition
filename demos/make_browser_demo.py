"""Generate demos/browser_demo.html layering WebM assets: backgrounds under cutouts.

Reads clips.csv so matte=no assets render as the back layer. Proof of the
browser playback path for the later generative/interactive "magic mirror".
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "media" / "assets"
OUT = Path(__file__).resolve().parent / "browser_demo.html"

opaque_stems = set()
with open(ROOT / "data" / "clips.csv", newline="") as f:
    for r in csv.DictReader(f):
        if r.get("clip_path") and r.get("matte", "").strip().lower() in ("no", "false", "0"):
            opaque_stems.add(Path(r["clip_path"]).stem)

webms = sorted(ASSETS.glob("*.webm"), key=lambda p: (p.stem not in opaque_stems, p.name))
videos = "\n".join(
    f'  <video src="../media/assets/{p.name}" autoplay loop muted playsinline '
    f'class="{"bg" if p.stem in opaque_stems else "fg"}"></video>'
    for p in webms
)
OUT.write_text(f"""<!doctype html>
<meta charset="utf-8">
<title>alpha asset demo</title>
<style>
  body {{ margin: 0; background: #111; height: 100vh; overflow: hidden; }}
  video {{ position: absolute; }}
  .bg {{ inset: 0; width: 100vw; height: 100vh; object-fit: cover; }}
  .fg {{ max-width: 45vw; bottom: 0; animation: drift 14s ease-in-out infinite alternate; }}
  .fg:nth-of-type(odd) {{ left: 8vw; }}
  .fg:nth-of-type(even) {{ right: 8vw; scale: 0.7; animation-direction: alternate-reverse; }}
  @keyframes drift {{ from {{ translate: 0 0; }} to {{ translate: 6vw -4vh; }} }}
</style>
{videos}
""")
print(f"wrote {OUT}: {len(opaque_stems & {p.stem for p in webms})} bg + "
      f"{len([p for p in webms if p.stem not in opaque_stems])} fg layers")
