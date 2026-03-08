import logging
import os
import threading
from flask import Flask, jsonify
from flask_cors import CORS

from weights_loader import download_weights
from routes import register_routes
from assistant_routes import register_assistant_routes

models_ready = False


def load_models_async():
    global models_ready
    logger = logging.getLogger(__name__)

    try:
        logger.info("⬇ Downloading model weights from S3...")
        download_weights()

        logger.info("🔥 Loading AI models into memory...")
        import model_registry
        model_registry.warm_up_all()

        models_ready = True
        logger.info("✅ Models loaded successfully")

    except Exception as e:
        logger.error(f"❌ Model loading failed: {e}")


def create_app():
    app = Flask(__name__)
    CORS(app)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting Hair AI Server")

    # Load models in background
    threading.Thread(
        target=load_models_async,
        daemon=True,
        name="model-loader"
    ).start()

    register_routes(app)
    register_assistant_routes(app)

    @app.route("/health")
    def health():
        try:
            import model_registry
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))

    logging.getLogger(__name__).info(
        f"🌐 Server running on http://0.0.0.0:{port}"
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )