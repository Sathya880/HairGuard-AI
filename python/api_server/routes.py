import logging
import os
import uuid
from io import BytesIO

import boto3
from PIL import Image
from flask import request, jsonify

from inference_worker.services import run_analysis

logger = logging.getLogger(__name__)


def get_s3():

    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION"),
    )


def load_s3_image(key):

    bucket = os.getenv("AWS_BUCKET_NAME")

    if not bucket:
        raise RuntimeError("AWS_BUCKET_NAME not configured")

    s3 = get_s3()

    obj = s3.get_object(
        Bucket=bucket,
        Key=key
    )

    return Image.open(BytesIO(obj["Body"].read())).convert("RGB")


def register_routes(app):

    @app.route("/upload-url", methods=["POST"])
    def create_upload_url():

        try:

            data = request.get_json(force=True) or {}

            user_id = data.get("userId")

            if not user_id:
                return jsonify({"error": "userId required"}), 400

            bucket = os.getenv("AWS_BUCKET_NAME")

            file_key = f"uploads/{user_id}/{uuid.uuid4().hex}.jpg"

            s3 = get_s3()

            url = s3.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": bucket,
                    "Key": file_key,
                    "ContentType": "image/jpeg"
                },
                ExpiresIn=300
            )

            return jsonify({
                "uploadUrl": url,
                "fileKey": file_key
            })

        except Exception as e:

            logger.exception("upload url error")

            return jsonify({"error": str(e)}), 500


    @app.route("/analyze", methods=["POST"])
    def analyze():

        try:

            data = request.get_json(force=True) or {}

            top_key = data.get("topImageKey")
            front_key = data.get("frontImageKey")
            back_key = data.get("backImageKey")

            if not top_key:
                return jsonify({
                    "success": False,
                    "error": "topImageKey is required"
                }), 400

            top_img = load_s3_image(top_key)

            front_img = load_s3_image(front_key) if front_key else None
            back_img = load_s3_image(back_key) if back_key else None

            result = run_analysis(
                top_image=top_img,
                front_image=front_img,
                back_image=back_img,
                flashcard_answers=data.get("flashcardAnswers", {}),
                user_id=data.get("userId", "anonymous"),
                previous_score=data.get("previousHairScore"),
                previous_dandruff=data.get("previousDandruffSeverity"),
            )

            return jsonify({"success": True, **result})

        except ValueError as e:

            logger.warning(f"validation error: {e}")

            return jsonify({"success": False, "error": str(e)}), 422

        except Exception as e:

            logger.exception("analyze endpoint error")

            return jsonify({"success": False, "error": str(e)}), 500