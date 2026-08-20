"""Cut clips.csv rows out of downloaded sources, normalized to the output spec."""

import subprocess

from . import config
from .fetch import local_source
from .manifest import parse_ts


def clip_name(identifier: str, start: str, end: str) -> str:
    fmt = lambda ts: f"{parse_ts(ts):08.2f}".replace(".", "_")
    return f"{identifier}__{fmt(start)}-{fmt(end)}"


def cut_clip(row: dict, force: bool = False) -> dict:
    """Cut + normalize one manifest row -> ProRes 422 intermediate in media/clips.

    Updates and returns the row (clip_path, cut_tier). Re-cuts when a better
    tier has appeared on disk since the last run.
    """
    src = local_source(row["identifier"])
    if src is None:
        raise FileNotFoundError(f"no downloaded source for {row['identifier']} — run fetch first")
    src_path, tier = src
    out = config.CLIPS / f"{clip_name(row['identifier'], row['start'], row['end'])}.mov"
    rel = str(out.relative_to(config.PROJECT_ROOT))  # repo-relative: portable across machines
    if out.exists() and row.get("cut_tier") == tier and not force:
        row["clip_path"] = rel
        return row

    start, end = parse_ts(row["start"]), parse_ts(row["end"])
    # src_crop (w:h:x:y) removes baked-in letterbox bars before scaling
    pre = f"crop={row['src_crop']}," if row.get("src_crop", "").strip() else ""
    if row.get("fit", "").strip().lower() == "fill":
        # backgrounds: zoom-crop to fill the frame instead of pillarboxing
        vf = (
            f"{pre}scale={config.WIDTH}:{config.HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={config.WIDTH}:{config.HEIGHT},"
            f"setsar=1,fps={config.FPS}"
        )
    else:
        vf = (
            f"{pre}scale={config.WIDTH}:{config.HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={config.WIDTH}:{config.HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
            f"setsar=1,fps={config.FPS}"
        )
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", src_path,
            "-vf", vf,
            "-c:v", "prores_ks", "-profile:v", "2",  # ProRes 422
            "-an",
            str(out),
        ],
        check=True,
    )
    row["cut_tier"] = tier
    row["clip_path"] = rel
    return row
