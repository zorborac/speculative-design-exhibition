# Speculative Design Exhibition Film

Found-footage collage film for the TIAT speculative design book club
(*Speculative Everything*, Dunne & Raby). The world: you can only hold three
private thoughts at once; thoughts are traded as commodities. The artifact:
a "magic mirror" screen of clipped snippets from the
[Prelinger Archives](https://archive.org/details/prelinger).

## Setup

```sh
uv sync              # search / fetch / cut stages
uv sync --extra ml   # + matting (RVM) and autotag (CLIP)
```

Requires ffmpeg (`brew install ffmpeg`) and the `PlayaYRaya` volume mounted —
`media/` is a symlink to `/Volumes/PlayaYRaya/speculative_film` (proxies,
masters, cut clips, and assets live there, never in git).

## Pipeline

```sh
uv run prelinger search "telepathy"   # grow data/candidates.csv (+ contact sheet)
open data/contact_sheet.html          # screen candidates in the browser
# add rows to data/clips.csv: identifier,start,end + tags/notes
uv run prelinger fetch                # 512kb proxies for clips.csv identifiers
uv run prelinger cut                  # normalized 1080p/24 ProRes 422 clips
uv run prelinger matte                # alpha assets: ProRes 4444 .mov + VP9 .webm
uv run prelinger autotag              # CLIP role suggestions -> clips.csv
# mark keepers with status=select, then re-run at master quality:
uv run prelinger fetch --tier master && uv run prelinger cut && uv run prelinger matte --force
uv run prelinger credits              # data/credits.md for the placard
```

Manifest columns worth knowing: `matte=no` makes a clip an opaque background
asset instead of a person cutout; `status=select` marks rows for master
re-fetch; `role` is yours to fill (autotag only writes `suggested_roles`).

## Demos

```sh
uv run python demos/render_fixed_demo.py --bg media/clips/<bg>.mov \
    --fg media/assets/<fg>.mov          # fixed-film composite (mp4)
uv run python demos/make_browser_demo.py && open demos/browser_demo.html
```

Assets are dual-format on purpose: ProRes 4444 for DaVinci Resolve /
compositing, WebM alpha for the browser-based generative direction.
