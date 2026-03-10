from typing import Dict, List, Tuple
import time
import requests

# =====================================================
# 🔗 FLASHCARD MAPPING SOURCE (NODE → MONGO)
# =====================================================

FLASHCARD_MAPPING_URL = "http://127.0.0.1:3000/ai/flashcard-mapping"
CACHE_TTL_SECONDS = 300  # 5 minutes

_mapping_cache = {
    "mapping": {},
    "versions": {},
    "last_fetch": 0.0,
}

# =====================================================
# INTERNAL: LOAD + CACHE FLASHCARD METADATA
# =====================================================


def _load_flashcard_mapping() -> Tuple[Dict[str, str], Dict[str, int]]:
    now = time.time()

    if now - _mapping_cache["last_fetch"] < CACHE_TTL_SECONDS:
        return _mapping_cache["mapping"], _mapping_cache["versions"]

    try:
        resp = requests.get(FLASHCARD_MAPPING_URL, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        mapping = data.get("mapping", {})
        versions = data.get("versions", {})

        if not isinstance(mapping, dict) or not isinstance(versions, dict):
            raise ValueError("Invalid mapping payload")

        _mapping_cache["mapping"] = mapping
        _mapping_cache["versions"] = versions
        _mapping_cache["last_fetch"] = now

    except Exception:
        # 🔒 FAIL SAFE
        _mapping_cache["mapping"] = {}
        _mapping_cache["versions"] = {}
        _mapping_cache["last_fetch"] = now

    return _mapping_cache["mapping"], _mapping_cache["versions"]


# =====================================================
# CARD ID → RULE KEY
# =====================================================


def map_card_ids_to_rules(raw_answers: Dict) -> Dict[str, str]:
    mapping, _ = _load_flashcard_mapping()
    mapped: Dict[str, str] = {}

    if not isinstance(raw_answers, dict):
        return mapped

    for card_id, answer in raw_answers.items():
        rule_key = mapping.get(str(card_id))
        if rule_key and isinstance(answer, str):
            mapped[rule_key] = answer

    return mapped


# =====================================================
# SEVERITY → DAMAGE (MATCHES NEW MODELS)
# =====================================================

HAIRLOSS_SEVERITY_MAP = {
    "none":       0,
    "low":       10,
    "mild":      25,
    "moderate":  45,
    "severe":    70,
    "very_severe": 85,
    "unknown":    0,
}

DANDRUFF_SEVERITY_MAP = {
    "none":     0,
    "low":     15,
    "moderate": 55,
    "severe":  80,
    "unknown":  0,
}

# ──────────────────────────────────────────────────────────────
# SEVERITY CONSENSUS CEILING TABLE
#
# Calculates a SCORE CEILING purely from the hairloss severity
# pattern across the three camera views (top / front / back),
# using their fixed detection weights (0.5 / 0.3 / 0.2).
#
# Using ABSOLUTE severe weight (sum of weights of severe+ views)
# because the weights are clinically fixed and well-understood:
#
#   View weights:  top=0.5   front=0.3   back=0.2
#
#   severe_abs thresholds → ceiling mapping:
#   ─────────────────────────────────────────────
#   ≥ 0.70  (top+front, top+back, all three)  →  42  (Poor)
#   ≥ 0.50  (top alone)                        →  65  (Moderate)
#   ≥ 0.30  (front alone)                      →  78  (Good/Moderate border)
#   < 0.30  (back alone, or none)              → moderate-based rules below
#
#   moderate_abs thresholds (when no severe views):
#   ≥ 0.75  (all/nearly all views moderate)   →  68  (Moderate)
#   ≥ 0.50  (top moderate + others light)     →  78  (Good boundary)
#   < 0.50                                     → 100  (uncapped)
#
# The ceiling is a MAXIMUM score from hairloss alone.
# Dandruff and lifestyle damage can only push the score LOWER,
# never above this ceiling.
# ──────────────────────────────────────────────────────────────

SEVERITY_RANK = {
    "unknown":    -1,
    "none":        0,
    "low":         1,
    "mild":        2,
    "moderate":    3,
    "high":        4,
    "severe":      5,
    "very_severe": 6,
}

# View weights — must match VIEW_WEIGHTS below
_TOP_W   = 0.5
_FRONT_W = 0.3
_BACK_W  = 0.2

VIEW_WEIGHTS = {"top": _TOP_W, "front": _FRONT_W, "back": _BACK_W}


def _compute_severity_ceiling(view_data: Dict[str, Dict]) -> int:
    """
    Returns a score ceiling (0–100) based purely on the distribution
    of hairloss severity across camera views.

    view_data: {"top": {"sev": str, "rank": int, "weight": float}, ...}
    """
    severe_abs = sum(
        d["weight"] for d in view_data.values()
        if d["sev"] in ("severe", "very_severe")
    )
    vsevere_abs = sum(
        d["weight"] for d in view_data.values()
        if d["sev"] == "very_severe"
    )
    moderate_abs = sum(
        d["weight"] for d in view_data.values()
        if d["rank"] >= SEVERITY_RANK["moderate"] and d["sev"] != "unknown"
    )

    # ── Severe / very-severe ceilings ─────────────────────────────────────────
    if vsevere_abs >= 0.50 or severe_abs >= 0.70:
        # Top+front / top+back / all views severe (or any with very_severe top)
        return 42   # Poor

    if severe_abs >= 0.50:
        # Top view severe alone (0.5 weight)
        return 65   # Moderate

    if severe_abs >= 0.30:
        # Front view severe alone (0.3 weight)
        return 78   # Borderline Good — dandruff/lifestyle can push to Moderate

    # ── Moderate ceilings (no severe views) ───────────────────────────────────
    if moderate_abs >= 0.75:
        # All or nearly all views moderate
        return 68   # Moderate

    if moderate_abs >= 0.50:
        # Top moderate with some lighter views
        return 78   # Good boundary

    # ── Mild / low / none — no artificial ceiling ─────────────────────────────
    return 100


def normalize_severity(value: str) -> str:
    if not isinstance(value, str):
        return "unknown"
    return value.strip().lower()


# =====================================================
# VERSIONED FLASHCARD RULES (UPDATED)
# =====================================================

FLASHCARD_RULES = {
    # 1️⃣ Hair Wash Frequency
    "hair_wash": {
        1: {
            "Daily": 0,
            "Every 2–3 days": 5,
            "Once a week": 15,
            "Less than once a week": 25,
        },
        2: {
            "Daily": 0,
            "Every 2–3 days": 8,
            "Once a week": 20,
            "Less than once a week": 30,
        },
    },
    # 2️⃣ Shampoo Type
    "shampoo_type": {
        1: {
            "Regular commercial shampoo": 10,
            "Anti-dandruff shampoo": 5,
            "Herbal / natural shampoo": 0,
            "I change shampoos frequently": 15,
        }
    },
    # 3️⃣ Heat Styling
    "heat_styling": {
        1: {
            "Every day": 30,
            "2–3 times a week": 15,
            "Rarely": 5,
            "Never": 0,
        }
    },
    # 4️⃣ Helmet / Cap Usage
    "helmet_usage": {
        1: {
            "Yes, daily": 15,
            "Yes, occasionally": 8,
            "Rarely": 3,
            "Never": 0,
        }
    },
    # 5️⃣ Scalp Sweat
    "scalp_sweat": {
        1: {
            "Yes, a lot": 20,
            "Moderate sweating": 10,
            "Very little": 3,
            "Not sure": 5,
        }
    },
    # 6️⃣ Diet
    "diet": {
        1: {
            "Balanced and nutritious": 0,
            "Mostly home food but irregular": 8,
            "Mostly fast food / junk food": 20,
            "Very irregular meals": 25,
        }
    },
    # 7️⃣ Sleep
    "sleep": {
        1: {
            "7–8 hours": 0,
            "6–7 hours": 8,
            "Less than 6 hours": 20,
            "Irregular sleep schedule": 25,
        }
    },
    # 8️⃣ Stress
    "stress": {
        1: {
            "Very high": 25,
            "Moderate": 12,
            "Low": 5,
            "I don't feel stressed": 0,
        }
    },
    # 9️⃣ Water Type
    "water_type": {
        1: {
            "Normal tap water": 5,
            "Filtered / RO water": 0,
            '"Hard water (borewell / hostel water)"': 20,
            "Not sure": 8,
        }
    },
    # 🔟 Family History
    "family_history": {
        1: {
            "Yes": 25,
            "No": 0,
            "Not sure": 10,
        }
    },
    # 1️⃣1️⃣ Problem Duration
    "problem_duration": {
        1: {
            "Less than 2 months": 5,
            "2–6 months": 10,
            "More than 6 months": 20,
            "More than a year": 30,
        }
    },
}


# =====================================================
# RULE PENALTY (VERSION-AWARE)
# =====================================================


def _get_rule_penalty(rule_key: str, answer: str, versions: Dict[str, int]) -> int:
    rule_versions = FLASHCARD_RULES.get(rule_key)
    if not rule_versions:
        return 0

    version = versions.get(rule_key)
    if version not in rule_versions:
        version = max(rule_versions.keys())

    return rule_versions[version].get(answer, 0)


# =====================================================
# FLASHCARD DAMAGE
# =====================================================


def compute_flashcard_damage(mapped_flashcards: Dict[str, str]) -> float:
    _, versions = _load_flashcard_mapping()
    penalties: List[int] = []

    for rule_key, answer in mapped_flashcards.items():
        if not isinstance(answer, str):
            continue

        penalty = _get_rule_penalty(rule_key, answer, versions)
        penalties.append(penalty)

    if not penalties:
        return 0.0

    avg_penalty = sum(penalties) / len(penalties)
    lifestyle_damage = min(avg_penalty * 2, 60)

    return round(lifestyle_damage, 2)


# =====================================================
# FINAL HEALTH SCORE
# =====================================================


def compute_hair_health_score(
    hairloss_views,
    dandruff_severity: str,
    flashcard_answers: Dict,
) -> Tuple[int, str, Dict]:

    # ──────────────────────────────────────────────────────────
    # 🔒 NORMALIZE HAIRLOSS INPUT (Backward Compatible)
    # ──────────────────────────────────────────────────────────

    if isinstance(hairloss_views, str):
        hairloss_views = {
            "top": hairloss_views,
            "front": "unknown",
            "back": "unknown",
        }

    if not isinstance(hairloss_views, dict):
        hairloss_views = {
            "top": "unknown",
            "front": "unknown",
            "back": "unknown",
        }

    hairloss_views = {
        "top":   hairloss_views.get("top",   "unknown"),
        "front": hairloss_views.get("front", "unknown"),
        "back":  hairloss_views.get("back",  "unknown"),
    }

    # ──────────────────────────────────────────────────────────
    # NORMALIZE DANDRUFF INPUT
    # ──────────────────────────────────────────────────────────

    dandruff_severity = normalize_severity(dandruff_severity)
    if dandruff_severity == "healthy":
        dandruff_severity = "none"

    # ──────────────────────────────────────────────────────────
    # 1️⃣  COMBINE HAIRLOSS FROM MULTIPLE VIEWS
    # ──────────────────────────────────────────────────────────

    hairloss_view_damage = {}
    total_weighted_damage = 0.0
    total_weight = 0.0
    view_data: Dict[str, Dict] = {}

    for view, weight in VIEW_WEIGHTS.items():
        severity = normalize_severity(hairloss_views.get(view))
        damage   = HAIRLOSS_SEVERITY_MAP.get(severity, 0)
        rank     = SEVERITY_RANK.get(severity, -1)

        hairloss_view_damage[view] = {
            "severity": severity,
            "damage":   damage,
            "weight":   weight,
        }
        view_data[view] = {
            "sev":    severity,
            "dmg":    damage,
            "rank":   rank,
            "weight": weight,
        }

        if severity != "unknown":
            total_weighted_damage += damage * weight
            total_weight += weight

    combined_hairloss_damage = (
        total_weighted_damage / total_weight if total_weight > 0 else 0.0
    )
    combined_hairloss_damage = round(combined_hairloss_damage, 2)

    # ── Overall severity label ────────────────────────────────
    normalized_views = [
        normalize_severity(hairloss_views.get(v)) for v in ("top", "front", "back")
    ]

    if "very_severe" in normalized_views:
        overall_hairloss_severity = "very_severe"
    elif combined_hairloss_damage >= 65:
        overall_hairloss_severity = "severe"
    elif combined_hairloss_damage >= 40:
        overall_hairloss_severity = "moderate"
    elif combined_hairloss_damage >= 20:
        overall_hairloss_severity = "mild"
    else:
        overall_hairloss_severity = "normal"

    # ──────────────────────────────────────────────────────────
    # 2️⃣  DANDRUFF DAMAGE
    # ──────────────────────────────────────────────────────────

    dandruff_damage = DANDRUFF_SEVERITY_MAP.get(dandruff_severity, 0)

    # ──────────────────────────────────────────────────────────
    # 3️⃣  LIFESTYLE DAMAGE (FLASHCARDS)
    # ──────────────────────────────────────────────────────────

    if not isinstance(flashcard_answers, dict):
        flashcard_answers = {}

    mapped_flashcards = map_card_ids_to_rules(flashcard_answers)
    lifestyle_damage  = compute_flashcard_damage(mapped_flashcards)

    # ──────────────────────────────────────────────────────────
    # 4️⃣  FINAL HEALTH SCORE
    # ──────────────────────────────────────────────────────────

    WEIGHTS = {
        "hairloss":  0.45,
        "dandruff":  0.25,
        "lifestyle": 0.30,
    }

    total_damage = (
        combined_hairloss_damage * WEIGHTS["hairloss"]
        + dandruff_damage        * WEIGHTS["dandruff"]
        + lifestyle_damage       * WEIGHTS["lifestyle"]
    )

    raw_score = max(0, min(100, int(round(100 - total_damage))))

    # ──────────────────────────────────────────────────────────
    # 5️⃣  SEVERITY CONSENSUS CEILING
    #
    # The weighted-damage formula alone can't produce "Poor" when
    # all views are severe, because hairloss only carries 45 % of
    # the total score.  The ceiling table corrects this by capping
    # the score based on how many views (and which ones) show
    # severe or very-severe hairloss, independent of the formula.
    #
    # Dandruff / lifestyle damage can push the score below the
    # ceiling but can never raise it above it.
    # ──────────────────────────────────────────────────────────

    severity_ceiling = _compute_severity_ceiling(view_data)
    score = min(raw_score, severity_ceiling)

    # ── Label ────────────────────────────────────────────────
    if score >= 75:
        label = "Good"
    elif score >= 50:
        label = "Moderate"
    else:
        label = "Poor"

    # ──────────────────────────────────────────────────────────
    # BREAKDOWN (unchanged structure — no downstream breakage)
    # ──────────────────────────────────────────────────────────

    breakdown = {
        "hairloss": {
            "overall_severity":   overall_hairloss_severity,
            "combined_damage":    combined_hairloss_damage,
            "severity_ceiling":   severity_ceiling,   # NEW — useful for debugging
            "views":              hairloss_view_damage,
            "weight":             WEIGHTS["hairloss"],
        },
        "dandruff": {
            "severity": dandruff_severity,
            "damage":   dandruff_damage,
            "weight":   WEIGHTS["dandruff"],
        },
        "lifestyle": {
            "damage":   lifestyle_damage,
            "weight":   WEIGHTS["lifestyle"],
            "answered": len(mapped_flashcards),
        },
        "total_damage": round(total_damage, 2),
    }

    return score, label, breakdown