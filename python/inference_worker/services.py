import logging
from concurrent.futures import ThreadPoolExecutor

import inference_worker.model_registry as _reg
from models.hair_health import compute_hair_health_score
from shared.utils import pick_worst
from shared.config import upload_overlay_async, image_to_jpeg_bytes

logger = logging.getLogger(__name__)

# Thread pools (safe for Render free tier)
MODEL_EXECUTOR = ThreadPoolExecutor(max_workers=2)
ENGINE_EXECUTOR = ThreadPoolExecutor(max_workers=2)

# Cached models (avoid repeated registry lookup)
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

    for key, future in futures.items():
        try:
            results[key] = future.result()
        except Exception:
            logger.exception(f"Model failed: {key}")
            results[key] = {}

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


def _upload_overlays(hairloss_top, dandruff_top, user_id):

    hair_future = None
    dand_future = None

    try:
        overlay = hairloss_top.get("overlay_image")

        if overlay is not None:
            hair_future = upload_overlay_async(
                image_to_jpeg_bytes(overlay),
                user_id
            )
    except Exception:
        logger.exception("Hair overlay upload failed")

    try:
        overlay = dandruff_top.get("overlay_image")

        if overlay is not None:
            dand_future = upload_overlay_async(
                image_to_jpeg_bytes(overlay),
                user_id
            )
    except Exception:
        logger.exception("Dandruff overlay upload failed")

    return hair_future, dand_future


def run_analysis(
    top_image,
    front_image,
    back_image,
    flashcard_answers,
    user_id,
    previous_score=None,
    previous_dandruff=None,
):

    # 1. Run AI models
    hairloss_top, dandruff_top, hairloss_front, hairloss_back = _run_models(
        top_image,
        front_image,
        back_image
    )

    # 2. Upload overlays asynchronously
    hair_upload, dand_upload = _upload_overlays(
        hairloss_top,
        dandruff_top,
        user_id
    )

    hairloss_severity = pick_worst([
        hairloss_top.get("severity"),
        hairloss_front.get("severity"),
        hairloss_back.get("severity"),
    ])

    dandruff_severity = dandruff_top.get("severity", "unknown")

    # 3. Lifestyle analysis
    lifestyle = _reg.get("lifestyle_analyzer").analyze(
        flashcard_answers
    ) or {}

    # 4. Hair health score
    score, label, breakdown = compute_hair_health_score(
        hairloss_views={
            "top": hairloss_top.get("severity"),
            "front": hairloss_front.get("severity"),
            "back": hairloss_back.get("severity"),
        },
        dandruff_severity=dandruff_severity,
        flashcard_answers=flashcard_answers,
    )

    # 5. Root cause
    root = _reg.get("bayesian_root_cause").infer(
        hairloss={"severity": hairloss_severity},
        dandruff={"severity": dandruff_severity},
        flashcard_answers=flashcard_answers,
        lifestyle_result=lifestyle,
    ) or {}

    primary_key = None
    causes = root.get("causes")

    if isinstance(causes, list) and causes:
        primary_key = causes[0].get("key")

    # 6. Parallel engines
    f_suggestions = ENGINE_EXECUTOR.submit(
        _reg.get("suggestions_engine").generate,
        root_cause=primary_key,
        hair_severity=hairloss_severity,
        dandruff_severity=dandruff_severity,
        lifestyle_score=lifestyle.get("score", 50),
    )

    f_remedies = ENGINE_EXECUTOR.submit(
        _reg.get("remedies_engine").generate,
        hairloss_severity,
        dandruff_severity,
        primary_key,
        flashcard_answers,
    )

    suggestions = f_suggestions.result() or {}
    remedies = f_remedies.result() or {}

    hair_overlay_url = hair_upload.result() if hair_upload else None
    dandruff_overlay_url = dand_upload.result() if dand_upload else None

    # 7. Progress tracking (this fixes your warning)
    progress = None

    if previous_score is not None and previous_dandruff is not None:

        raw = _reg.get("progress_tracker").track_progress(
            previous_hair_score=previous_score,
            current_hair_score=score,
            previous_dandruff_severity=previous_dandruff,
            current_dandruff_severity=dandruff_severity,
        )

        if raw:
            progress = {
                "previousScore": raw.get("previous_hair_score"),
                "currentScore": raw.get("current_hair_score"),
                "scoreChange": raw.get("score_change"),
                "hairTrend": raw.get("hair_trend"),
                "dandruffTrend": raw.get("dandruff_trend"),
            }

    # 8. Final response
    return {
        "hairloss": {
            "overallSeverity": hairloss_severity,
            "overlayImageUrl": hair_overlay_url,
        },
        "dandruff": {
            "severity": dandruff_severity,
            "overlayImageUrl": dandruff_overlay_url,
        },
        "health": {
            "score": score,
            "label": label,
            "breakdown": breakdown
        },
        "lifestyle": lifestyle,
        "rootCause": root,
        "suggestions": suggestions,
        "tipsAndRemedies": remedies,
        "progress": progress
    }