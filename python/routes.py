from flask import request, jsonify
from services import run_analysis
from utils import download_and_check_blur
import model_registry as _reg


def register_routes(app):

    @app.route("/analyze", methods=["POST"])
    def analyze():

        data = request.get_json()

        user_id = data.get("userId")

        top_url   = data.get("topImageUrl")
        front_url = data.get("frontImageUrl")
        back_url  = data.get("backImageUrl")

        flashcard_answers = data.get("flashcardAnswers", {})

        previous_score    = data.get("previousHairScore")
        previous_dandruff = data.get("previousDandruffSeverity")

        if not top_url:
            return jsonify({"error": "topImageUrl required"}), 400

        try:

            top_image = download_and_check_blur(top_url, "top")

            front_image = None
            if front_url:
                front_image = download_and_check_blur(front_url, "front")

            back_image = None
            if back_url:
                back_image = download_and_check_blur(back_url, "back")

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
                "userId": user_id,
                **result
            })

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(tb)                          # prints to Flask terminal
            return jsonify({
                "success": False,
                "error": str(e),
                "traceback": tb                # also visible in app response
            }), 500

    # ─────────────────────────────────────────
    # ADAPTIVE ROUTINE
    # ─────────────────────────────────────────
    @app.route("/adaptive-routine", methods=["POST"])
    def adaptive_routine():
        try:
            data = request.get_json(force=True)

            routine = _reg.get("adaptive_routine_engine").generate(
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
            traceback.print_exc()   # ← add this line
            jsonify({
                "success": False,
                "error": str(e)
            }), 500
