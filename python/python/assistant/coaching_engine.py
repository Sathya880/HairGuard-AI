"""
Coaching Engine Module

Generates structured coaching messages based on strategy mode and context.
All messages are specific to the user's actual root_cause, severity,
lifestyle_score, and dandruff_severity — never generic.
"""

from dataclasses import dataclass
from typing import Literal, Optional
from .state_classifier import AssistantContext

StrategyMode = Literal[
    "urgency",
    "intervention",
    "optimization",
    "accountability",
    "reinforcement",
    "data_collection",
    "monitoring",
]

ToneType = Literal[
    "urgent",
    "firm",
    "supportive",
    "encouraging",
    "analytical",
    "neutral",
]

PriorityLevel = Literal["critical", "high", "medium", "low"]


@dataclass
class CoachingResponse:
    """Structured coaching response."""
    message: str
    tone_type: ToneType
    priority_level: PriorityLevel


# =====================================================
# HELPERS
# =====================================================

def _severity_label(sev: Optional[str]) -> str:
    """Convert severity to a readable phrase."""
    mapping = {
        "none": "no hair loss",
        "low": "minor hair thinning",
        "mild": "mild hair loss",
        "moderate": "moderate hair loss",
        "high": "significant hair loss",
        "severe": "severe hair loss",
        "very_severe": "very severe hair loss",
        "unknown": "hair changes",
    }
    return mapping.get((sev or "unknown").lower(), "hair changes")


def _dandruff_label(sev: Optional[str]) -> str:
    mapping = {
        "none": "no dandruff",
        "low": "minor scalp flaking",
        "mild": "mild dandruff",
        "moderate": "moderate dandruff",
        "severe": "severe dandruff",
        "unknown": "",
    }
    return mapping.get((sev or "unknown").lower(), "")


def _root_cause_tip(root_cause: Optional[str]) -> str:
    """Return a short cause-specific action tip."""
    if not root_cause:
        return "address your identified root cause"
    rc = root_cause.lower()

    if "stress" in rc or "cortisol" in rc:
        return "manage cortisol: daily 10-min walks, cut screen time before bed"
    if "hormonal" in rc or "dht" in rc or "androgenetic" in rc:
        return "consult a dermatologist for hormonal or DHT-related treatment options"
    if "nutritional" in rc or "deficiency" in rc or "diet" in rc:
        return "increase protein, biotin, zinc and iron intake consistently"
    if "dandruff" in rc or "fungal" in rc or "seborrheic" in rc:
        return "use ketoconazole or zinc pyrithione shampoo 2–3× per week"
    if "genetic" in rc:
        return "use clinically proven topical treatments and protect existing follicles"
    if "alopecia" in rc:
        return "seek early dermatologist evaluation — timing matters with alopecia"
    if "scalp" in rc:
        return "improve scalp circulation with oil massage and a gentle routine"
    return f"target your identified cause: {root_cause}"


def _score_band(score: float) -> str:
    if score >= 75:
        return "good"
    if score >= 55:
        return "moderate"
    if score >= 40:
        return "poor"
    return "critical"


# =====================================================
# COACHING ENGINE
# =====================================================

