import cv2
import requests
import numpy as np
from PIL import Image
from io import BytesIO
import re
from concurrent.futures import ThreadPoolExecutor


MIN_SIZE = 128

def sanitize_username(u):
    return re.sub(r"[^a-zA-Z0-9_-]", "_", u)

def image_to_jpeg_bytes(img):
    if img.dtype != np.uint8:
        img = (img * 255).astype(np.uint8)

    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

    buf = BytesIO()
    Image.fromarray(img).save(buf, format="JPEG", quality=90)
    buf.seek(0)
    return buf.read()

def is_blurry(image, threshold=8):

    if isinstance(image, Image.Image):
        img = np.array(image)
    else:
        img = image

    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    variance = cv2.Laplacian(gray, cv2.CV_64F).var()

    print("Blur score:", variance)

    return variance < threshold, variance


def pick_worst(sev_list):

    order = ["none", "low", "mild", "moderate", "high", "severe", "very_severe"]

    valid = [
        str(s).lower().strip()
        for s in sev_list
        if s and str(s).lower().strip() in order
    ]

    if not valid:
        return "unknown"

    return sorted(valid, key=lambda x: order.index(x))[-1]

def download_image(url):

    r = requests.get(url, timeout=30)
    r.raise_for_status()

    img_array = np.frombuffer(r.content, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Invalid image data")

    h, w = img.shape[:2]

    if w < MIN_SIZE or h < MIN_SIZE:
        raise ValueError(f"Image too small ({w}x{h})")

    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    return Image.fromarray(img)

def download_images(top_url, front_url=None, back_url=None):

    with ThreadPoolExecutor(max_workers=3) as executor:

        f_top = executor.submit(download_and_check_blur, top_url, "top")

        f_front = executor.submit(
            download_and_check_blur, front_url, "front"
        ) if front_url else None

        f_back = executor.submit(
            download_and_check_blur, back_url, "back"
        ) if back_url else None

        top = f_top.result()
        front = f_front.result() if f_front else None
        back = f_back.result() if f_back else None

    return top, front, back

def download_and_check_blur(url, image_type):

    img = download_image(url)

    is_blur, blur_score = is_blurry(img)

    if is_blur:
        raise ValueError(
            f"{image_type} image is blurry (score={blur_score}). Please upload clearer photo."
        )

    return img