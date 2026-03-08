"""
Context Builder Module

Builds AssistantContext from user data.
Handles ALL incoming report formats:
  - Trimmed:  { hairScore, lifestyleScore, hairSeverity, dandruffSeverity }
  - Full:     { health: {score}, lifestyle: {overallScore}, hairloss: {overallSeverity}, ... }
  - Legacy:   { hair_score, lifestyle_score }
"""

from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any, List

TrendType = Literal["improving", "worsening", "stable"]
DataStrengthType = Literal["strong", "moderate", "weak"]


# =====================================================
# REPORT FIELD NORMALIZER
# =====================================================


def _extract_hair_score(report: Dict[str, Any]) -> float:
    """
    Extract hair score from any report format.

    Priority order:
    1. report['health']['score']          ← full report format
    2. report['hairScore']                ← trimmed camelCase format
    3. report['hair_score']               ← snake_case legacy
    4. 50.0                               ← safe default
    """
    health = report.get("health")
    if isinstance(health, dict):
        score = health.get("score")
        if score is not None:
            return float(score)

    for key in ("hairScore", "hair_score", "hairHealthScore", "score"):
        val = report.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass

    return 50.0


def _extract_lifestyle_score(report: Dict[str, Any]) -> float:
    """
    Extract lifestyle score from any report format.

    Priority order:
    1. report['lifestyle']['overallScore']
    2. report['lifestyle']['score']
    3. report['lifestyleScore']
    4. report['lifestyle_score']
    5. 50.0
    """
    lifestyle = report.get("lifestyle")
    if isinstance(lifestyle, dict):
        for key in ("overallScore", "score", "overall_score"):
            val = lifestyle.get(key)
            if val is not None:
                try:
                    return float(val)
                except (TypeError, ValueError):
                    pass

    for key in ("lifestyleScore", "lifestyle_score"):
        val = report.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass

    return 50.0


def _extract_hairloss_severity(report: Dict[str, Any]) -> str:
    """Extract hair loss severity from any report format."""
    hairloss = report.get("hairloss")
    if isinstance(hairloss, dict):
        sev = hairloss.get("overallSeverity") or hairloss.get("severity")
        if sev:
            return str(sev)

    for key in (
        "hairSeverity",
        "hair_severity",
        "hairlossSeverity",
        "hairloss_severity",
    ):
        val = report.get(key)
        if val:
            return str(val)

    return "unknown"


def _extract_dandruff_severity(report: Dict[str, Any]) -> str:
    """Extract dandruff severity from any report format."""
    dandruff = report.get("dandruff")
    if isinstance(dandruff, dict):
        sev = dandruff.get("severity")
        if sev:
            return str(sev)

    for key in ("dandruffSeverity", "dandruff_severity"):
        val = report.get(key)
        if val:
            return str(val)

    return "unknown"


def _extract_root_cause(
    report: Dict[str, Any], root_cause_result: Dict[str, Any]
) -> Optional[str]:
    """Extract primary root cause from report or separate root_cause_result dict."""
    if root_cause_result:
        for key in ("root_cause", "primary_cause", "primary"):
            val = root_cause_result.get(key)
            if val:
                return str(val)

    rc = report.get("rootCause")
    if isinstance(rc, dict):
        for key in ("primary", "primary_cause", "root_cause"):
            val = rc.get(key)
            if val:
                return str(val)

    return None


# =====================================================
# CONTEXT BUILDER
# =====================================================


