"""Person matting with Robust Video Matting -> alpha assets.

Each cut clip becomes two assets: ProRes 4444 with alpha (compositing/Resolve)
and VP9 WebM with alpha (browser playback). Rows marked matte=no are passed
through as opaque background assets in the same two formats.

Requires the ml extra: uv sync --extra ml
"""

import os
import subprocess
from pathlib import Path

# Some RVM ops lack MPS kernels; let torch fall back to CPU for those.
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

from . import config

_model = None
_device = None


def _load_model():
    global _model, _device
    if _model is None:
        import torch

        _device = "mps" if torch.backends.mps.is_available() else "cpu"
        _model = torch.hub.load(
            "PeterL1n/RobustVideoMatting", "mobilenetv3", trust_repo=True
        )
        _model = _model.to(_device).eval()
    return _model, _device


def _raw_reader(path: str):
    return subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path,
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE,
    )


def _prores4444_writer(out: Path, pix_in: str):
    return subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "rawvideo", "-pix_fmt", pix_in,
         "-s", f"{config.WIDTH}x{config.HEIGHT}", "-r", str(config.FPS), "-i", "-",
         "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
         str(out)],
        stdin=subprocess.PIPE,
    )


def matte_clip(clip_path: str) -> Path:
    """RVM over one clip -> media/assets/<name>.mov (ProRes 4444 + alpha)."""
    import torch

    model, device = _load_model()
    out = config.ASSETS / (Path(clip_path).stem + ".mov")
    frame_bytes = config.WIDTH * config.HEIGHT * 3

    reader = _raw_reader(clip_path)
    writer = _prores4444_writer(out, "rgba")
    rec = [None] * 4
    with torch.no_grad():
        while True:
            buf = reader.stdout.read(frame_bytes)
            if len(buf) < frame_bytes:
                break
            src = (
                torch.frombuffer(bytearray(buf), dtype=torch.uint8)
                .reshape(config.HEIGHT, config.WIDTH, 3)
                .permute(2, 0, 1)[None]
                .to(device)
                .float()
                / 255.0
            )
            fgr, pha, *rec = model(src, *rec, downsample_ratio=0.25)
            rgba = torch.cat([fgr, pha], dim=1).clamp(0, 1)
            frame = (
                (rgba[0].permute(1, 2, 0) * 255).byte().cpu().numpy().tobytes()
            )
            writer.stdin.write(frame)
    reader.stdout.close()
    writer.stdin.close()
    writer.wait()
    if writer.returncode:
        raise RuntimeError(f"ffmpeg writer failed for {out}")
    return out


def passthrough_clip(clip_path: str) -> Path:
    """matte=no rows: opaque background asset, same container as matted ones."""
    out = config.ASSETS / (Path(clip_path).stem + ".mov")
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", clip_path,
         "-c:v", "prores_ks", "-profile:v", "2", "-an", str(out)],
        check=True,
    )
    return out


def to_webm(mov: Path, alpha: bool = True) -> Path:
    """Browser derivative of an asset .mov."""
    out = mov.with_suffix(".webm")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(mov),
           "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "32", "-row-mt", "1"]
    if alpha:
        cmd += ["-pix_fmt", "yuva420p", "-auto-alt-ref", "0"]
    else:
        cmd += ["-pix_fmt", "yuv420p"]
    subprocess.run(cmd + [str(out)], check=True)
    return out
