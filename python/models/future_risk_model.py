"""
Future Risk Model — Enhanced with trend projections and graph-ready data.

Returns a structured payload containing:
  - month-by-month score projections (for line charts)
  - risk tier and confidence band (for shaded area charts)
  - contributing risk factors with weights (for bar/radar charts)
  - milestone events (for annotated timeline charts)
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional
import math


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

SEVERITY_DECAY_RATE = {
    # How many score points are lost per month without intervention
    "none":       0.3,
    "low":        0.6,
    "mild":       1.0,
    "moderate":   1.6,
    "high":       2.2,
    "severe":     3.0,
    "very_severe": 3.8,
    "unknown":    1.0,
}

DANDRUFF_PENALTY = {
    "none":     0.0,
    "low":      0.1,
    "mild":     0.2,
    "moderate": 0.35,
    "severe":   0.55,
    "unknown":  0.2,
}

# Extra points recovered (or lost) per month based on lifestyle score.
# Using a plain list of (lo, hi, bonus) tuples instead of a tuple-keyed
# dict — tuple-keyed dicts cause "list indices must be integers or slices,
# not tuple" when the object is inadvertently treated as a list elsewhere.
_LIFESTYLE_BONUS_RANGES = [
    (80, 100,  0.8),
    (60,  79,  0.4),
    (40,  59,  0.0),
    (20,  39, -0.3),
    (0,   19, -0.7),
]

RISK_TIERS = [
    (80, 100, "low",      "Low Risk",      "#4CAF50"),
    (60,  79, "guarded",  "Guarded",       "#8BC34A"),
    (40,  59, "moderate", "Moderate Risk", "#FF9800"),
    (20,  39, "high",     "High Risk",     "#F44336"),
    (0,   19, "critical", "Critical",      "#B71C1C"),
]

PROJECTION_MONTHS = 12   # How far ahead to project
CONFIDENCE_BAND   = 5.0  # ± points for the confidence interval shading


# ─────────────────────────────────────────────────────────────────────────────
# Data classes (graph-ready payloads)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TrendPoint:
    month: int               # 0 = current, 1–12 = future months
    label: str               # "Now", "Month 1", …, "Month 12"
    score: float             # projected hair health score
    score_upper: float       # confidence band upper bound
    score_lower: float       # confidence band lower bound
    risk_tier: str           # e.g. "moderate"
    risk_label: str          # e.g. "Moderate Risk"
    color: str               # hex color for chart theming


@dataclass
class RiskFactor:
    key: str                 # machine-readable key
    label: str               # human-readable label
    impact: float            # 0–100, how much this factor drives risk
    direction: str           # "worsening" | "stable" | "improving"
    description: str


@dataclass
class Milestone:
    month: int
    label: str
    description: str
    severity: str            # "warning" | "danger" | "info"


@dataclass
class FutureRiskResult:
    # ── Summary ──────────────────────────────────────────────────────────────
    current_score: float
    projected_score_3m: float
    projected_score_6m: float
    projected_score_12m: float

    overall_risk_tier: str
    overall_risk_label: str
    overall_risk_color: str
    timeline_summary: str    # one-line human label (backwards-compat)

    # ── Graph data ────────────────────────────────────────────────────────────
    trend_points: List[TrendPoint]      # month-by-month line chart data
    risk_factors: List[RiskFactor]      # bar / radar chart data
    milestones: List[Milestone]         # annotated events on timeline

    # ── Metadata ─────────────────────────────────────────────────────────────
    intervention_scenario: Optional[List[TrendPoint]] = field(default=None)
    # ^ what the trend looks like IF the user follows recommendations


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_risk_tier(score: float):
    for low, high, key, label, color in RISK_TIERS:
        if low <= score <= high:
            return key, label, color
    return "critical", "Critical", "#B71C1C"


def _get_lifestyle_bonus(lifestyle_score: float) -> float:
    """Return the monthly score adjustment for the given lifestyle score."""
    score = float(lifestyle_score)          # guard against int/str input
    for lo, hi, bonus in _LIFESTYLE_BONUS_RANGES:
        if lo <= score <= hi:
            return bonus
    return 0.0


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _sigmoid_decay(base_decay: float, month: int) -> float:
    """
    Applies a sigmoid curve so decay accelerates early then levels off.
    Mimics real-world hair health deterioration patterns.
    """
    acceleration = 1 / (1 + math.exp(-0.3 * (month - 4)))
    return base_decay * (0.6 + 0.8 * acceleration)


def _project_scores(
    start_score: float,
    monthly_decay: float,
    lifestyle_bonus: float,
    months: int,
) -> List[float]:
    """Project score over `months` applying decay and lifestyle adjustment."""
    scores = [start_score]
    net_change = -monthly_decay + lifestyle_bonus

    for m in range(1, months + 1):
        prev = scores[-1]
        # Sigmoid-modulated decay + slight mean-reversion at extremes
        decay = _sigmoid_decay(abs(net_change), m) * (-1 if net_change < 0 else 1)
        mean_reversion = (50 - prev) * 0.01   # gentle pull toward 50
        new_score = _clamp(prev + decay + mean_reversion)
        scores.append(new_score)

    return scores


# ─────────────────────────────────────────────────────────────────────────────
# Main Model
# ─────────────────────────────────────────────────────────────────────────────

class FutureRiskModel:
    """
    Predicts future hair health trajectory and returns graph-ready data.

    Args passed to predict():
        hair_score          (float, 0–100)   current overall hair health score
        hairloss_severity   (str)            e.g. "moderate"
        dandruff_severity   (str)            e.g. "mild"
        lifestyle_score     (float, 0–100)   from LifestyleAnalyzer
        root_cause          (str|None)       primary root cause key
    """

    def predict(
        self,
        hair_score: float,
        hairloss_severity: str = "unknown",
        dandruff_severity: str = "unknown",
        lifestyle_score: float = 50.0,
        root_cause: Optional[str] = None,
    ) -> dict:

        hair_score      = _clamp(float(hair_score))
        lifestyle_score = _clamp(float(lifestyle_score))

        # ── Monthly decay rate ────────────────────────────────────────────────
        base_decay      = SEVERITY_DECAY_RATE.get(hairloss_severity, 1.0)
        dandruff_extra  = DANDRUFF_PENALTY.get(dandruff_severity, 0.2)
        lifestyle_bonus = _get_lifestyle_bonus(lifestyle_score)
        monthly_decay   = base_decay + dandruff_extra

        # ── Baseline projections ──────────────────────────────────────────────
        baseline_scores = _project_scores(
            hair_score, monthly_decay, lifestyle_bonus, PROJECTION_MONTHS
        )

        # ── Intervention projections (user follows all recommendations) ───────
        # Intervention cuts decay by 60% and adds a recovery bonus
        intervention_scores = _project_scores(
            hair_score,
            monthly_decay * 0.4,
            lifestyle_bonus + 0.5,
            PROJECTION_MONTHS,
        )

        # ── Build trend points ────────────────────────────────────────────────
        def build_trend(scores: List[float]) -> List[TrendPoint]:
            points = []
            for m, score in enumerate(scores):
                tier, label, color = _get_risk_tier(score)
                points.append(TrendPoint(
                    month       = m,
                    label       = "Now" if m == 0 else f"Month {m}",
                    score       = round(score, 1),
                    score_upper = round(_clamp(score + CONFIDENCE_BAND), 1),
                    score_lower = round(_clamp(score - CONFIDENCE_BAND), 1),
                    risk_tier   = tier,
                    risk_label  = label,
                    color       = color,
                ))
            return points

        trend_points          = build_trend(baseline_scores)
        intervention_points   = build_trend(intervention_scores)

        # ── Key projections ───────────────────────────────────────────────────
        proj_3m  = baseline_scores[3]
        proj_6m  = baseline_scores[6]
        proj_12m = baseline_scores[12]

        # ── Risk factors ──────────────────────────────────────────────────────
        risk_factors = self._build_risk_factors(
            hairloss_severity, dandruff_severity,
            lifestyle_score, root_cause, hair_score
        )

        # ── Milestones ────────────────────────────────────────────────────────
        milestones = self._build_milestones(baseline_scores, hairloss_severity)

        # ── Overall risk (based on 6-month projection) ────────────────────────
        tier, risk_label, color = _get_risk_tier(proj_6m)

        # ── Timeline summary (backwards-compatible string) ────────────────────
        timeline_summary = self._timeline_summary(hair_score, proj_3m, proj_6m, proj_12m)

        result = FutureRiskResult(
            current_score         = round(hair_score, 1),
            projected_score_3m    = round(proj_3m, 1),
            projected_score_6m    = round(proj_6m, 1),
            projected_score_12m   = round(proj_12m, 1),
            overall_risk_tier     = tier,
            overall_risk_label    = risk_label,
            overall_risk_color    = color,
            timeline_summary      = timeline_summary,
            trend_points          = trend_points,
            risk_factors          = risk_factors,
            milestones            = milestones,
            intervention_scenario = intervention_points,
        )

        return asdict(result)

    # ── Risk factor builder ───────────────────────────────────────────────────

    def _build_risk_factors(
        self,
        hairloss_severity: str,
        dandruff_severity: str,
        lifestyle_score: float,
        root_cause: Optional[str],
        hair_score: float,
    ) -> List[RiskFactor]:

        factors = []

        # Hairloss severity factor
        decay = SEVERITY_DECAY_RATE.get(hairloss_severity, 1.0)
        factors.append(RiskFactor(
            key         = "hairloss_severity",
            label       = "Hair Loss Severity",
            impact      = round(min(decay / 3.8 * 100, 100), 1),
            direction   = "worsening" if decay > 1.5 else ("stable" if decay > 0.8 else "improving"),
            description = f"Current severity: {hairloss_severity}. Contributing {decay:.1f} pts/month decay.",
        ))

        # Dandruff factor
        penalty = DANDRUFF_PENALTY.get(dandruff_severity, 0.2)
        factors.append(RiskFactor(
            key         = "dandruff",
            label       = "Scalp Dandruff",
            impact      = round(penalty / 0.55 * 100, 1),
            direction   = "worsening" if penalty > 0.3 else ("stable" if penalty > 0.1 else "improving"),
            description = f"Dandruff severity: {dandruff_severity}. Adds {penalty:.2f} pts/month to decay.",
        ))

        # Lifestyle factor
        bonus = _get_lifestyle_bonus(lifestyle_score)
        lifestyle_impact = abs(bonus) / 0.8 * 100
        factors.append(RiskFactor(
            key         = "lifestyle",
            label       = "Lifestyle Score",
            impact      = round(lifestyle_impact, 1),
            direction   = "improving" if bonus > 0.3 else ("stable" if bonus > -0.2 else "worsening"),
            description = f"Lifestyle score: {lifestyle_score:.0f}/100. Net monthly adjustment: {bonus:+.1f} pts.",
        ))

        # Current score baseline risk
        score_risk = max(0, (100 - hair_score) / 100 * 60)
        factors.append(RiskFactor(
            key         = "baseline_score",
            label       = "Current Health Baseline",
            impact      = round(score_risk, 1),
            direction   = "stable",
            description = f"Starting score of {hair_score:.0f} — lower baselines carry compounding risk.",
        ))

        # Root cause factor (if known)
        if root_cause:
            root_labels = {
                "stress":        ("Stress & Cortisol",    55, "High cortisol accelerates follicle miniaturisation."),
                "nutritional":   ("Nutritional Deficiency", 65, "Deficiencies in iron/B12/zinc impair regrowth cycles."),
                "hormonal":      ("Hormonal Imbalance",   70, "DHT elevation is a primary driver of follicle damage."),
                "scalp_health":  ("Scalp Health Issues",  50, "Inflammation disrupts follicle environment."),
                "genetic":       ("Genetic Predisposition", 80, "Hereditary factors compound all other risks."),
                "environmental": ("Environmental Damage",  45, "Pollution and UV exposure weaken hair structure."),
            }
            label, impact, desc = root_labels.get(
                root_cause,
                (root_cause.replace("_", " ").title(), 50, "Identified as primary root cause.")
            )
            factors.append(RiskFactor(
                key         = root_cause,
                label       = label,
                impact      = float(impact),
                direction   = "worsening",
                description = desc,
            ))

        # Sort by impact descending
        factors.sort(key=lambda f: f.impact, reverse=True)
        return factors

    # ── Milestone builder ─────────────────────────────────────────────────────

    def _build_milestones(
        self, scores: List[float], hairloss_severity: str
    ) -> List[Milestone]:

        milestones = []
        tier_transitions = {}

        prev_tier = _get_risk_tier(scores[0])[0]
        for m, score in enumerate(scores[1:], start=1):
            tier = _get_risk_tier(score)[0]
            if tier != prev_tier and tier not in tier_transitions:
                tier_transitions[tier] = m
                milestones.append(Milestone(
                    month       = m,
                    label       = f"Risk shifts to {tier.title()}",
                    description = (
                        f"Projected score drops to {score:.0f} by month {m}, "
                        f"entering {tier} risk territory."
                    ),
                    severity    = "danger" if tier in ("high", "critical") else "warning",
                ))
            prev_tier = tier

        # Fixed clinical milestones
        if hairloss_severity in ("moderate", "high", "severe", "very_severe"):
            milestones.append(Milestone(
                month       = 3,
                label       = "Recommended Check-in",
                description = "Schedule a dermatologist consultation to assess progression.",
                severity    = "info",
            ))

        if scores[6] < 50:
            milestones.append(Milestone(
                month       = 6,
                label       = "Critical Threshold at 6 Months",
                description = "Without intervention, score may fall below 50 — visible worsening likely.",
                severity    = "danger",
            ))

        milestones.sort(key=lambda m: m.month)
        return milestones

    # ── Summary string ────────────────────────────────────────────────────────

    @staticmethod
    def _timeline_summary(
        current: float, proj_3m: float, proj_6m: float, proj_12m: float
    ) -> str:
        delta_12 = proj_12m - current

        if delta_12 >= 5:
            return "Trajectory is improving — keep up your routine."
        if delta_12 >= -3:
            return "Stable trajectory over 12 months — maintenance is key."
        if delta_12 >= -10:
            return "Moderate decline expected over 12 months without intervention."
        if delta_12 >= -20:
            return "Significant decline projected — early intervention recommended."
        return "High risk of rapid worsening — immediate action advised."