from flask import Flask, request, jsonify
import logging

from services import run_analysis
from shared.weights_loader import download_weights

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)


@app.before_first_request
def init_models():

    logging.info("⬇ Downloading weights")

    download_weights()


@app.route("/run-analysis", methods=["POST"])
def run():

    try:

        data = request.json

        result = run_analysis(
            data["topImage"],
            data.get("frontImage"),
            data.get("backImage"),
            data.get("flashcardAnswers", {}),
            data.get("userId"),
            data.get("previousHairScore"),
            data.get("previousDandruffSeverity")
        )

        return jsonify(result)

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500