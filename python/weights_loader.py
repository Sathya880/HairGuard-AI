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

        # Check if all weights already exist
        if all(os.path.exists(f"weights/{f}") for f in FILES):
            logger.info("✓ All weights already present")
            _downloaded = True
            return

        for file in FILES:

            local_path = f"weights/{file}"

            if os.path.exists(local_path):
                logger.info(f"✓ weight already exists: {local_path}")
                continue

            url = BASE_URL + file
            logger.info(f"⬇ downloading {url}")

            try:
                r = requests.get(url, stream=True, timeout=60)
                r.raise_for_status()

                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(8192):
                        if chunk:
                            f.write(chunk)

                logger.info(f"✓ downloaded {local_path}")

            except Exception as e:
                logger.error(f"❌ Failed downloading {file}: {e}")
                raise

        _downloaded = True