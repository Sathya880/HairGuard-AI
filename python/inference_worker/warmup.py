import logging
import threading

from inference_worker.model_registry import get

logger = logging.getLogger(__name__)


def warm_models():
    """
    Warm critical models in parallel so first API request is fast.
    """

    models = [
        "hairloss_model",
        "dandruff_model",
        "hair_density_analyzer"
    ]

    def load(name):
        try:
            logger.info(f"🔥 warming {name}")
            get(name)
            logger.info(f"✅ {name} ready")
        except Exception as e:
            logger.error(f"❌ {name} failed: {e}")

    threads = []

    for model in models:
        t = threading.Thread(target=load, args=(model,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    logger.info("🚀 all models warmed")