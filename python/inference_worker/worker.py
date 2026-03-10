import logging

from inference_worker.services import run_analysis
from shared.weights_loader import download_weights

logger = logging.getLogger(__name__)


def initialize_worker():

    try:
        logger.info("⬇ downloading weights")
        download_weights()
        logger.info("✅ weights ready")

    except Exception as e:
        logger.exception("weight download failed")


def run_worker(data):

    try:

        result = run_analysis(
            top_image=data["topImage"],
            front_image=data.get("frontImage"),
            back_image=data.get("backImage"),
            flashcard_answers=data.get("flashcardAnswers", {}),
            user_id=data.get("userId"),
            previous_score=data.get("previousHairScore"),
            previous_dandruff=data.get("previousDandruffSeverity"),
        )

        return result

    except Exception as e:

        logger.exception("worker failed")

        return {
            "success": False,
            "error": str(e)
        }