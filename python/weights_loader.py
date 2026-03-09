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
            logger.info("✓ weights already downloaded in this session")
            return

        os.makedirs("weights", exist_ok=True)

        # check if all files already exist
        if all(os.path.exists(f"weights/{f}") for f in FILES):
            logger.info("✓ all weights already exist locally")
            _downloaded = True
            return

        for file in FILES:

            local_path = f"weights/{file}"

            if os.path.exists(local_path):
                logger.info(f"✓ weight exists: {local_path}")
                continue

            url = BASE_URL + file
            logger.info(f"⬇ downloading {url}")

            try:
                response = requests.get(url, stream=True, timeout=60)
                response.raise_for_status()

                with open(local_path, "wb") as f:
                    for chunk in response.iter_content(8192):
                        if chunk:
                            f.write(chunk)

                logger.info(f"✓ downloaded {file}")

            except Exception as e:
                logger.error(f"❌ download failed for {file}: {e}")
                raise

        _downloaded = True