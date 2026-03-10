"""
Hair AI Backend — Production Entry Point
Compatible with Flask 3.x
"""

import logging
import os
import threading

from flask import Flask, jsonify
from flask_cors import CORS

from api_server.routes import register_routes
from assistant_service.assistant_routes import register_assistant_routes


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("hair_ai")


def ensure_weights():
    """Download model weights if missing"""

    try:
        from shared.weights_loader import download_weights

        logger.info("⬇ checking model weights")
        download_weights()

        logger.info("✅ weights ready")

    except Exception as e:
        logger.error(f"weight download failed: {e}")


def start_background_tasks():
    """Run startup tasks safely"""

    logger.info("⚙ starting background tasks")

    # download weights
    threading.Thread(
        target=ensure_weights,
        daemon=True
    ).start()

    # warm models
    from inference_worker.warmup import warm_models

    threading.Thread(
        target=warm_models,
        daemon=True
    ).start()


def create_app():

    app = Flask(__name__)
    CORS(app)

    logger.info("🚀 Hair AI backend starting")

    register_routes(app)
    register_assistant_routes(app)

    @app.route("/")
    def root():
        return jsonify({
            "service": "hair-ai-backend",
            "status": "running"
        })

    @app.route("/health")
    def health():

        try:
            from inference_worker.model_registry import status

            return jsonify({
                "status": "ok",
                "models": status()
            })

        except Exception as e:
            return jsonify({
                "status": "error",
                "error": str(e)
            }), 500

    return app


app = create_app()

# start background initialization
start_background_tasks()


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    logger.info(f"🌐 running on port {port}")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )