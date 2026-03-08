import numpy as np


class LifestyleAnalyzer:

    def __init__(self):

        self.feature_order = [
            "hair_wash",
            "shampoo_type",
            "heat_styling",
            "helmet_usage",
            "scalp_sweat",
            "diet",
            "sleep",
            "stress",
            "water_type",
            "family_history",
            "problem_duration",
        ]

    # -----------------------------------------------------
    # Feature Encoding (unchanged)
    # -----------------------------------------------------
    def _encode_feature(self, factor, answer):

        answer = str(answer).lower()

        if factor == "hair_wash":
            if "daily" in answer:
                return 0.9
            if "2" in answer:
                return 0.7
            if "once" in answer:
                return 0.4
            return 0.2

        if factor == "shampoo_type":
            if "herbal" in answer:
                return 0.9
            if "anti" in answer:
                return 0.8
            if "change" in answer:
                return 0.4
            return 0.5

        if factor == "heat_styling":
            if "every day" in answer:
                return 0.2
            if "2" in answer:
                return 0.5
            if "rarely" in answer:
                return 0.8
            return 0.9

        if factor == "helmet_usage":
            if "daily" in answer:
                return 0.4
            if "occasionally" in answer:
                return 0.6
            if "rarely" in answer:
                return 0.8
            return 0.9

        if factor == "scalp_sweat":
            if "a lot" in answer:
                return 0.3
            if "moderate" in answer:
                return 0.6
            if "little" in answer:
                return 0.8
            return 0.5

        if factor == "diet":
            if "balanced" in answer:
                return 0.9
            if "home" in answer:
                return 0.7
            if "fast" in answer:
                return 0.3
            return 0.2

        if factor == "sleep":
            if "7" in answer or "8" in answer:
                return 0.9
            if "6" in answer:
                return 0.6
            return 0.3

        if factor == "stress":
            if "very high" in answer:
                return 0.2
            if "moderate" in answer:
                return 0.5
            if "low" in answer:
                return 0.8
            return 0.9

        if factor == "water_type":
            if "hard" in answer:
                return 0.3
            if "filtered" in answer:
                return 0.9
            return 0.6

        if factor == "family_history":
            if "yes" in answer:
                return 0.3
            if "no" in answer:
                return 0.9
            return 0.5

        if factor == "problem_duration":
            if "year" in answer:
                return 0.3
            if "6" in answer:
                return 0.5
            if "2" in answer:
                return 0.7
            return 0.9

        return 0.5

    # -----------------------------------------------------
    # Analyze (Corrected)
    # -----------------------------------------------------
    def analyze(self, flashcard_answers):

        if not isinstance(flashcard_answers, dict):
            flashcard_answers = {}

        factor_map = {
            "1": "hair_wash",
            "2": "shampoo_type",
            "3": "heat_styling",
            "4": "helmet_usage",
            "5": "scalp_sweat",
            "6": "diet",
            "7": "sleep",
            "8": "stress",
            "9": "water_type",
            "10": "family_history",
            "11": "problem_duration",
        }

        encoded_features = []
        detailed_scores = {}

        for key, factor in factor_map.items():
            value = flashcard_answers.get(key, "")
            encoded = self._encode_feature(factor, value)
            encoded_features.append(encoded)
            detailed_scores[factor] = int(encoded * 100)

        # Overall lifestyle score
        overall_score = int(np.mean(encoded_features) * 100)

        # Overall risk probability (0-1)
        overall_risk_probability = round(1 - np.mean(encoded_features), 3)

        # Risk severity
        if overall_risk_probability >= 0.66:
            severity = "high"
        elif overall_risk_probability >= 0.4:
            severity = "moderate"
        else:
            severity = "low"

        priority_areas = [
            factor for factor, score in detailed_scores.items()
            if score < 60
        ]

        return {
            "overall_score": overall_score,
            "severity": severity,
            "overall_risk_probability": overall_risk_probability,
            "priority_areas": priority_areas,
            "feature_scores": detailed_scores,
        }