import logging
from concurrent.futures import ThreadPoolExecutor

import inference_worker.model_registry as _reg
from inference_worker.concurrency import inference_semaphore

from models.hair_health import compute_hair_health_score
from shared.utils import pick_worst
from shared.config import upload_overlay_async, image_to_jpeg_bytes

logger = logging.getLogger(__name__)

MODEL_EXECUTOR = ThreadPoolExecutor(max_workers=2)
ENGINE_EXECUTOR = ThreadPoolExecutor(max_workers=2)

_hairloss_model = None
_dandruff_model = None
_density_model = None


def _ensure_models():
    global _hairloss_model, _dandruff_model, _density_model

    if _hairloss_model is None:
        _hairloss_model = _reg.get("hairloss_model")

    if _dandruff_model is None:
        _dandruff_model = _reg.get("dandruff_model")

    if _density_model is None:
        _density_model = _reg.get("hair_density_analyzer")


def _run_models(top_image, front_image, back_image):

    _ensure_models()

    futures = {}

    futures["hair_top"] = MODEL_EXECUTOR.submit(_hairloss_model, top_image)
    futures["dand_top"] = MODEL_EXECUTOR.submit(_dandruff_model, top_image)

    if front_image:
        futures["hair_front"] = MODEL_EXECUTOR.submit(_hairloss_model, front_image)

    if back_image:
        futures["density_back"] = MODEL_EXECUTOR.submit(_density_model.analyze, back_image)

    results = {}

    for k, f in futures.items():
        try:
            results[k] = f.result()
        except Exception:
            logger.exception(f"model failed: {k}")
            results[k] = {}

    hairloss_back = {}

    if "density_back" in results:

        density_class = results["density_back"].get("prediction")

        hairloss_back = {
            "severity": {
                "normal": "normal",
                "moderate": "moderate",
                "severe": "severe"
            }.get(density_class, "unknown"),
            "densityClass": density_class
        }

    return (
        results.get("hair_top", {}),
        results.get("dand_top", {}),
        results.get("hair_front", {}),
        hairloss_back
    )


def run_analysis(
    top_image,
    front_image,
    back_image,
    flashcard_answers,
    user_id,
    previous_score=None,
    previous_dandruff=None,
):

    with inference_semaphore:

        hairloss_top, dandruff_top, hairloss_front, hairloss_back = _run_models(
            top_image,
            front_image,
            back_image
        )

    hair_upload, dand_upload = None, None

    try:

        overlay = hairloss_top.get("overlay_image")

        if overlay is not None:

            hair_upload = upload_overlay_async(
                image_to_jpeg_bytes(overlay),
                user_id
            )

    except Exception:
        logger.exception("overlay upload failed")

    hairloss_severity = pick_worst([
        hairloss_top.get("severity"),
        hairloss_front.get("severity"),
        hairloss_back.get("severity"),
    ])

    dandruff_severity = dandruff_top.get("severity", "unknown")

    lifestyle = _reg.get("lifestyle_analyzer").analyze(
        flashcard_answers
    ) or {}

    score, label, breakdown = compute_hair_health_score(
        hairloss_views={
            "top": hairloss_top.get("severity"),
            "front": hairloss_front.get("severity"),
            "back": hairloss_back.get("severity"),
        },
        dandruff_severity=dandruff_severity,
        flashcard_answers=flashcard_answers,
    )

    return {
        "hairloss": {"overallSeverity": hairloss_severity},
        "dandruff": {"severity": dandruff_severity},
        "health": {
            "score": score,
            "label": label,
            "breakdown": breakdown
        },
        "lifestyle": lifestyle
    }