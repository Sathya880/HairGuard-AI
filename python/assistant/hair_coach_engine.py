"""
Hair Coach Engine

Generates rich, contextual coaching summaries for the Flutter AI Hair Coach
home-screen greeting card. This produces the short (2–3 sentence) message
shown before the user taps any action button.

Design goals:
- Always references the user's actual scores and root cause
- Different message for each combination of score band + risk level
- Ends with one clear, immediate action the user can take
- No generic filler — every word is specific to this user's data
"""

from typing import Optional, Dict, Any


# =====================================================
# SEVERITY / SCORE HELPERS
# =====================================================

def _score_band(score: float) -> str:
    if score >= 75:
        return "good"
    if score >= 55:
        return "moderate"
    if score >= 40:
        return "poor"
    return "critical"


def _severity_phrase(sev: Optional[str]) -> str:
    mapping = {
        "none": "no active hair loss",
        "low": "minor hair thinning",
        "mild": "mild hair loss",
        "moderate": "moderate hair loss",
        "high": "significant hair loss",
        "severe": "severe hair loss",
        "very_severe": "very severe hair loss",
    }
    return mapping.get((sev or "").lower(), "hair changes detected")


def _dandruff_phrase(sev: Optional[str]) -> str:
    mapping = {
        "none": "",
        "low": "",
        "mild": " with mild dandruff",
        "moderate": " with moderate dandruff",
        "severe": " and severe dandruff that needs urgent attention",
    }
    return mapping.get((sev or "").lower(), "")


def _root_cause_action(root_cause: Optional[str]) -> str:
    """One-sentence action specific to root cause."""
    if not root_cause:
        return "Follow your assigned routine daily to start building data."
    rc = root_cause.lower()

    if "stress" in rc or "cortisol" in rc:
        return "Priority today: add a 10-minute stress-relief activity — cortisol is your main enemy right now."
    if "hormonal" in rc or "dht" in rc or "androgenetic" in rc:
        return "Consider discussing DHT-blocking treatments with a dermatologist soon."
    if "nutritional" in rc or "deficiency" in rc or "diet" in rc:
        return "Start with one protein-rich meal and a multivitamin with biotin and zinc today."
    if "fungal" in rc or "seborrheic" in rc or "dandruff" in rc:
        return "Use an anti-fungal shampoo tonight — this is the fastest lever for your condition."
    if "genetic" in rc:
        return "Protect existing follicles now with consistent scalp care and clinically-backed topicals."
    if "scalp" in rc:
        return "A 5-minute oil massage tonight will boost scalp circulation — your follicles need blood flow."
    if "alopecia" in rc:
        return "Early treatment is critical for alopecia — book a dermatologist appointment this week."
    return f"Focus on your primary cause ({root_cause}) with your assigned routine."


def _lifestyle_note(lifestyle_score: Optional[float]) -> str:
    if lifestyle_score is None:
        return ""
    if lifestyle_score < 40:
        return " Your lifestyle score is low — sleep, stress and diet are amplifying the problem."
    if lifestyle_score < 65:
        return " Improving sleep and hydration will accelerate recovery."
    return ""


def _risk_note(risk_percent: float) -> str:
    if risk_percent >= 70:
        return f" ⚠️ Your 6-month risk is {risk_percent:.0f}% — acting now can change this trajectory."
    if risk_percent >= 45:
        return f" Your 6-month risk sits at {risk_percent:.0f}% — manageable if you stay consistent."
    return ""


# =====================================================
# MAIN ENGINE
# =====================================================

