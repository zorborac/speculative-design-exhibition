"""Paths and constants shared across pipeline stages."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEDIA = PROJECT_ROOT / "media"  # symlink -> /Volumes/PlayaYRaya/speculative_film
PROXIES = MEDIA / "proxies"
MASTERS = MEDIA / "masters"
CLIPS = MEDIA / "clips"
ASSETS = MEDIA / "assets"
THUMBS = MEDIA / "thumbs"

DATA = PROJECT_ROOT / "data"
CANDIDATES_CSV = DATA / "candidates.csv"
CLIPS_CSV = DATA / "clips.csv"
CONTACT_SHEET = DATA / "contact_sheet.html"
CREDITS_MD = DATA / "credits.md"

# Output spec (settled): 1080p landscape, 24fps.
WIDTH = 1920
HEIGHT = 1080
FPS = 24

COLLECTION = "prelinger"

# archive.org "format" strings tried in order when picking a file to download.
PROXY_FORMATS = ["512Kb MPEG4", "h.264", "MPEG4"]
MASTER_FORMATS = ["h.264 HD", "MPEG2", "h.264", "MPEG4"]

# Vocabulary for CLIP-assisted role suggestions; the final `role` column in
# clips.csv is always human-confirmed.
ROLE_VOCAB = {
    "thought": "a person deep in thought, daydreaming or pondering alone",
    "public": "a crowd of people in a public space",
    "market": "a marketplace, trading floor or shop where things are bought and sold",
    "commodity": "close-up of products, goods or merchandise",
    "machine": "industrial machinery or technology in operation",
    "interior": "a quiet domestic interior scene",
    "speech": "a person speaking, lecturing or broadcasting to others",
    "city": "city streets with traffic and buildings",
}


def ensure_media_dirs() -> None:
    if not MEDIA.exists():
        raise SystemExit(
            f"{MEDIA} is missing — is /Volumes/PlayaYRaya mounted? "
            "The media dir is a symlink onto that volume."
        )
    for d in (PROXIES, MASTERS, CLIPS, ASSETS, THUMBS):
        d.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(exist_ok=True)
