"""
Weights Loader
==============
Downloads ML model weights from S3 on first boot (if not already present).

Storage strategy for Render 512 MB disk
----------------------------------------
Render's free tier has ephemeral disk — weights are re-downloaded on every
cold start. The files total ~300 MB so we download in parallel and skip any
file that already exists on disk (warm restart / persistent disk scenario).

The download is triggered lazily from model_registry.get() via each model's
factory, so the server is never blocked at startup.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import requests

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

# Override via WEIGHTS_BASE_URL env var to point at your own bucket path
BASE_URL = os.getenv(
    "WEIGHTS_BASE_URL",
    "https://hair-app-user-images.s3.ap-south-1.amazonaws.com/models/"
)

FILES = [
    "attention_unet_hair.pth",
    "severity_model.pkl",
    "swin_scalp_presence.pth",
    "swin_dandruff_severity.pth",
]

WEIGHTS_DIR = os.getenv("WEIGHTS_DIR", "weights")

# ─────────────────────────────────────────────
# Internal state
# ─────────────────────────────────────────────

_lock       = Lock()
_downloaded = False
_HTTP       = requests.Session()
_POOL       = ThreadPoolExecutor(max_workers=3, thread_name_prefix="weights-dl")


# ─────────────────────────────────────────────
# File download
# ─────────────────────────────────────────────

def _download_file(file_name: str) -> None:
    local = os.path.join(WEIGHTS_DIR, file_name)
    tmp   = local + ".part"

    if os.path.exists(local):
        logger.info(f"✓ weight exists: {file_name}")
        return

    url = BASE_URL + file_name
    logger.info(f"⬇  downloading: {url}")

    try:
        resp = _HTTP.get(url, stream=True, timeout=180)
        resp.raise_for_status()

        with open(tmp, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    fh.write(chunk)

        os.replace(tmp, local)
        logger.info(f"✅ saved: {file_name}")

    except Exception as exc:
        logger.error(f"❌ failed: {file_name} → {exc}")
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def download_weights() -> None:
    """
    Ensure all weight files are present locally.
    Thread-safe; idempotent (safe to call multiple times).
    """
    global _downloaded

    with _lock:
        if _downloaded:
            return

        os.makedirs(WEIGHTS_DIR, exist_ok=True)

        missing = [f for f in FILES
                   if not os.path.exists(os.path.join(WEIGHTS_DIR, f))]

        if not missing:
            logger.info("✓ all weights already on disk")
            _downloaded = True
            return

        logger.info(f"⬇  downloading {len(missing)} weight file(s) in parallel …")
        futures = [_POOL.submit(_download_file, f) for f in missing]
        for fut in futures:
            fut.result()   # re-raises on error

        _downloaded = True
        logger.info("✅ all model weights ready")