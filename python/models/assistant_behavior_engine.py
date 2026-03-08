"""
Assistant Behavior Engine
Generates coaching-style messages, detects inconsistencies and stagnation
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta


class AssistantBehaviorEngine:
    """
    Generates personalized coaching messages, detects patterns in user behavior,
    and provides accountability-based messaging for hair care routines.
    """

    def __init__(self):
        # Inconsistency detection thresholds
        self.inconsistency_thresholds = {
            "routine_missed_days": 3,
            "score_variance": 20,
            "streak_broken": True,
        }

        # Stagnation detection
        self.stagnation_thresholds = {
            "weeks_no_change": 4,
            "score_change_min": 2,
        }

        # Coaching message templates
        self.motivation_messages = {
            "great_progress": [
                "Amazing progress! You're doing fantastic. Keep up the great work! 💪",
                "Your dedication is paying off! Those consistent efforts are showing results.",
                "We're seeing real improvement here! You should be proud of your commitment.",
            ],
            "good_progress": [
                "Good progress! You're on the right track. Every small step counts!",
                "Nice improvement! Keep following your routine and you'll see even more results.",
                "You're making progress! Stay consistent and the results will keep coming.",
            ],
            "maintaining": [
                "You're holding steady! Consistency is key to maintaining your gains.",
                "Nice work maintaining your routine. The key now is small improvements.",
                "You're doing well to stay consistent. Let's push for that next improvement!",
            ],
            "needs_effort": [
                "Time to refocus! Your hair needs your commitment right now.",
                "Let's get back on track! Your future self will thank you for the effort.",
                "We can do this! One day at a time, let's rebuild that routine.",
            ],
            "struggling": [
                "It's okay to have setbacks. What matters is getting back on track.",
                "Let's restart fresh today. Small steps lead to big changes.",
                "Every expert was once a beginner. Let's take it one task at a time.",
            ],
        }

        # Accountability messages
        self.accountability_messages = [
            "I notice you missed your routine yesterday. Let's make today count!",
            "Your streak is important - let's protect that progress today!",
            "I see the routine adherence has been inconsistent. What's getting in the way?",
            "Let's check in: How can I help you stay on track this week?",
            "Accountability partner alert! You've got this - let's do this together!",
        ]

        # Specific coaching messages
        self.coaching_templates = {
            "sleep_improvement": [
                "Sleep is when your body repairs! Try to get 7-8 hours for optimal hair growth.",
                "Your sleep patterns affect cortisol levels which impact hair health. Prioritize rest!",
            ],
            "diet_improvement": [
                "Hair is made of protein! Make sure you're getting enough lean protein daily.",
                "Those vitamins are working from the inside out. Keep up the healthy eating!",
            ],
            "stress_reduction": [
                "Stress shows in your hair! Try incorporating 5 minutes of meditation daily.",
                "Your stress management is improving! Lower cortisol means happier hair follicles.",
            ],
            "routine_consistency": [
                "Consistency beats intensity! Small daily actions lead to big results.",
                "Your routine is your hair's best friend. Stick with it!",
            ],
        }

    def analyze_behavior(
        self,
        current_report: Dict,
        previous_reports: List[Dict],
        routine_adherence: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        Analyze user behavior and generate coaching messages

        Args:
            current_report: Current hair analysis report
            previous_reports: List of previous reports
            routine_adherence: Optional list of routine completion data

        Returns:
            Dictionary with coaching messages and detected patterns
        """

        # Detect inconsistencies
        inconsistencies = self._detect_inconsistencies(
            previous_reports, routine_adherence
        )

        # Detect stagnation
        stagnation = self._detect_stagnation(previous_reports)

        # Determine progress status
        progress_status = self._evaluate_progress(current_report, previous_reports)

        # Generate main coaching message
        main_message = self._generate_main_message(
            progress_status, inconsistencies, stagnation
        )

        # Generate specific recommendations
        recommendations = self._generate_recommendations(
            current_report, progress_status, inconsistencies
        )

        return {
            "main_message": main_message,
            "progress_status": progress_status,
            "inconsistencies_detected": inconsistencies,
            "stagnation_detected": stagnation,
            "recommendations": recommendations,
            "urgency_level": self._determine_urgency(inconsistencies, stagnation),
            "accountability_message": (
                self._get_accountability_message(routine_adherence)
                if routine_adherence
                else None
            ),
        }

    def _detect_inconsistencies(
        self, previous_reports: List[Dict], routine_adherence: Optional[List[Dict]]
    ) -> List[Dict]:
        """Detect inconsistencies in user behavior"""

        inconsistencies = []

        # Check routine adherence if available
        if routine_adherence:
            recent = routine_adherence[-7:]  # Last 7 days

            missed_days = sum(1 for day in recent if not day.get("completed", False))

            if missed_days >= self.inconsistency_thresholds["routine_missed_days"]:
                inconsistencies.append(
                    {
                        "type": "routine_missed",
                        "severity": "high" if missed_days >= 5 else "medium",
                        "details": f"Missed {missed_days} of last 7 days",
                    }
                )

        # Check score variance
        if len(previous_reports) >= 3:
            scores = [
                r.get("health", {}).get("score", 50) for r in previous_reports[-5:]
            ]

            if scores:
                score_range = max(scores) - min(scores)

                if score_range > self.inconsistency_thresholds["score_variance"]:
                    inconsistencies.append(
                        {
                            "type": "score_variance",
                            "severity": "medium",
                            "details": f"Score fluctuated by {score_range} points recently",
                        }
                    )

        return inconsistencies

    def _detect_stagnation(self, previous_reports: List[Dict]) -> Dict:
        """Detect if user is in a stagnation period"""

        if len(previous_reports) < 3:
            return {"detected": False, "reason": "insufficient_data"}

        # Get recent scores
        recent_scores = [
            r.get("health", {}).get("score", 50)
            for r in previous_reports[-6:]  # Last 6 reports
        ]

        if len(recent_scores) < 3:
            return {"detected": False, "reason": "insufficient_data"}

        # Check if scores are essentially unchanged
        max_change = max(recent_scores) - min(recent_scores)

        if max_change <= self.stagnation_thresholds["score_change_min"]:
            return {
                "detected": True,
                "weeks_without_change": len(recent_scores)
                * 2,  # Assuming bi-weekly reports
                "severity": "high" if len(recent_scores) >= 5 else "medium",
            }

        return {"detected": False}

    def _evaluate_progress(
        self, current_report: Dict, previous_reports: List[Dict]
    ) -> str:
        """Evaluate current progress status"""

        current_score = current_report.get("health", {}).get("score", 50)

        if not previous_reports:
            return "new_user"

        # Compare with most recent previous report
        last_score = previous_reports[-1].get("health", {}).get("score", 50)

        diff = current_score - last_score

        if diff > 5:
            return "great_progress"
        elif diff > 0:
            return "good_progress"
        elif diff == 0:
            return "maintaining"
        elif diff > -5:
            return "needs_effort"
        else:
            return "struggling"

    def _generate_main_message(
        self, progress_status: str, inconsistencies: List[Dict], stagnation: Dict
    ) -> str:
        """Generate main coaching message"""

        # Get base message from templates
        messages = self.motivation_messages.get(
            progress_status, self.motivation_messages["maintaining"]
        )

        base_message = messages[0]  # Get first message as default

        # Add specific context if issues detected
        if stagnation.get("detected"):
            weeks = stagnation.get("weeks_without_change", 0)
            if weeks >= 4:
                base_message += (
                    " We've seen minimal change in "
                    + str(weeks)
                    + " weeks - let's try adjusting your approach."
                )

        if any(inc.get("type") == "routine_missed" for inc in inconsistencies):
            base_message += " I noticed some routine days were missed recently."

        return base_message

    def _generate_recommendations(
        self, current_report: Dict, progress_status: str, inconsistencies: List[Dict]
    ) -> List[str]:
        """Generate specific recommendations"""

        recommendations = []

        # Get root cause from report
        root_cause = current_report.get("rootCause", {}).get("primary", "")

        # Add cause-specific coaching
        if root_cause:
            cause_lower = root_cause.lower()

            if "stress" in cause_lower:
                recommendations.extend(self.coaching_templates["stress_reduction"][:1])

            if "nutrition" in cause_lower or "deficiency" in cause_lower:
                recommendations.extend(self.coaching_templates["diet_improvement"][:1])

        # Add progress-specific recommendations
        if progress_status in ["needs_effort", "struggling"]:
            recommendations.append(
                "Let's start with just one task today. Building momentum is key!"
            )

        # Add general recommendation if none yet
        if not recommendations:
            recommendations.append(
                "Consistency is your superpower! Keep following your routine daily."
            )

        return recommendations

    def _determine_urgency(self, inconsistencies: List[Dict], stagnation: Dict) -> str:
        """Determine urgency level of response needed"""

        # Check for high severity issues
        if any(inc.get("severity") == "high" for inc in inconsistencies):
            return "high"

        if stagnation.get("detected") and stagnation.get("severity") == "high":
            return "high"

        if any(inc.get("severity") == "medium" for inc in inconsistencies):
            return "medium"

        return "low"

    def _get_accountability_message(self, routine_adherence: List[Dict]) -> str:
        """Generate accountability-focused message"""

        if not routine_adherence:
            return ""

        # Get most recent completion rate
        recent = routine_adherence[-14:]  # Last 2 weeks

        completed = sum(1 for day in recent if day.get("completed", False))

        if completed < len(recent) * 0.5:
            return self.accountability_messages[0]  # Missed message
        elif completed < len(recent) * 0.75:
            return self.accountibility_messages[2]  # Inconsistent message

        return self.accountability_messages[4]  # Encouraging message

    def generate_checkin_message(
        self, days_since_last: int, current_streak: int
    ) -> str:
        """Generate a check-in message based on time since last activity"""

        if days_since_last == 0:
            return "Great to see you today! Let's keep that momentum going! 💪"
        elif days_since_last == 1:
            return (
                "Welcome back! Missing one day is okay - let's get back on track today!"
            )
        elif days_since_last <= 3:
            return "We've missed you! Your hair routine awaits. Let's restart together!"
        elif days_since_last <= 7:
            return "It's been a week! Let's reconnect with your hair care routine. You've got this!"
        else:
            return f"Welcome back! Your {current_streak} streak is waiting to be rebuilt. Let's start fresh!"


def create_assistant_behavior_engine() -> AssistantBehaviorEngine:
    """Factory function to create AssistantBehaviorEngine instance"""
    return AssistantBehaviorEngine()


if __name__ == "__main__":
    engine = AssistantBehaviorEngine()

    # Test behavior analysis
    current = {"health": {"score": 65}, "rootCause": {"primary": "Scalp Inflammation"}}

    previous = [
        {"health": {"score": 60}},
        {"health": {"score": 62}},
        {"health": {"score": 65}},
    ]

    result = engine.analyze_behavior(current, previous)

    print("Assistant Behavior Analysis:")
    print(f"  Status: {result['progress_status']}")
    print(f"  Message: {result['main_message']}")
    print(f"  Urgency: {result['urgency_level']}")
