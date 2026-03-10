"""
Weekly Review Engine Module

This module provides the WeeklyReviewEngine class for generating
weekly review summaries. Suitable for scheduled cron execution.
"""

from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any, List
from datetime import datetime, timedelta

# Import from existing modules
from .state_classifier import AssistantContext


# Type definitions
WeeklyTrendType = Literal["improvement", "stagnation", "decline"]
ToneType = Literal["celebratory", "neutral", "concerned"]


@dataclass
class WeeklyAdherenceStats:
    """Weekly adherence statistics."""

    current_adherence: float
    previous_adherence: float
    change: float
    trend: str  # "improving", "declining", "stable"


@dataclass
class WeeklyReview:
    """Structured weekly review object."""

    week_start_date: str
    week_end_date: str
    hair_score_current: float
    hair_score_previous: float
    hair_score_change: float
    weekly_trend: WeeklyTrendType
    adherence_stats: WeeklyAdherenceStats
    summary_message: str
    tone: ToneType
    priority: str
    generated_at: str


class WeeklyReviewEngine:
    """
    Engine for generating weekly review summaries.

    Designed for scheduled cron execution. Analyzes weekly changes
    in hair score and adherence to generate summary coaching.
    """

    # Thresholds for trend detection
    IMPROVEMENT_THRESHOLD = 1.0  # Score change >= 1% = improvement
    DECLINE_THRESHOLD = -1.0  # Score change <= -1% = decline

    # Thresholds for adherence change
    ADHERENCE_IMPROVEMENT = 5.0  # 5% improvement
    ADHERENCE_DECLINE = -5.0  # 5% decline

    def __init__(self):
        """Initialize the WeeklyReviewEngine."""
        pass

    def generate_review(
        self,
        current_context: AssistantContext,
        previous_context: AssistantContext,
        week_start: Optional[datetime] = None,
        week_end: Optional[datetime] = None,
    ) -> WeeklyReview:
        """
        Generate a weekly review.

        Args:
            current_context: Most recent assistant context
            previous_context: Previous assistant context (from last week)
            week_start: Start of the week (defaults to 7 days ago)
            week_end: End of the week (defaults to today)

        Returns:
            WeeklyReview: Structured weekly review
        """
        # Set default dates if not provided
        if week_end is None:
            week_end = datetime.now()
        if week_start is None:
            week_start = week_end - timedelta(days=7)

        # Calculate hair score change
        hair_score_change = current_context.hair_score - previous_context.hair_score

        # Determine weekly trend
        weekly_trend = self._detect_weekly_trend(hair_score_change)

        # Calculate adherence change
        adherence_change = (
            current_context.routine_adherence - previous_context.routine_adherence
        )

        adherence_trend = self._detect_adherence_trend(adherence_change)

        adherence_stats = WeeklyAdherenceStats(
            current_adherence=current_context.routine_adherence,
            previous_adherence=previous_context.routine_adherence,
            change=adherence_change,
            trend=adherence_trend,
        )

        # Generate summary message
        summary_message = self._generate_summary_message(
            weekly_trend=weekly_trend,
            hair_score_change=hair_score_change,
            current_score=current_context.hair_score,
            adherence_stats=adherence_stats,
            context=current_context,
        )

        # Determine tone and priority
        tone = self._determine_tone(weekly_trend)
        priority = self._determine_priority(weekly_trend, adherence_stats)

        return WeeklyReview(
            week_start_date=week_start.strftime("%Y-%m-%d"),
            week_end_date=week_end.strftime("%Y-%m-%d"),
            hair_score_current=current_context.hair_score,
            hair_score_previous=previous_context.hair_score,
            hair_score_change=hair_score_change,
            weekly_trend=weekly_trend,
            adherence_stats=adherence_stats,
            summary_message=summary_message,
            tone=tone,
            priority=priority,
            generated_at=datetime.now().isoformat(),
        )

    def _detect_weekly_trend(self, score_change: float) -> WeeklyTrendType:
        """
        Detect weekly trend based on score change.

        Args:
            score_change: Change in hair score

        Returns:
            WeeklyTrendType: Detected trend
        """
        if score_change >= self.IMPROVEMENT_THRESHOLD:
            return "improvement"
        elif score_change <= self.DECLINE_THRESHOLD:
            return "decline"
        else:
            return "stagnation"

    def _detect_adherence_trend(self, adherence_change: float) -> str:
        """
        Detect adherence trend.

        Args:
            adherence_change: Change in adherence

        Returns:
            str: Adherence trend
        """
        if adherence_change >= self.ADHERENCE_IMPROVEMENT:
            return "improving"
        elif adherence_change <= self.ADHERENCE_DECLINE:
            return "declining"
        else:
            return "stable"

    def _generate_summary_message(
        self,
        weekly_trend: WeeklyTrendType,
        hair_score_change: float,
        current_score: float,
        adherence_stats: WeeklyAdherenceStats,
        context: AssistantContext,
    ) -> str:
        """
        Generate summary coaching message.

        Args:
            weekly_trend: Detected weekly trend
            hair_score_change: Score change
            current_score: Current hair score
            adherence_stats: Adherence statistics
            context: Assistant context

        Returns:
            str: Summary message
        """
        if weekly_trend == "improvement":
            return (
                f"Weekly Progress: +{hair_score_change:+.1f} points. "
                f"Hair score now at {current_score:.1f}. "
                f"Adherence {adherence_stats.trend} at {adherence_stats.current_adherence:.1f}%. "
                f"Your consistent routine is paying off. "
                f"Keep maintaining this momentum."
            )
        elif weekly_trend == "decline":
            return (
                f"Weekly Alert: {hair_score_change:+.1f} points. "
                f"Hair score now at {current_score:.1f}. "
                f"Adherence {adherence_stats.trend} at {adherence_stats.current_adherence:.1f}%. "
                f"This week's results indicate regression. "
                f"Review your routine and identify what changed."
            )
        else:  # stagnation
            return (
                f"Weekly Summary: {hair_score_change:+.1f} points. "
                f"Hair score stable at {current_score:.1f}. "
                f"Adherence {adherence_stats.trend} at {adherence_stats.current_adherence:.1f}%. "
                f"Consider optimization strategies to break through "
                f"this plateau and accelerate progress."
            )

    def _determine_tone(self, weekly_trend: WeeklyTrendType) -> ToneType:
        """
        Determine tone based on trend.

        Args:
            weekly_trend: Detected weekly trend

        Returns:
            ToneType: Appropriate tone
        """
        tone_map = {
            "improvement": "celebratory",
            "decline": "concerned",
            "stagnation": "neutral",
        }
        return tone_map.get(weekly_trend, "neutral")

    def _determine_priority(
        self,
        weekly_trend: WeeklyTrendType,
        adherence_stats: WeeklyAdherenceStats,
    ) -> str:
        """
        Determine priority based on trend and adherence.

        Args:
            weekly_trend: Detected weekly trend
            adherence_stats: Adherence statistics

        Returns:
            str: Priority level
        """
        if weekly_trend == "decline":
            return "high"

        if adherence_stats.trend == "declining":
            return "medium"

        if weekly_trend == "improvement":
            return "low"

        return "medium"

    def generate_from_reports(
        self,
        current_week_reports: List[Dict[str, Any]],
        previous_week_reports: List[Dict[str, Any]],
        current_adherence: float,
        previous_adherence: float,
    ) -> WeeklyReview:
        """
        Generate review from raw report data.

        Args:
            current_week_reports: Reports from current week
            previous_week_reports: Reports from previous week
            current_adherence: Current week adherence
            previous_adherence: Previous week adherence

        Returns:
            WeeklyReview: Structured weekly review
        """
        # Calculate average scores
        current_score = self._calculate_average_score(current_week_reports)
        previous_score = self._calculate_average_score(previous_week_reports)

        # Create minimal context objects
        current_context = AssistantContext(
            hair_score=current_score,
            previous_score=previous_score,
            routine_adherence=current_adherence,
            risk_6_month=50.0,
            trend="stable",
            reports_count=len(current_week_reports),
            confidence=70.0,
            data_strength="moderate",
        )

        previous_context = AssistantContext(
            hair_score=previous_score,
            previous_score=previous_score,
            routine_adherence=previous_adherence,
            risk_6_month=50.0,
            trend="stable",
            reports_count=len(previous_week_reports),
            confidence=70.0,
            data_strength="moderate",
        )

        return self.generate_review(current_context, previous_context)

    def _calculate_average_score(self, reports: List[Dict[str, Any]]) -> float:
        """
        Calculate average hair score from reports.

        Args:
            reports: List of report dictionaries

        Returns:
            float: Average score
        """
        if not reports:
            return 50.0

        scores = [r.get("hair_score", 50.0) for r in reports]
        return sum(scores) / len(scores)

    def to_dict(self, review: WeeklyReview) -> Dict[str, Any]:
        """
        Convert review to dictionary.

        Args:
            review: WeeklyReview object

        Returns:
            Dict: Dictionary representation
        """
        return {
            "week_start_date": review.week_start_date,
            "week_end_date": review.week_end_date,
            "hair_score_current": review.hair_score_current,
            "hair_score_previous": review.hair_score_previous,
            "hair_score_change": review.hair_score_change,
            "weekly_trend": review.weekly_trend,
            "adherence_stats": {
                "current_adherence": review.adherence_stats.current_adherence,
                "previous_adherence": review.adherence_stats.previous_adherence,
                "change": review.adherence_stats.change,
                "trend": review.adherence_stats.trend,
            },
            "summary_message": review.summary_message,
            "tone": review.tone,
            "priority": review.priority,
            "generated_at": review.generated_at,
        }


def generate_weekly_review(
    current_context: AssistantContext,
    previous_context: AssistantContext,
) -> Dict[str, Any]:
    """
    Convenience function to generate weekly review.

    Args:
        current_context: Current assistant context
        previous_context: Previous assistant context

    Returns:
        Dict: Weekly review as dictionary
    """
    engine = WeeklyReviewEngine()
    review = engine.generate_review(current_context, previous_context)
    return engine.to_dict(review)