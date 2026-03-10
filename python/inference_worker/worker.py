import logging
from services import run_analysis
from shared.weights_loader import download_weights

logger = logging.getLogger(__name__)

# download weights once at import time
try:
    logger.info("⬇ Downloading model weights")
    download_weights()
    logger.info("✅ Weights ready")
except Exception as e:
    logger.error(f"Weight download failed: {e}")


def run_worker(data):
    """
    Worker entry for analysis
    """

    try:

        result = run_analysis(
            data["topImage"],
            data.get("frontImage"),
            data.get("backImage"),
            data.get("flashcardAnswers", {}),
            data.get("userId"),
            data.get("previousHairScore"),
            data.get("previousDandruffSeverity")
        )

        return result

    except Exception as e:

        logger.exception("Worker failed")

        return {
            "success": False,
            "error": str(e)
        }