class HairCoachEngine:
    """
    Generates the short contextual greeting message shown on the
    AI Hair Coach home screen.
    """

    def generate_greeting(
        self,
        hair_score: float,
        lifestyle_score: Optional[float] = None,
        hairloss_severity: Optional[str] = None,
        dandruff_severity: Optional[str] = None,
        root_cause: Optional[str] = None,
        risk_6_month: float = 0.0,
        trend: str = "stable",
        reports_count: int = 1,
    ) -> str:
        """
        Generate a concise, personalised greeting message (2–3 sentences).

        Returns:
            str: Coaching message for the Flutter home card.
        """
        band = _score_band(hair_score)
        hl_phrase = _severity_phrase(hairloss_severity)
        dd_phrase = _dandruff_phrase(dandruff_severity)
        action = _root_cause_action(root_cause)
        ls_note = _lifestyle_note(lifestyle_score)
        risk_note = _risk_note(risk_6_month)

        # First scan — no trend data
        if reports_count <= 1:
            return self._first_scan_message(
                hair_score, band, hl_phrase, dd_phrase, action, ls_note, risk_note
            )

        # Trend-based messages
        if trend == "improving":
            return self._improving_message(
                hair_score, hl_phrase, dd_phrase, action, ls_note
            )
        elif trend == "worsening":
            return self._worsening_message(
                hair_score, band, hl_phrase, dd_phrase, action, ls_note, risk_note
            )
        else:
            return self._stable_message(
                hair_score, band, hl_phrase, dd_phrase, action, ls_note, risk_note
            )

    def _first_scan_message(
        self, score, band, hl_phrase, dd_phrase, action, ls_note, risk_note
    ) -> str:
        if band == "critical":
            return (
                f"Your first scan shows a hair health score of {score:.0f}/100 "
                f"with {hl_phrase}{dd_phrase} — this needs immediate attention.{ls_note}{risk_note} "
                f"{action}"
            )
        if band == "poor":
            return (
                f"Welcome! Your baseline score is {score:.0f}/100 with {hl_phrase}{dd_phrase}.{ls_note} "
                f"There's real room to improve from here. {action}"
            )
        if band == "moderate":
            return (
                f"Your scan shows a score of {score:.0f}/100 with {hl_phrase}{dd_phrase} — "
                f"a solid starting point.{ls_note} "
                f"{action}"
            )
        # Good
        return (
            f"Great baseline! Score: {score:.0f}/100 with {hl_phrase}{dd_phrase}.{ls_note} "
            f"Your goal is to maintain and optimise. {action}"
        )

    def _improving_message(
        self, score, hl_phrase, dd_phrase, action, ls_note
    ) -> str:
        return (
            f"Your hair health is improving — score now {score:.0f}/100 with {hl_phrase}{dd_phrase}.{ls_note} "
            f"This progress is real. Keep the momentum: {action}"
        )

    def _worsening_message(
        self, score, band, hl_phrase, dd_phrase, action, ls_note, risk_note
    ) -> str:
        urgency = "⚠️ " if band in ("critical", "poor") else ""
        return (
            f"{urgency}Your score has declined to {score:.0f}/100 with {hl_phrase}{dd_phrase}.{ls_note}{risk_note} "
            f"A change in approach is needed now. {action}"
        )

    def _stable_message(
        self, score, band, hl_phrase, dd_phrase, action, ls_note, risk_note
    ) -> str:
        if band in ("critical", "poor"):
            return (
                f"Score holding at {score:.0f}/100 with {hl_phrase}{dd_phrase}.{risk_note} "
                f"Stability is good but the score needs to climb. {action}"
            )
        return (
            f"Score stable at {score:.0f}/100 with {hl_phrase}{dd_phrase}.{ls_note} "
            f"You're in maintenance mode — ready to optimise. {action}"
        )


# =====================================================
# CONVENIENCE FUNCTION
# =====================================================

def generate_coach_greeting(
    report: Dict[str, Any],
    progress_result: Optional[Dict[str, Any]] = None,
    trend: str = "stable",
    reports_count: int = 1,
) -> str:
    """
    Generate greeting from a full or trimmed report dict.

    Args:
        report: Full AIResult or trimmed { hairScore, lifestyleScore, ... }
        progress_result: ProgressTrackerEngine output
        trend: fallback trend if progress_result not available
        reports_count: Total number of scans available
    """

    from .context_builder import (
        _extract_hair_score,
        _extract_lifestyle_score,
        _extract_hairloss_severity,
        _extract_dandruff_severity,
        _extract_root_cause,
    )

    # Extract core data
    hair_score = _extract_hair_score(report)
    lifestyle_score = _extract_lifestyle_score(report)
    hairloss_severity = _extract_hairloss_severity(report)
    dandruff_severity = _extract_dandruff_severity(report)
    root_cause = _extract_root_cause(report, {})

    # Default values
    hair_trend = trend
    score_change = 0

    # Use progress tracker if available
    if progress_result:
        score_change = progress_result.get("score_change", 0)

        progress_trend = progress_result.get("hair_trend")

        if progress_trend == "Improved":
            hair_trend = "improving"
        elif progress_trend == "Worsened":
            hair_trend = "worsening"
        elif progress_trend == "Stable":
            hair_trend = "stable"

    # Initialize engine
    engine = HairCoachEngine()

    # Generate message
    message = engine.generate_greeting(
        hair_score=hair_score,
        lifestyle_score=lifestyle_score,
        hairloss_severity=hairloss_severity,
        dandruff_severity=dandruff_severity,
        root_cause=root_cause,
        trend=hair_trend,
        reports_count=reports_count,
    )

    # Add progress insight if available
    if progress_result and reports_count > 1:
        if score_change > 0:
            message += f" (+{int(score_change)} points since your last scan.)"
        elif score_change < 0:
            message += f" ({int(score_change)} points since your last scan.)"

    return message