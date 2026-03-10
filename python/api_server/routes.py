"""
API Gateway Routes
==================
Thin layer that receives requests from the Flutter app and
dispatches to the inference pipeline (in-process, no HTTP hop).
"""

import logging

from flask import request, jsonify

from inference_worker.services import run_analysis
from shared.utils import download_images

logger = logging.getLogger(__name__)


def register_routes(app):

    @app.route("/analyze", methods=["POST"])
    def analyze():
        """
        Main analysis endpoint.

        Accepts JSON:
          topImage          str   (required) — URL of top-view scalp photo
          frontImage        str   (optional)
          backImage         str   (optional)
          flashcardAnswers  dict  (optional)
          userId            str   (required)
          previousHairScore float (optional) — enables progress tracking
          previousDandruffSeverity str (optional)
        """
        try:
            data = request.get_json(force=True) or {}

            top_url   = data.get("topImage")
            front_url = data.get("frontImage")
            back_url  = data.get("backImage")

            if not top_url:
                return jsonify({
                    "success": False,
                    "error": "topImage is required"
                }), 400

            # Download + blur-check images in parallel
            top_img, front_img, back_img = download_images(
                top_url, front_url, back_url
            )

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
            # Image validation errors (blur, size, etc.)
            logger.warning(f"Validation error: {e}")
            return jsonify({"success": False, "error": str(e)}), 422

        except Exception as e:
            logger.exception("Analyze endpoint error")
            return jsonify({"success": False, "error": str(e)}), 500