class CoachingEngine:
    """
    Generates personalized coaching messages.
    Every message references the user's actual metrics:
    hair_score, root_cause, severity, lifestyle_score, dandruff.
    """

    def __init__(self):
        pass

    def generate_coaching(
        self, strategy_mode: StrategyMode, context: AssistantContext
    ) -> CoachingResponse:
        score_delta = context.hair_score - context.previous_score

        handlers = {
            "urgency": self._handle_urgency,
            "intervention": self._handle_intervention,
            "optimization": self._handle_optimization,
            "accountability": self._handle_accountability,
            "reinforcement": self._handle_reinforcement,
            "data_collection": self._handle_data_collection,
            "monitoring": self._handle_monitoring,
        }

        handler = handlers.get(strategy_mode, self._handle_monitoring)
        return handler(context, score_delta)

    # ── URGENCY ────────────────────────────────────────────────
    def _handle_urgency(self, context: AssistantContext, delta: float) -> CoachingResponse:
        hl_label = _severity_label(getattr(context, "hairloss_severity", None))
        cause_tip = _root_cause_tip(context.root_cause)
        dd_label = _dandruff_label(getattr(context, "dandruff_severity", None))
        dd_note = f" Combined with {dd_label}," if dd_label else ""

        message = (
            f"⚠️ Immediate attention needed. Your hair health score is {context.hair_score}/100 "
            f"with {hl_label}.{dd_note} your 6-month risk is {context.risk_6_month:.0f}%. "
            f"Root cause identified: {context.root_cause or 'under evaluation'}. "
            f"Without action now, follicle damage may become permanent. "
            f"Priority step: {cause_tip}. "
            f"Book a dermatologist consultation this week."
        )
        return CoachingResponse(message=message, tone_type="urgent", priority_level="critical")

    # ── INTERVENTION ───────────────────────────────────────────
    def _handle_intervention(self, context: AssistantContext, delta: float) -> CoachingResponse:
        hl_label = _severity_label(getattr(context, "hairloss_severity", None))
        cause_tip = _root_cause_tip(context.root_cause)
        band = _score_band(context.hair_score)

        message = (
            f"Your hair score dropped {delta:+.1f} points to {context.hair_score}/100 ({band}). "
            f"Current condition: {hl_label}. "
            f"Root cause: {context.root_cause or 'not yet confirmed'}. "
            f"This decline pattern means your current routine isn't enough. "
            f"Targeted action: {cause_tip}. "
            f"Review any recent product changes or lifestyle disruptions."
        )
        return CoachingResponse(message=message, tone_type="firm", priority_level="high")

    # ── OPTIMIZATION ───────────────────────────────────────────
    def _handle_optimization(self, context: AssistantContext, delta: float) -> CoachingResponse:
        potential = 100 - context.hair_score
        ls = getattr(context, "lifestyle_score", None)
        lifestyle_note = (
            f" Your lifestyle score is {ls:.0f}/100 — "
            + ("improving sleep and diet could unlock further gains." if ls and ls < 70
               else "maintaining this is key.")
        ) if ls else ""

        cause_tip = _root_cause_tip(context.root_cause)

        message = (
            f"Solid progress. Score stable at {context.hair_score}/100 with {potential:.0f} points "
            f"of headroom remaining.{lifestyle_note} "
            f"Root cause ({context.root_cause or 'identified'}) is being managed. "
            f"To push past this plateau: {cause_tip}. "
            f"Small consistent changes now will compound over 4–8 weeks."
        )
        return CoachingResponse(message=message, tone_type="analytical", priority_level="medium")

    # ── ACCOUNTABILITY ─────────────────────────────────────────
    def _handle_accountability(self, context: AssistantContext, delta: float) -> CoachingResponse:
        gap = max(0, 60 - context.routine_adherence)
        hl_label = _severity_label(getattr(context, "hairloss_severity", None))
        cause_tip = _root_cause_tip(context.root_cause)

        message = (
            f"Consistency check: routine adherence at {context.routine_adherence:.0f}% — "
            f"{gap:.0f} points below the minimum for results. "
            f"Your current hair score is {context.hair_score}/100 with {hl_label}. "
            f"With root cause identified as {context.root_cause or 'under review'}, "
            f"an inconsistent routine allows the condition to progress. "
            f"Focus on one non-negotiable daily step: {cause_tip}. "
            f"Start there. Complexity can wait."
        )
        return CoachingResponse(message=message, tone_type="firm", priority_level="high")

    # ── REINFORCEMENT ──────────────────────────────────────────
    def _handle_reinforcement(self, context: AssistantContext, delta: float) -> CoachingResponse:
        hl_label = _severity_label(getattr(context, "hairloss_severity", None))
        ls = getattr(context, "lifestyle_score", None)
        ls_note = f" Lifestyle score: {ls:.0f}/100." if ls else ""

        message = (
            f"Great momentum! Score improved from {context.previous_score} to {context.hair_score} "
            f"({delta:+.1f} points). {hl_label.capitalize()} is responding to your routine. "
            f"Adherence: {context.routine_adherence:.0f}%.{ls_note} "
            f"Root cause ({context.root_cause or 'identified'}) is being addressed. "
            f"Keep this protocol exactly as-is for the next 4 weeks. "
            f"Avoid swapping products mid-progress — consistency is what's working."
        )
        return CoachingResponse(message=message, tone_type="encouraging", priority_level="low")

    # ── DATA COLLECTION ────────────────────────────────────────
    def _handle_data_collection(self, context: AssistantContext, delta: float) -> CoachingResponse:
        issues = []
        if context.confidence < 50:
            issues.append(f"confidence at {context.confidence:.0f}%")
        if context.data_strength == "weak":
            issues.append(f"only {context.reports_count} scan(s) recorded")
        if not context.root_cause:
            issues.append("root cause not yet confirmed")

        message = (
            f"Not enough data for a precise coaching plan yet. "
            f"Current state: {', '.join(issues) if issues else 'limited history'}. "
            f"Hair score: {context.hair_score}/100. "
            f"Complete at least 3 scans over 4–6 weeks to establish reliable trends. "
            f"In the meantime, follow your assigned routine daily and track how your scalp feels. "
            f"More data = more accurate, personalised recommendations."
        )
        return CoachingResponse(message=message, tone_type="analytical", priority_level="medium")

    # ── MONITORING ─────────────────────────────────────────────
    def _handle_monitoring(self, context: AssistantContext, delta: float) -> CoachingResponse:
        hl_label = _severity_label(getattr(context, "hairloss_severity", None))
        dd_label = _dandruff_label(getattr(context, "dandruff_severity", None))
        condition_note = hl_label
        if dd_label:
            condition_note += f" with {dd_label}"

        cause_tip = _root_cause_tip(context.root_cause)

        message = (
            f"Stable. Hair score: {context.hair_score}/100. Condition: {condition_note}. "
            f"Root cause: {context.root_cause or 'under monitoring'}. "
            f"6-month risk: {context.risk_6_month:.0f}%. "
            f"Routine adherence: {context.routine_adherence:.0f}%. "
            f"Continue current protocol. Focus area: {cause_tip}. "
            f"Next scan recommended in 2–3 weeks."
        )
        return CoachingResponse(message=message, tone_type="neutral", priority_level="low")


# =====================================================
# CONVENIENCE FUNCTION
# =====================================================

def generate_coaching_message(
    strategy_mode: StrategyMode, context: AssistantContext
) -> CoachingResponse:
    engine = CoachingEngine()
    return engine.generate_coaching(strategy_mode, context)