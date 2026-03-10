"""
Weights Loader
==============
Downloads ML model weights from S3 on first boot.

Optimized for:
- Railway / Render ephemeral disk
- parallel download
- safe streaming
- retry on network failure
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import requests

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

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

MAX_WORKERS = int(os.getenv("WEIGHTS_DOWNLOAD_THREADS", 3))
RETRIES = 3

# ─────────────────────────────────────────────
# INTERNAL STATE
# ─────────────────────────────────────────────

_lock = Lock()
_downloaded = False
_http = requests.Session()


# ─────────────────────────────────────────────
# DOWNLOAD SINGLE FILE
# ─────────────────────────────────────────────

def _download_file(file_name: str) -> None:

    local = os.path.join(WEIGHTS_DIR, file_name)
    tmp = local + ".part"

    if os.path.exists(local):
        logger.info(f"✓ weight exists: {file_name}")
        return

    url = BASE_URL + file_name

    for attempt in range(RETRIES):

        try:

            logger.info(f"⬇ downloading {file_name} (attempt {attempt+1})")

            r = _http.get(url, stream=True, timeout=300)
            r.raise_for_status()

            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 64):
                    if chunk:
                        f.write(chunk)

            os.replace(tmp, local)

            logger.info(f"✅ saved {file_name}")
            return

        except Exception as e:

            logger.warning(f"retry {file_name} ({attempt+1}) → {e}")
            time.sleep(2)

    raise RuntimeError(f"failed to download {file_name}")


# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────

def download_weights() -> None:
    """
    Ensure all weight files exist locally.
    Thread safe.
    """

    global _downloaded

    with _lock:

        if _downloaded:
            return

        os.makedirs(WEIGHTS_DIR, exist_ok=True)

        missing = [
            f for f in FILES
            if not os.path.exists(os.path.join(WEIGHTS_DIR, f))
        ]

        if not missing:
            logger.info("✓ weights already present")
            _downloaded = True
            return

        logger.info(f"⬇ downloading {len(missing)} weight files")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            pool.map(_download_file, missing)

        _downloaded = True
        logger.info("✅ all weights ready")