"""Fixed-film proof: composite alpha assets over a background via ffmpeg.

Usage:
  uv run python demos/render_fixed_demo.py --bg media/clips/<bg>.mov \
      --fg media/assets/<a>.mov --fg media/assets/<b>.mov \
      [--out demos/fixed_demo.mp4] [--dur 30]

This is the seed of the "device running code" path: a program decides
placement/timing and ffmpeg does the compositing.
"""

import argparse
import subprocess

POSITIONS = [
    "(W-w)/2:(H-h)/2",   # center
    "W/8:(H-h)/2",       # left third
    "W-w-W/8:(H-h)/2",   # right third
]
SCALES = [0.9, 0.6, 0.7]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bg", required=True, help="background clip (opaque)")
    ap.add_argument("--fg", action="append", default=[], help="alpha asset .mov (repeatable)")
    ap.add_argument("--out", default="demos/fixed_demo.mp4")
    ap.add_argument("--dur", type=float, default=30.0)
    args = ap.parse_args()

    inputs = ["-stream_loop", "-1", "-i", args.bg]
    for fg in args.fg:
        inputs += ["-stream_loop", "-1", "-i", fg]

    chains, last = [], "0:v"
    for i, _ in enumerate(args.fg, start=1):
        scale = SCALES[(i - 1) % len(SCALES)]
        pos = POSITIONS[(i - 1) % len(POSITIONS)]
        start = (i - 1) * 3  # stagger entrances
        chains.append(f"[{i}:v]scale=iw*{scale}:-1[fg{i}]")
        chains.append(
            f"[{last}][fg{i}]overlay={pos}:enable='gte(t,{start})'[v{i}]"
        )
        last = f"v{i}"
    fc = ";".join(chains) if chains else "[0:v]null[v0]"
    if not chains:
        last = "v0"

    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "warning", "-y", *inputs,
         "-filter_complex", fc, "-map", f"[{last}]",
         "-t", str(args.dur), "-r", "24",
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", args.out],
        check=True,
    )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
