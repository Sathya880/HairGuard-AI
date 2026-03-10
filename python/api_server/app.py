import logging
import os
import threading

from flask import Flask
from flask_cors import CORS

from api_server.routes import register_routes
from assistant_service.assistant_routes import register_assistant_routes
from shared.weights_loader import download_weights

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("hair_ai")


def init_models():

    try:

        logger.info("⬇ checking model weights")

        download_weights()

        logger.info("🔥 warming models")

        from inference_worker.warmup import warm_models

        warm_models()

        logger.info("✅ initialization complete")

    except Exception:
        logger.exception("Initialization failed")


def create_app():

    app = Flask(__name__)
    CORS(app)

    register_routes(app)
    register_assistant_routes(app)

    @app.route("/")
    def root():
        return {"service": "hair-ai-backend"}

    @app.route("/health")
    def health():

        from inference_worker.model_registry import status

        return {"status": "ok", "models": status()}

    return app


app = create_app()

threading.Thread(target=init_models, daemon=True).start()


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)