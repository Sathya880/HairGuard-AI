import os
import boto3
from dotenv import load_dotenv
import uuid
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from PIL import Image
import cv2


load_dotenv()

AWS_BUCKET = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

if not all([AWS_BUCKET, AWS_REGION, AWS_ACCESS_KEY, AWS_SECRET_KEY]):
    raise RuntimeError("AWS env vars missing")

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION,
)

# safer executor creation
CPU_COUNT = os.cpu_count() or 4
S3_EXECUTOR = ThreadPoolExecutor(max_workers=CPU_COUNT * 4)


# ─────────────────────────────────────────────────────────
# IMAGE → JPEG BYTES
# ─────────────────────────────────────────────────────────

def image_to_jpeg_bytes(img):

    if img is None:
        return None

    # ensure numpy array
    if not isinstance(img, np.ndarray):
        img = np.array(img)

    # convert float image
    if img.dtype != np.uint8:
        img = np.clip(img * 255, 0, 255).astype(np.uint8)

    # grayscale → rgb
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

    buffer = BytesIO()
    Image.fromarray(img).save(buffer, format="JPEG", quality=90)
    buffer.seek(0)

    return buffer.read()


# ─────────────────────────────────────────────────────────
# SYNC S3 UPLOAD
# ─────────────────────────────────────────────────────────

def _upload_overlay_sync(image_bytes, user_id):

    if image_bytes is None:
        return None

    user_id = str(user_id)

    key = f"results/{user_id}/overlays/{uuid.uuid4().hex}.jpg"

    s3.put_object(
        Bucket=AWS_BUCKET,
        Key=key,
        Body=image_bytes,
        ContentType="image/jpeg",
        CacheControl="public, max-age=31536000",
    )

    return f"https://{AWS_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"


# ─────────────────────────────────────────────────────────
# ASYNC UPLOAD
# ─────────────────────────────────────────────────────────

def upload_overlay_async(image_bytes, user_id):

    if image_bytes is None:
        return None

    # FIX: use correct executor
    return S3_EXECUTOR.submit(_upload_overlay_sync, image_bytes, user_id)