class AssistantContextBuilder:
    """
    Builder for constructing AssistantContext from user data.
    Handles all report formats from Node.js / Flutter.
    """

    IMPROVING_THRESHOLD = 2.0
    WORSENING_THRESHOLD = -2.0
    DATA_STRONG_THRESHOLD = 5
    DATA_MODERATE_THRESHOLD = 2

    def __init__(
        self,
        user_reports: Optional[List[Dict[str, Any]]] = None,
        routine_adherence_data: Optional[Dict[str, Any]] = None,
        lifestyle_score_trend: Optional[Dict[str, Any]] = None,
        root_cause_result: Optional[Dict[str, Any]] = None,
        progress_result: Optional[Dict[str, Any]] = None,
    ):
        self.user_reports = user_reports or []
        self.routine_adherence_data = routine_adherence_data or {}
        self.lifestyle_score_trend = lifestyle_score_trend or {}
        self.root_cause_result = root_cause_result or {}
        self.progress_result = progress_result or {}

    def build(self):
        """Build and return the assistant context."""
        from .state_classifier import AssistantContext

        hair_score = self._compute_hair_score()
        previous_score = self._compute_previous_score()
        trend = self._compute_trend(hair_score, previous_score)
        reports_count = len(self.user_reports)
        root_cause = self._compute_root_cause()
        confidence = self._compute_confidence(reports_count)
        data_strength = self._compute_data_strength(reports_count)
        risk_6_month = self._compute_risk_6_month(hair_score)
        routine_adherence = self._compute_routine_adherence()
        lifestyle_score = self._compute_lifestyle_score()

        latest = self.user_reports[0] if self.user_reports else {}
        dandruff_severity = _extract_dandruff_severity(latest)
        hairloss_severity = _extract_hairloss_severity(latest)

        return AssistantContext(
            hair_score=hair_score,
            previous_score=previous_score,
            routine_adherence=routine_adherence,
            risk_6_month=risk_6_month,
            trend=trend,
            reports_count=reports_count,
            confidence=confidence,
            data_strength=data_strength,
            root_cause=root_cause,
            dandruff_severity=dandruff_severity,
            hairloss_severity=hairloss_severity,
            lifestyle_score=lifestyle_score,
        )

    def _compute_hair_score(self) -> float:
        if not self.user_reports:
            return 50.0
        sorted_reports = sorted(
            self.user_reports,
            key=lambda r: r.get("createdAt", r.get("created_at", "")),
            reverse=True,
        )
        return _extract_hair_score(sorted_reports[0])

    def _compute_previous_score(self) -> float:
        if len(self.user_reports) < 2:
            return self._compute_hair_score()
        sorted_reports = sorted(
            self.user_reports,
            key=lambda r: r.get("createdAt", r.get("created_at", "")),
            reverse=True,
        )
        return _extract_hair_score(sorted_reports[1])

    def _compute_trend(self, hair_score: float, previous_score: float) -> str:
        # Progress tracker result takes priority if available
        if self.progress_result:
            trend = self.progress_result.get("hair_trend")
            if trend == "Improved":
                return "improving"
            elif trend == "Worsened":
                return "worsening"
            elif trend == "Stable":
                return "stable"

        delta = hair_score - previous_score

        if delta >= self.IMPROVING_THRESHOLD:
            return "improving"
        elif delta <= self.WORSENING_THRESHOLD:
            return "worsening"

        return "stable"

    def _compute_root_cause(self) -> Optional[str]:
        latest = self.user_reports[0] if self.user_reports else {}
        return _extract_root_cause(latest, self.root_cause_result)

    def _compute_confidence(self, reports_count: int) -> float:
        if reports_count >= 5:
            base = 90.0
        elif reports_count >= 3:
            base = 75.0
        elif reports_count >= 1:
            base = 60.0
        else:
            base = 30.0

        if self.routine_adherence_data:
            base = min(95.0, base + 5)
        if self.lifestyle_score_trend:
            base = min(95.0, base + 5)
        return base

    def _compute_data_strength(self, reports_count: int) -> str:
        if reports_count >= self.DATA_STRONG_THRESHOLD:
            return "strong"
        elif reports_count >= self.DATA_MODERATE_THRESHOLD:
            return "moderate"
        return "weak"

    def _compute_risk_6_month(self, hair_score: float) -> float:
        """Estimate 6-month risk as inverse of hair score, scaled."""
        return max(0.0, min(100.0, (100.0 - hair_score) * 0.8))

    def _compute_routine_adherence(self) -> float:
        if not self.routine_adherence_data:
            return 50.0
        adherence = self.routine_adherence_data.get("adherence_percentage")
        if adherence is not None:
            return float(adherence)
        completed = self.routine_adherence_data.get("completed", 0)
        total = self.routine_adherence_data.get("total", 1)
        if total > 0:
            return float((completed / total) * 100)
        return 50.0

    def _compute_lifestyle_score(self) -> float:
        if not self.user_reports:
            return 50.0
        latest = self.user_reports[0]
        return _extract_lifestyle_score(latest)

    def to_dict(self) -> Dict[str, Any]:
        context = self.build()
        return {
            "hair_score": context.hair_score,
            "previous_score": context.previous_score,
            "routine_adherence": context.routine_adherence,
            "trend": context.trend,
            "reports_count": context.reports_count,
            "confidence": context.confidence,
            "data_strength": context.data_strength,
            "root_cause": context.root_cause,
            "dandruff_severity": context.dandruff_severity,
            "hairloss_severity": context.hairloss_severity,
            "lifestyle_score": context.lifestyle_score,
        }


# =====================================================
# CONVENIENCE FUNCTION
# =====================================================


def build_assistant_context(
    user_reports=None,
    routine_adherence_data=None,
    lifestyle_score_trend=None,
    root_cause_result=None,
    progress_result=None,
):
    builder = AssistantContextBuilder(
        user_reports=user_reports,
        routine_adherence_data=routine_adherence_data,
        lifestyle_score_trend=lifestyle_score_trend,
        root_cause_result=root_cause_result,
        progress_result=progress_result,
    )
    return builder.build()