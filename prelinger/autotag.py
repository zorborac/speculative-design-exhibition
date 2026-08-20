"""CLIP-assisted semantic role suggestions for cut clips.

Writes suggested_roles ("role:score, ...") into clips.csv; the team confirms
by filling the role column. Requires the ml extra: uv sync --extra ml
"""

import subprocess
import tempfile
from pathlib import Path

from . import config

_state = None

N_FRAMES = 8


def _load():
    global _state
    if _state is None:
        import open_clip
        import torch

        device = "mps" if torch.backends.mps.is_available() else "cpu"
        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="laion2b_s34b_b79k"
        )
        tokenizer = open_clip.get_tokenizer("ViT-B-32")
        model = model.to(device).eval()
        prompts = list(config.ROLE_VOCAB.values())
        with torch.no_grad():
            text = model.encode_text(tokenizer(prompts).to(device))
            text = text / text.norm(dim=-1, keepdim=True)
        _state = (model, preprocess, text, device)
    return _state


def suggest_roles(clip_path: str, top_k: int = 3) -> str:
    import torch
    from PIL import Image

    model, preprocess, text, device = _load()
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", clip_path,
             "-vf", f"thumbnail,fps=1", "-frames:v", str(N_FRAMES),
             f"{td}/f%02d.jpg"],
            check=True,
        )
        frames = sorted(Path(td).glob("*.jpg"))
        if not frames:
            return ""
        imgs = torch.stack([preprocess(Image.open(f)) for f in frames]).to(device)
        with torch.no_grad():
            feats = model.encode_image(imgs)
            feats = feats / feats.norm(dim=-1, keepdim=True)
            probs = (100.0 * feats @ text.T).softmax(dim=-1).mean(dim=0)
    roles = list(config.ROLE_VOCAB)
    ranked = sorted(zip(roles, probs.tolist()), key=lambda x: -x[1])[:top_k]
    return ", ".join(f"{r}:{p:.2f}" for r, p in ranked)
