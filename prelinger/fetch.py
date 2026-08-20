"""Download a proxy or master derivative per archive.org item."""

import internetarchive as ia

from . import config


def pick_file(item, formats: list[str]):
    """First file matching the format priority list; smallest if several."""
    files = list(item.get_files())
    for fmt in formats:
        matches = [f for f in files if f.format == fmt]
        if matches:
            return min(matches, key=lambda f: int(f.size or 0))
    return None


def fetch_item(identifier: str, tier: str = "proxy") -> str | None:
    """Download the chosen derivative into media/<tier>s/<identifier>/.

    Returns the local path, or None when no matching derivative exists.
    Skips files already on disk (internetarchive checksums them).
    """
    formats = config.PROXY_FORMATS if tier == "proxy" else config.MASTER_FORMATS
    dest_root = config.PROXIES if tier == "proxy" else config.MASTERS
    item = ia.get_item(identifier)
    if not item.exists:
        raise ValueError(f"archive.org item not found: {identifier}")
    f = pick_file(item, formats)
    if f is None:
        return None
    # resolve() the media symlink and pass destdir, or the library's
    # path-traversal guard (which checks against destdir/cwd) trips
    base = dest_root.resolve()
    dest = base / identifier / f.name
    if not dest.exists():
        f.download(file_path=f"{identifier}/{f.name}", destdir=str(base), retries=5)
    return str(dest)


def local_source(identifier: str) -> tuple[str, str] | None:
    """Best source already on disk: (path, tier), preferring master."""
    for root, tier in ((config.MASTERS, "master"), (config.PROXIES, "proxy")):
        d = root / identifier
        if d.is_dir():
            vids = sorted(
                p for p in d.iterdir()
                if p.suffix.lower() in (".mp4", ".m4v", ".mpg", ".mpeg", ".avi", ".mov")
            )
            if vids:
                return str(vids[0]), tier
    return None
