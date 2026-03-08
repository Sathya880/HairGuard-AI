import os
import logging
import requests
from threading import Lock

logger = logging.getLogger(__name__)

BASE_URL = "https://hair-app-user-images.s3.ap-south-1.amazonaws.com/models/"

FILES = [
    "attention_unet_hair.pth",
    "severity_model.pkl",
    "swin_scalp_presence.pth",
    "swin_dandruff_severity.pth"
]

_download_lock = Lock()
_downloaded = False


def download_weights():
    global _downloaded

    with _download_lock:

        if _downloaded:
            return

        os.makedirs("weights", exist_ok=True)

        for file in FILES:

            local_path = f"weights/{file}"

            if os.path.exists(local_path):
                logger.info(f"✓ weight already exists: {local_path}")
                continue

            url = BASE_URL + file
            logger.info(f"⬇ downloading {url}")

            r = requests.get(url, stream=True)
            r.raise_for_status()

            with open(local_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)

            logger.info(f"✓ downloaded {local_path}")

        _downloaded = True