"""OpenAI client + image download helpers (loads .env from repo root)."""
from __future__ import annotations

import base64
import io
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

from common import REPO_ROOT

_ENV_LOADED = False


def ensure_env() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    load_dotenv(REPO_ROOT / ".env")
    _ENV_LOADED = True


def get_client() -> OpenAI:
    ensure_env()
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set. Add it to .env in the project root.")
    return OpenAI(api_key=key)


def generate_image(prompt: str, cfg: dict):
    """Call Images API with optional fallback model."""
    client = get_client()
    model = cfg.get("openai_image_model", "gpt-image-1")
    api_size = cfg.get("openai_image_size", "1024x1024")
    try:
        return client.images.generate(model=model, prompt=prompt[:4000], size=api_size, n=1)
    except Exception as primary_err:
        fallback = cfg.get("openai_fallback_model")
        if not fallback or fallback == model:
            raise primary_err
        print(f"  Primary model {model} failed ({primary_err}); trying {fallback}...")
        return client.images.generate(model=fallback, prompt=prompt[:4000], size=api_size, n=1)


def save_image_response(response, out_path: Path, size: int) -> None:
    item = response.data[0]
    if getattr(item, "b64_json", None):
        raw = base64.b64decode(item.b64_json)
    elif getattr(item, "url", None):
        import urllib.request

        raw = urllib.request.urlopen(item.url, timeout=120).read()
    else:
        raise RuntimeError("OpenAI image response had no b64_json or url")
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    if img.size != (size, size):
        img = img.resize((size, size), Image.Resampling.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
