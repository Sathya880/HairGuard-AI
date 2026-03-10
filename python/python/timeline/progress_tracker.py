"""
Hair Progress Tracker Engine
Compares previous and current scan results to show hair health improvement
"""

from typing import Dict


class ProgressTrackerEngine:
    """
    Tracks hair health progress between scans.
    Used for demo visualization instead of long-term forecasting.
    """

    def track_progress(
        self,
        previous_hair_score: int,
        current_hair_score: int,
        previous_dandruff_severity: str,
        current_dandruff_severity: str,
    ) -> Dict:
        """
        Compare previous and current hair analysis results

        Returns:
            progress_percent
            hair_trend
            dandruff_trend
        """

        # Hair score change
        score_change = current_hair_score - previous_hair_score

        if score_change > 0:
            hair_trend = "Improved"
        elif score_change < 0:
            hair_trend = "Worsened"
        else:
            hair_trend = "Stable"

        # Dandruff severity ranking
        severity_rank = {
            "none": 0,
            "low": 1,
            "mild": 2,
            "moderate": 3,
            "high": 4,
            "severe": 5
        }

        prev_rank = severity_rank.get(previous_dandruff_severity.lower(), 2)
        curr_rank = severity_rank.get(current_dandruff_severity.lower(), 2)

        if curr_rank < prev_rank:
            dandruff_trend = "Improved"
        elif curr_rank > prev_rank:
            dandruff_trend = "Worsened"
        else:
            dandruff_trend = "Stable"

        return {
            "previous_hair_score": previous_hair_score,
            "current_hair_score": current_hair_score,
            "score_change": score_change,
            "hair_trend": hair_trend,
            "dandruff_trend": dandruff_trend
        }


def create_progress_tracker() -> ProgressTrackerEngine:
    return ProgressTrackerEngine()


if __name__ == "__main__":

    tracker = ProgressTrackerEngine()

    result = tracker.track_progress(
        previous_hair_score=55,
        current_hair_score=68,
        previous_dandruff_severity="moderate",
        current_dandruff_severity="mild"
    )

    print("Hair Progress Report")
    print("Previous Score:", result["previous_hair_score"])
    print("Current Score:", result["current_hair_score"])
    print("Score Change:", result["score_change"])
    print("Hair Trend:", result["hair_trend"])
    print("Dandruff Trend:", result["dandruff_trend"])