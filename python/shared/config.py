# shared/config.py
import logging
import os
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from io import BytesIO
from typing import Optional

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

AWS_BUCKET = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

_s3 = None


def _get_s3_client():
    global _s3
    if _s3 is not None:
        return _s3

    if not all([AWS_BUCKET, AWS_REGION, AWS_ACCESS_KEY, AWS_SECRET_KEY]):
        raise RuntimeError("AWS S3 credentials not configured")

    import boto3
    from botocore.config import Config

    _s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        config=Config(
            region_name=AWS_REGION,
            retries={"max_attempts": 3, "mode": "standard"},
            max_pool_connections=10,
        ),
    )
    return _s3


S3_EXECUTOR = ThreadPoolExecutor(max_workers=4)


def image_to_jpeg_bytes(img) -> Optional[bytes]:

    if img is None:
        return None

    if not isinstance(img, np.ndarray):
        img = np.array(img)

    if img.dtype != np.uint8:
        img = np.clip(img * 255, 0, 255).astype(np.uint8)

    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

    buf = BytesIO()
    Image.fromarray(img).save(buf, format="JPEG", quality=90, optimize=True)
    buf.seek(0)

    return buf.read()


def _upload_sync(image_bytes, user_id):

    key = f"results/{user_id}/overlays/{uuid.uuid4().hex}.jpg"

    _get_s3_client().put_object(
        Bucket=AWS_BUCKET,
        Key=key,
        Body=image_bytes,
        ContentType="image/jpeg",
        CacheControl="public,max-age=31536000",
    )

    return f"https://{AWS_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"


def upload_overlay_async(image_bytes, user_id) -> Optional[Future]:

    if image_bytes is None:
        return None

    return S3_EXECUTOR.submit(_upload_sync, image_bytes, str(user_id))