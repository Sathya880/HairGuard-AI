"""
Hair AI Backend — Unified Entry Point for Render
=================================================
Single-process architecture to fit within 512 MB RAM.

Architecture (matches diagram):
  Mobile App (Flutter)
       ↓
  API Gateway  ←→  Assistant Engine Service
       ↓
  AI Inference Service
       ↓
  Shared Services Layer
  ↙            ↘
AWS S3        Postgres
"""

import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS

from api_server.routes import register_routes
from assistant_service.assistant_routes import register_assistant_routes

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("hair_ai")


# ─────────────────────────────────────────────
# APP FACTORY
# ─────────────────────────────────────────────

def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    logger.info("🚀 Starting Hair AI Backend (Unified)")

    # Register all route groups
    register_routes(app)
    register_assistant_routes(app)

    @app.route("/health")
    def health():
        from inference_worker.model_registry import status as model_status
        return jsonify({
            "status": "ok",
            "service": "hair-ai-backend",
            "models": model_status()
        })

    @app.route("/")
    def root():
        return jsonify({"message": "Hair AI Backend — running ✅"})

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🌐 Listening on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)