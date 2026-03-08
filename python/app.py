import logging
import os
from flask import Flask
from flask_cors import CORS

from weights_loader import download_weights
from routes import register_routes
from assistant_routes import register_assistant_routes


def create_app():

    app = Flask(__name__)
    CORS(app)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting Hair AI Server")

    # Download model weights from S3
    download_weights()

    # Load models into memory
    import model_registry
    model_registry.warm_up_all()

    register_routes(app)
    register_assistant_routes(app)

    @app.route("/health")
    def health():
        from flask import jsonify
        return jsonify({
            "status": "ok",
            "models": model_registry.status()
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