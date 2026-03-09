import logging
import os
import threading
from flask import Flask, jsonify
from flask_cors import CORS

from weights_loader import download_weights
from routes import register_routes
from assistant_routes import register_assistant_routes

import model_registry


models_ready = False
models_loading_started = False


def load_models_async():
    """Load AI models in background."""
    global models_ready

    logger = logging.getLogger("model_loader")

    try:
        logger.info("⬇ Checking / downloading model weights...")
        download_weights()

        logger.info("🔥 Loading AI models...")
        model_registry.warm_up_all()

        models_ready = True
        logger.info("✅ All AI models ready")

    except Exception:
        logger.exception("❌ Model loading failed")


def start_background_model_loading():
    """Ensure model loading starts only once."""
    global models_loading_started

    if models_loading_started:
        return

    models_loading_started = True

    thread = threading.Thread(
        target=load_models_async,
        daemon=True
    )
    thread.start()


def create_app():
    app = Flask(__name__)
    CORS(app)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    logger = logging.getLogger("app")
    logger.info("🚀 Starting Hair AI Server")

    register_routes(app)
    register_assistant_routes(app)

    @app.before_request
    def ensure_models_loading():
        # starts model loading on first request
        start_background_model_loading()

    @app.route("/health")
    def health():
        try:
            model_status = model_registry.status()
        except Exception:
            model_status = "loading"

        return jsonify({
            "status": "ok",
            "models": model_status,
            "ready": models_ready
        })

    return app


app = create_app()


# Local development run
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    logging.getLogger("app").info(
        f"🌐 Server running on http://0.0.0.0:{port}"
    )

    start_background_model_loading()

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )