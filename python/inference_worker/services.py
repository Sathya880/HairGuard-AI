"""
Inference Services
==================
Core analysis pipeline. Orchestrates:
  1. Parallel model inference (hairloss, dandruff, density)
  2. Overlay upload to S3
  3. Lifestyle analysis
  4. Hair health scoring
  5. Root cause (Bayesian)
  6. Parallel domain engines (suggestions, remedies, risk, routine)
  7. Optional progress tracking
"""

import logging
from concurrent.futures import ThreadPoolExecutor

import inference_worker.model_registry as _reg
from models.hair_health import compute_hair_health_score
from shared.utils import pick_worst
from shared.config import upload_overlay_async, image_to_jpeg_bytes

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Thread pools — kept small to respect 512 MB
# ─────────────────────────────────────────────

MODEL_EXECUTOR  = ThreadPoolExecutor(max_workers=2, thread_name_prefix="model")
ENGINE_EXECUTOR = ThreadPoolExecutor(max_workers=3, thread_name_prefix="engine")


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _normalize_view(view: dict) -> dict:
    if not isinstance(view, dict):
        return {"severity": "unknown", "damage": None, "weight": None}
    return {
        "severity": view.get("severity", "unknown"),
        "damage":   view.get("damage"),
        "weight":   view.get("weight"),
    }


# ─────────────────────────────────────────────
# Run AI models in parallel
# ─────────────────────────────────────────────

def _run_models(top_image, front_image, back_image):
    hairloss_fn  = _reg.get("hairloss_model")
    dandruff_fn  = _reg.get("dandruff_model")
    density_ana  = _reg.get("hair_density_analyzer")

    f_hl_top    = MODEL_EXECUTOR.submit(hairloss_fn, top_image)
    f_dd_top    = MODEL_EXECUTOR.submit(dandruff_fn, top_image)
    f_hl_front  = MODEL_EXECUTOR.submit(hairloss_fn, front_image) if front_image else None
    f_den_back  = MODEL_EXECUTOR.submit(density_ana.analyze, back_image)  if back_image  else None

    hairloss_top   = f_hl_top.result()  or {}
    dandruff_top   = f_dd_top.result()  or {}
    hairloss_front = f_hl_front.result() if f_hl_front else {}

    hairloss_back = {}
    if f_den_back:
        density       = f_den_back.result() or {}
        density_class = density.get("prediction")
        hairloss_back = {
            "severity":     {"normal": "normal", "moderate": "moderate",
                             "severe": "severe"}.get(density_class, "unknown"),
            "densityClass": density_class,
        }

    return hairloss_top, dandruff_top, hairloss_front, hairloss_back


# ─────────────────────────────────────────────
# Upload overlays to S3 (async)
# ─────────────────────────────────────────────

def _upload_overlays(hairloss_top, dandruff_top, user_id):
    f_hair     = None
    f_dandruff = None

    try:
        overlay = hairloss_top.get("overlay_image")
        if overlay is not None:
            f_hair = upload_overlay_async(image_to_jpeg_bytes(overlay), user_id)
    except Exception:
        logger.exception("Hair overlay upload failed")

    try:
        overlay = dandruff_top.get("overlay_image")
        if overlay is not None:
            f_dandruff = upload_overlay_async(image_to_jpeg_bytes(overlay), user_id)
    except Exception:
        logger.exception("Dandruff overlay upload failed")

    hair_url     = f_hair.result()     if f_hair     else None
    dandruff_url = f_dandruff.result() if f_dandruff else None
    return hair_url, dandruff_url


# ─────────────────────────────────────────────
# Main analysis pipeline
# ─────────────────────────────────────────────

def run_analysis(
    top_image,
    front_image,
    back_image,
    flashcard_answers: dict,
    user_id: str,
    previous_score=None,
    previous_dandruff=None,
) -> dict:

    # 1 — AI inference
    hairloss_top, dandruff_top, hairloss_front, hairloss_back = _run_models(
        top_image, front_image, back_image
    )

    hair_overlay_url, dandruff_overlay_url = _upload_overlays(
        hairloss_top, dandruff_top, user_id
    )

    hairloss_severity = pick_worst([
        hairloss_top.get("severity"),
        hairloss_front.get("severity"),
        hairloss_back.get("severity"),
    ])
    dandruff_severity = dandruff_top.get("severity", "unknown")

    # 2 — Lifestyle
    lifestyle_result = _reg.get("lifestyle_analyzer").analyze(flashcard_answers) or {}

    # 3 — Hair health score
    score, label, breakdown = compute_hair_health_score(
        hairloss_views={
            "top":   hairloss_top.get("severity"),
            "front": hairloss_front.get("severity"),
            "back":  hairloss_back.get("severity"),
        },
        dandruff_severity=dandruff_severity,
        flashcard_answers=flashcard_answers,
    )

    hl_breakdown     = breakdown.get("hairloss", {})
    combined_damage  = hl_breakdown.get("combined_damage")
    overall_severity = hl_breakdown.get("overall_severity") or hairloss_severity
    view_details     = hl_breakdown.get("views", {})

    hairloss = {
        "overallSeverity": overall_severity,
        "combinedDamage":  combined_damage,
        "overlayImageUrl": hair_overlay_url,
        "views": {
            "top":   _normalize_view(view_details.get("top")),
            "front": _normalize_view(view_details.get("front")),
            "back":  _normalize_view(view_details.get("back")),
        },
    }

    dandruff = {
        "severity":        dandruff_severity,
        "overlayImageUrl": dandruff_overlay_url,
        "summary":         None,
    }

    health = {"score": score, "label": label, "breakdown": breakdown}

    # 4 — Root cause
    root_result = _reg.get("bayesian_root_cause").infer(
        hairloss=hairloss,
        dandruff=dandruff,
        flashcard_answers=flashcard_answers,
        lifestyle_result=lifestyle_result,
    ) or {}

    primary_key = None
    causes = root_result.get("causes")
    if isinstance(causes, list) and causes:
        primary_key = causes[0].get("key")

    # 5 — Parallel domain engines
    f_sugg = ENGINE_EXECUTOR.submit(
        _reg.get("suggestions_engine").generate,
        root_cause=primary_key,
        hair_severity=hairloss_severity or "none",
        dandruff_severity=dandruff_severity or "none",
        lifestyle_score=lifestyle_result.get("score", 50),
    )
    f_rem = ENGINE_EXECUTOR.submit(
        _reg.get("remedies_engine").generate,
        hairloss_severity, dandruff_severity, primary_key, flashcard_answers,
    )
    f_fut = ENGINE_EXECUTOR.submit(
        _reg.get("future_risk_model").predict,
        hair_score=score,
        hairloss_severity=hairloss_severity or "unknown",
        dandruff_severity=dandruff_severity or "unknown",
        lifestyle_score=lifestyle_result.get("score", 50),
        root_cause=primary_key,
    )
    f_ada = ENGINE_EXECUTOR.submit(
        _reg.get("adaptive_routine_engine").generate,
        hairloss_severity=hairloss_severity,
        dandruff_severity=dandruff_severity,
        root_cause=root_result.get("primary_cause"),
        lifestyle_score=lifestyle_result.get("score", 0),
        humidity="normal",
        pollution_level="moderate",
    )

    suggestions      = f_sugg.result() or {}
    remedies         = f_rem.result()  or {}
    future_risk      = f_fut.result()  or {}
    adaptive_routine = f_ada.result()

    # 6 — Progress tracking
    progress_result = None
    if previous_score is not None and previous_dandruff is not None:
        raw = _reg.get("progress_tracker").track_progress(
            previous_hair_score=previous_score,
            current_hair_score=score,
            previous_dandruff_severity=previous_dandruff,
            current_dandruff_severity=dandruff_severity,
        )
        if raw:
            progress_result = {
                "previousScore": raw.get("previous_hair_score"),
                "currentScore":  raw.get("current_hair_score"),
                "scoreChange":   raw.get("score_change"),
                "hairTrend":     raw.get("hair_trend"),
                "dandruffTrend": raw.get("dandruff_trend"),
            }

    # 7 — Assemble response
    return {
        "hairloss":  hairloss,
        "dandruff":  dandruff,
        "health":    health,
        "lifestyle": lifestyle_result,

        "rootCause": {
            "primary":         root_result.get("primary_cause"),
            "secondary":       root_result.get("secondary_cause"),
            "details":         root_result.get("impact_breakdown", {}),
            "causes":          root_result.get("causes", []),
            "confidence":      root_result.get("confidence_percent"),
            "data_strength":   root_result.get("data_strength"),
            "network_summary": root_result.get("network_summary"),
        },

        "suggestions":      suggestions,
        "tipsAndRemedies":  remedies,
        "futureRisk":       future_risk,
        "adaptiveRoutine":  adaptive_routine,
        "progress":         progress_result,

        "assistantContext": {
            "currentReport": {
                "hairScore":         score,
                "lifestyleScore":    lifestyle_result.get("score", 0),
                "hairSeverity":      hairloss_severity,
                "dandruffSeverity":  dandruff_severity,
                "rootCause":         root_result.get("primary_cause"),
            }
        },
    }