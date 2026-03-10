"""
State Classifier Module

Classifies user state using hair score progress,
routine adherence, and data confidence.
"""

from dataclasses import dataclass
from typing import Literal, Optional


TrendType = Literal["improving", "worsening", "stable"]
DataStrengthType = Literal["strong", "moderate", "weak"]

StateType = Literal[
    "improving",
    "plateau",
    "declining",
    "low_discipline",
    "uncertain",
    "neutral",
]


@dataclass
class AssistantContext:
    """
    Context data used by the assistant state classifier.
    """

    hair_score: float
    previous_score: float
    routine_adherence: float
    trend: TrendType
    reports_count: int
    confidence: float
    data_strength: DataStrengthType
    risk_6_month: float = 0.0
    root_cause: Optional[str] = None
    # Extended fields used by coaching engine
    dandruff_severity: Optional[str] = None
    hairloss_severity: Optional[str] = None
    lifestyle_score: Optional[float] = None


class StateClassifier:
    """
    Classifies the user's state based on hair progress and adherence.
    """

    PRIORITY_RULES = [
        "_check_low_discipline",
        "_check_declining",
        "_check_improving",
        "_check_plateau",
        "_check_uncertain",
    ]

    def __init__(self, context: AssistantContext):
        self.context = context
        self.score_change = context.hair_score - context.previous_score

    def classify(self) -> StateType:
        """
        Apply classification rules in priority order.
        """

        for rule_method in self.PRIORITY_RULES:
            state = getattr(self, rule_method)()
            if state:
                return state

        return "neutral"

    # -------------------------------------------------

    def _check_low_discipline(self) -> Optional[StateType]:
        """
        Low routine adherence.
        """
        if self.context.routine_adherence < 40:
            return "low_discipline"
        return None

    def _check_declining(self) -> Optional[StateType]:
        """
        Detect declining hair health.
        """
        if self.context.trend == "worsening":
            return "declining"

        if self.score_change <= -5:
            return "declining"

        return None

    def _check_improving(self) -> Optional[StateType]:
        """
        Detect improvement trend.
        """
        if self.context.trend == "improving" and self.context.routine_adherence >= 60:
            return "improving"

        if self.score_change >= 5:
            return "improving"

        return None

    def _check_plateau(self) -> Optional[StateType]:
        """
        Plateau detection.
        """
        if self.context.trend == "stable" and self.context.reports_count >= 3:
            return "plateau"

        return None

    def _check_uncertain(self) -> Optional[StateType]:
        """
        Weak or unreliable data.
        """
        if self.context.confidence < 50:
            return "uncertain"

        if self.context.data_strength == "weak":
            return "uncertain"

        return None


def classify_state(context: AssistantContext) -> StateType:
    """
    Convenience wrapper.
    """
    classifier = StateClassifier(context)
    return classifier.classify()