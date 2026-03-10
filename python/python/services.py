from concurrent.futures import ThreadPoolExecutor

from models.hair_health import compute_hair_health_score
from utils import pick_worst
from config import upload_overlay_async, image_to_jpeg_bytes

# GLOBAL executor for model inference
MODEL_EXECUTOR = ThreadPoolExecutor(max_workers=3)

# GLOBAL executor for AI engines
ENGINE_EXECUTOR = ThreadPoolExecutor(max_workers=5)

import model_registry as _reg


def normalize_view(view):
    if not isinstance(view, dict):
        return {"severity": "unknown", "damage": None, "weight": None}
    return {
        "severity": view.get("severity", "unknown"),
        "damage":   view.get("damage"),
        "weight":   view.get("weight")
    }

def run_models(top_image, front_image, back_image):

    process_hairloss      = _reg.get("hairloss_model")
    process_dandruff      = _reg.get("dandruff_model")
    hair_density_analyzer = _reg.get("hair_density_analyzer")

    executor = MODEL_EXECUTOR

    f_hairloss_top   = executor.submit(process_hairloss, top_image)
    f_dandruff_top   = executor.submit(process_dandruff, top_image)

    f_hairloss_front = executor.submit(process_hairloss, front_image) if front_image else None
    f_density_back   = executor.submit(hair_density_analyzer.analyze, back_image) if back_image else None

    hairloss_top   = f_hairloss_top.result()  or {}
    dandruff_top   = f_dandruff_top.result()  or {}
    hairloss_front = f_hairloss_front.result() if f_hairloss_front else {}
    hairloss_back  = {}

    if f_density_back:
        density       = f_density_back.result()
        density_class = density.get("prediction")
        back_severity = {
            "normal": "normal",
            "moderate": "moderate",
            "severe": "severe"
        }.get(density_class, "unknown")

        hairloss_back = {
            "severity": back_severity,
            "densityClass": density_class
        }

    return hairloss_top, dandruff_top, hairloss_front, hairloss_back


def upload_overlays(hairloss_top, dandruff_top, user_id):

    f_hair = None
    f_dandruff = None

    try:
        overlay = hairloss_top.get("overlay_image")
        if overlay is not None:
            f_hair = upload_overlay_async(
                image_to_jpeg_bytes(overlay),
                user_id
            )
    except Exception as e:
        print("Hair overlay upload error:", e)

    try:
        overlay = dandruff_top.get("overlay_image")
        if overlay is not None:
            f_dandruff = upload_overlay_async(
                image_to_jpeg_bytes(overlay),
                user_id
            )
    except Exception as e:
        print("Dandruff overlay upload error:", e)

    hair_url = None
    dandruff_url = None

    if f_hair:
        hair_url = f_hair.result()

    if f_dandruff:
        dandruff_url = f_dandruff.result()

    return hair_url, dandruff_url


