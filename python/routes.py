from flask import request, jsonify
from services import run_analysis
import model_registry
from utils import download_images


def register_routes(app):

    # ─────────────────────────────
    # HAIR ANALYSIS
    # ─────────────────────────────
    @app.route("/analyze", methods=["POST"])
    def analyze():

        try:

            if not model_registry.is_ready("hairloss_model"):
                return jsonify({
                    "success": False,
                    "error": "AI models still loading"
                }), 503

            data = request.get_json(force=True)

            user_id = data.get("userId")

            top_url = data.get("topImageUrl")
            front_url = data.get("frontImageUrl")
            back_url = data.get("backImageUrl")

            flashcard_answers = data.get("flashcardAnswers", {})

            previous_score = data.get("previousHairScore")
            previous_dandruff = data.get("previousDandruffSeverity")

            if not top_url:
                return jsonify({
                    "success": False,
                    "error": "topImageUrl required"
                }), 400

            # Download images from S3
            top_image, front_image, back_image = download_images(
                top_url,
                front_url,
                back_url
            )

            result = run_analysis(
                top_image,
                front_image,
                back_image,
                flashcard_answers,
                user_id,
                previous_score,
                previous_dandruff
            )

            return jsonify({
                "success": True,
                **result
            })

        except Exception as e:
            import traceback
            tb = traceback.format_exc()

            print(tb)

            return jsonify({
                "success": False,
                "error": str(e),
                "traceback": tb
            }), 500


    # ─────────────────────────────
    # ADAPTIVE ROUTINE
    # ─────────────────────────────
    @app.route("/adaptive-routine", methods=["POST"])
    def adaptive_routine():

        try:

            data = request.get_json(force=True)

            routine = model_registry.get("adaptive_routine_engine").generate(
                hairloss_severity=data.get("hairlossSeverity", "moderate"),
                dandruff_severity=data.get("dandruffSeverity", "moderate"),
                root_cause=data.get("rootCause", "general"),
                lifestyle_score=float(data.get("lifestyleScore", 50)),
                humidity=data.get("humidity", "normal"),
                pollution_level=data.get("pollutionLevel", "moderate"),
            )

            return jsonify({
                "success": True,
                "routine": routine
            })

        except Exception as e:
            import traceback
            traceback.print_exc()

            return jsonify({
                "success": False,
                "error": str(e)
            }), 500