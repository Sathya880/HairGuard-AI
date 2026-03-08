class HairScoreAnalyzer:

    def analyze(self, score):
        if score >= 75:
            category = "Good"
        elif score >= 50:
            category = "Moderate"
        else:
            category = "Poor"

        return {
            "score": score,
            "condition": category
        }
