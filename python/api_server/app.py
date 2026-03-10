"""
Hair AI Backend — Unified Entry Point
Optimized for Railway / Render (512MB containers)

Architecture
------------
Mobile App (Flutter)
      ↓
API Gateway (Flask)
      ↓
Inference Worker
      ↓
Domain Engines
"""

import logging
import os
import threading

from flask import Flask, jsonify
from flask_cors import CORS

from api_server.routes import register_routes
from assistant_service.assistant_routes import register_assistant_routes


# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("hair_ai")


# ─────────────────────────────────────────────
# BACKGROUND MODEL WARMUP
# ─────────────────────────────────────────────

def warm_models():
    """
    Warm critical models in background so first request is fast.
    Safe for low-memory containers.
    """

    try:

        from inference_worker.model_registry import get

        logger.info("🔥 warming critical models")

        # warm minimal models only
        get("hairloss_model")
        get("dandruff_model")
        get("hair_density_analyzer")

        logger.info("✅ core models warmed")

    except Exception as e:
        logger.error(f"model warmup failed: {e}")


# ─────────────────────────────────────────────
# BACKGROUND WEIGHT DOWNLOAD
# ─────────────────────────────────────────────

def ensure_weights():

    try:

        from shared.weights_loader import download_weights

        logger.info("⬇ ensuring model weights exist")

        download_weights()

        logger.info("✅ weights ready")

    except Exception as e:
        logger.error(f"weight download failed: {e}")


# ─────────────────────────────────────────────
# APP FACTORY
# ─────────────────────────────────────────────

def create_app():

    app = Flask(__name__)
    CORS(app)

    logger.info("🚀 Starting Hair AI Backend")

    # register API groups
    register_routes(app)
    register_assistant_routes(app)

    # ─────────────────────────────
    # ROOT
    # ─────────────────────────────

    @app.route("/")
    def root():

        return jsonify(
            {
                "service": "hair-ai-backend",
                "status": "running",
            }
        )

    # ─────────────────────────────
    # HEALTH
    # ─────────────────────────────

    @app.route("/health")
    def health():

        try:

            from inference_worker.model_registry import status

            return jsonify(
                {
                    "status": "ok",
                    "models": status(),
                }
            )

        except Exception as e:

            return jsonify(
                {
                    "status": "error",
                    "error": str(e),
                }
            ), 500

    # ─────────────────────────────
    # STARTUP HOOK
    # ─────────────────────────────

    @app.before_first_request
    def startup_tasks():

        logger.info("⚙ running background initialization")

        # download weights
        threading.Thread(
            target=ensure_weights,
            daemon=True,
        ).start()

        # warm models
        threading.Thread(
            target=warm_models,
            daemon=True,
        ).start()

    return app


# ─────────────────────────────────────────────
# CREATE APP INSTANCE
# ─────────────────────────────────────────────

app = create_app()


# ─────────────────────────────────────────────
# LOCAL DEVELOPMENT
# ─────────────────────────────────────────────

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    logger.info(f"🌐 running on port {port}")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )