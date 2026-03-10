import logging
import re
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import requests
from PIL import Image


logger = logging.getLogger(__name__)

# ─────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────

MIN_SIZE = 128
MAX_DOWNLOAD_WORKERS = 3

# reuse executor instead of creating per request
DOWNLOAD_EXECUTOR = ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_WORKERS)

# persistent HTTP session (connection pooling)
HTTP_SESSION = requests.Session()


# ─────────────────────────────────────
# USERNAME SANITIZER
# ─────────────────────────────────────

def sanitize_username(username):

    return re.sub(r"[^a-zA-Z0-9_-]", "_", username)


# ─────────────────────────────────────
# IMAGE → JPEG BYTES
# ─────────────────────────────────────

def image_to_jpeg_bytes(img):

    if img is None:
        return None

    if not isinstance(img, np.ndarray):
        img = np.array(img)

    if img.dtype != np.uint8:
        img = np.clip(img * 255, 0, 255).astype(np.uint8)

    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

    buffer = BytesIO()

    Image.fromarray(img).save(
        buffer,
        format="JPEG",
        quality=90,
        optimize=True
    )

    buffer.seek(0)

    return buffer.read()


# ─────────────────────────────────────
# BLUR DETECTION
# ─────────────────────────────────────

def is_blurry(image, threshold=8):

    if isinstance(image, Image.Image):
        img = np.array(image)
    else:
        img = image

    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    variance = cv2.Laplacian(gray, cv2.CV_64F).var()

    logger.info(f"Blur score: {variance}")

    return variance < threshold, variance


# ─────────────────────────────────────
# SEVERITY HELPER
# ─────────────────────────────────────

def pick_worst(sev_list):

    order = [
        "none",
        "low",
        "mild",
        "moderate",
        "high",
        "severe",
        "very_severe"
    ]

    valid = [
        str(s).lower().strip()
        for s in sev_list
        if s and str(s).lower().strip() in order
    ]

    if not valid:
        return "unknown"

    return sorted(valid, key=lambda x: order.index(x))[-1]


# ─────────────────────────────────────
# IMAGE DOWNLOAD
# ─────────────────────────────────────

def download_image(url):

    try:

        response = HTTP_SESSION.get(url, timeout=30)

        response.raise_for_status()

        img_array = np.frombuffer(response.content, np.uint8)

        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Invalid image data")

        h, w = img.shape[:2]

        if w < MIN_SIZE or h < MIN_SIZE:
            raise ValueError(f"Image too small ({w}x{h})")

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        return Image.fromarray(img)

    except Exception as e:

        logger.exception(f"Image download failed: {url}")

        raise


# ─────────────────────────────────────
# PARALLEL DOWNLOAD
# ─────────────────────────────────────

def download_images(top_url, front_url=None, back_url=None):

    futures = []

    f_top = DOWNLOAD_EXECUTOR.submit(
        download_and_check_blur,
        top_url,
        "top"
    )

    futures.append(f_top)

    f_front = None
    f_back = None

    if front_url:

        f_front = DOWNLOAD_EXECUTOR.submit(
            download_and_check_blur,
            front_url,
            "front"
        )

        futures.append(f_front)

    if back_url:

        f_back = DOWNLOAD_EXECUTOR.submit(
            download_and_check_blur,
            back_url,
            "back"
        )

        futures.append(f_back)

    top = f_top.result()
    front = f_front.result() if f_front else None
    back = f_back.result() if f_back else None

    return top, front, back


# ─────────────────────────────────────
# DOWNLOAD + BLUR CHECK
# ─────────────────────────────────────

def download_and_check_blur(url, image_type):

    img = download_image(url)

    is_blur, blur_score = is_blurry(img)

    if is_blur:

        raise ValueError(
            f"{image_type} image is blurry "
            f"(score={blur_score}). Please upload clearer photo."
        )

    return img