def run_analysis(
        top_image, front_image, back_image,
        flashcard_answers,
        user_id,
        previous_score=None, previous_dandruff=None):

    # ─────────────────────────────────────
    # Run core AI models
    # ─────────────────────────────────────
    hairloss_top, dandruff_top, hairloss_front, hairloss_back = run_models(
        top_image, front_image, back_image
    )

    hairloss_overlay_url, dandruff_overlay_url = upload_overlays(
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

    lifestyle_result = _reg.get("lifestyle_analyzer").analyze(
        flashcard_answers
    ) or {}

    score, label, breakdown = compute_hair_health_score(
        hairloss_views={
            "top":   hairloss_top.get("severity"),
            "front": hairloss_front.get("severity"),
            "back":  hairloss_back.get("severity"),
        },
        dandruff_severity=dandruff_severity,
        flashcard_answers=flashcard_answers
    )

    hairloss_breakdown = breakdown.get("hairloss", {})
    combined_damage = hairloss_breakdown.get("combined_damage")
    overall_severity = hairloss_breakdown.get("overall_severity") or hairloss_severity
    view_details = hairloss_breakdown.get("views", {})

    hairloss = {
        "overallSeverity": overall_severity,
        "combinedDamage": combined_damage,
        "overlayImageUrl": hairloss_overlay_url,
        "views": {
            "top": normalize_view(view_details.get("top")),
            "front": normalize_view(view_details.get("front")),
            "back": normalize_view(view_details.get("back"))
        }
    }

    dandruff = {
        "severity": dandruff_severity,
        "overlayImageUrl": dandruff_overlay_url,
        "summary": None
    }

    health = {
        "score": score,
        "label": label,
        "breakdown": breakdown
    }

    # ─────────────────────────────────────
    # Root cause engine
    # ─────────────────────────────────────
    root_result = _reg.get("bayesian_root_cause").infer(
        hairloss=hairloss,
        dandruff=dandruff,
        flashcard_answers=flashcard_answers,
        lifestyle_result=lifestyle_result
    ) or {}

    primary_key = None
    causes = root_result.get("causes")

    if isinstance(causes, list) and causes:
        primary_key = causes[0].get("key")

    # ─────────────────────────────────────
    # Run independent engines in parallel
    # ─────────────────────────────────────
    f_suggestions = ENGINE_EXECUTOR.submit(
        _reg.get("suggestions_engine").generate,
        root_cause=primary_key,
        hair_severity=hairloss_severity or "none",
        dandruff_severity=dandruff_severity or "none",
        lifestyle_score=lifestyle_result.get("score", 50)
    )

    f_remedies = ENGINE_EXECUTOR.submit(
        _reg.get("remedies_engine").generate,
        hairloss_severity,
        dandruff_severity,
        primary_key,
        flashcard_answers
    )

    f_future = ENGINE_EXECUTOR.submit(
        _reg.get("future_risk_model").predict,
        hair_score=score,
        hairloss_severity=hairloss_severity or "unknown",
        dandruff_severity=dandruff_severity or "unknown",
        lifestyle_score=lifestyle_result.get("score", 50),
        root_cause=primary_key
    )

    f_adaptive = ENGINE_EXECUTOR.submit(
        _reg.get("adaptive_routine_engine").generate,
        hairloss_severity=hairloss_severity,
        dandruff_severity=dandruff_severity,
        root_cause=root_result.get("primary_cause"),
        lifestyle_score=lifestyle_result.get("score", 0),
        humidity="normal",
        pollution_level="moderate"
    )

    suggestions = f_suggestions.result() or {}
    tips_and_remedies = f_remedies.result() or {}
    future_risk = f_future.result() or {}
    adaptive_routine = f_adaptive.result()

    # ─────────────────────────────────────
    # Progress tracking
    # ─────────────────────────────────────
    progress_result = None

    if previous_score is not None and previous_dandruff is not None:

        raw_progress = _reg.get("progress_tracker").track_progress(
            previous_hair_score=previous_score,
            current_hair_score=score,
            previous_dandruff_severity=previous_dandruff,
            current_dandruff_severity=dandruff_severity
        )

        if raw_progress:
            progress_result = {
                "previousScore": raw_progress.get("previous_hair_score"),
                "currentScore": raw_progress.get("current_hair_score"),
                "scoreChange": raw_progress.get("score_change"),
                "hairTrend": raw_progress.get("hair_trend"),
                "dandruffTrend": raw_progress.get("dandruff_trend"),
            }

    # ─────────────────────────────────────
    # Final response
    # ─────────────────────────────────────
    return {
        "hairloss": hairloss,
        "dandruff": dandruff,
        "health": health,
        "lifestyle": lifestyle_result,

        "rootCause": {
            "primary": root_result.get("primary_cause"),
            "secondary": root_result.get("secondary_cause"),
            "details": root_result.get("impact_breakdown", {}),
            "causes": root_result.get("causes", []),
            "confidence": root_result.get("confidence_percent"),
            "data_strength": root_result.get("data_strength"),
            "network_summary": root_result.get("network_summary"),
        },

        "suggestions": suggestions,
        "tipsAndRemedies": tips_and_remedies,
        "futureRisk": future_risk,
        "adaptiveRoutine": adaptive_routine,
        "progress": progress_result,

        "assistantContext": {
            "currentReport": {
                "hairScore": score,
                "lifestyleScore": lifestyle_result.get("score", 0),
                "hairSeverity": hairloss_severity,
                "dandruffSeverity": dandruff_severity,
                "rootCause": root_result.get("primary_cause"),
            }
        }
    }
