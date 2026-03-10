"""
Evidence Tips Engine
Provides categorized hair care tips with evidence levels and safety notes
"""

from typing import Dict, List


class EvidenceTipsEngine:
    """
    Generates categorized tips with evidence levels and safety notes
    for hair care based on severity and root cause.
    """

    def __init__(self):
        # Scientifically proven tips (strong evidence)
        self.scientifically_proven = {
            "general": [
                {
                    "tip": "Minoxidil is FDA-approved for treating male and female pattern baldness",
                    "evidence_level": "High",
                    "safety_note": "May cause initial shedding. Consult doctor before use. Not for pregnant women.",
                },
                {
                    "tip": "Finasteride effectively treats male pattern baldness by blocking DHT",
                    "evidence_level": "High",
                    "safety_note": "Prescription only. May cause sexual side effects. Not for women.",
                },
                {
                    "tip": "Low-level laser therapy (LLLT) promotes hair growth",
                    "evidence_level": "High",
                    "safety_note": "Use as directed. Avoid looking directly at lasers. Generally safe.",
                },
                {
                    "tip": "Protein intake is essential for hair structure",
                    "evidence_level": "High",
                    "safety_note": "Aim for 0.8g protein per kg body weight. Balance with overall diet.",
                },
            ],
            "scalp_health": [
                {
                    "tip": "Ketoconazole shampoo reduces scalp inflammation and DHT",
                    "evidence_level": "High",
                    "safety_note": "Use 2-3 times per week. May cause dryness. Rinse thoroughly.",
                },
                {
                    "tip": "Salicylic acid helps remove scalp scale and debris",
                    "evidence_level": "Medium-High",
                    "safety_note": "Can cause initial dryness. Start with lower concentrations.",
                },
            ],
            "nutrition": [
                {
                    "tip": "Iron deficiency is linked to hair loss",
                    "evidence_level": "High",
                    "safety_note": "Get blood test before supplementing. Excess iron is dangerous.",
                },
                {
                    "tip": "Vitamin D deficiency correlates with hair loss",
                    "evidence_level": "Medium-High",
                    "safety_note": "Test levels first. Don't exceed recommended daily dose.",
                },
                {
                    "tip": "Biotin supplements may help brittle nails more than hair",
                    "evidence_level": "Medium",
                    "safety_note": "Generally safe. May interfere with lab tests for heart issues.",
                },
            ],
        }

        # Clinically observed tips (moderate evidence)
        self.clinically_observed = {
            "general": [
                {
                    "tip": "Scalp massage increases blood flow and may stimulate growth",
                    "evidence_level": "Medium",
                    "safety_note": "Be gentle. Avoid aggressive massage on inflamed scalp.",
                },
                {
                    "tip": "Platelet-Rich Plasma (PRP) therapy shows promising results",
                    "evidence_level": "Medium",
                    "safety_note": "Requires multiple sessions. Results vary. Consult dermatologist.",
                },
                {
                    "tip": "Consistent routine yields better results than sporadic intensive care",
                    "evidence_level": "Medium",
                    "safety_note": "Be patient. Results take 3-6 months to appear.",
                },
            ],
            "scalp_care": [
                {
                    "tip": "Tea tree oil has anti-inflammatory properties",
                    "evidence_level": "Medium",
                    "safety_note": "Always dilute (5-10% in carrier oil). May cause allergic reaction.",
                },
                {
                    "tip": "Aloe vera soothes irritated scalp",
                    "evidence_level": "Medium",
                    "safety_note": "Patch test first. Pure gel preferred over products with additives.",
                },
            ],
            "lifestyle": [
                {
                    "tip": "Stress management correlates with improved hair health",
                    "evidence_level": "Medium",
                    "safety_note": "Find stress relief that works for you. Consistency matters.",
                },
                {
                    "tip": "Adequate sleep (7-9 hours) supports hair growth cycle",
                    "evidence_level": "Medium",
                    "safety_note": "Maintain consistent sleep schedule for best results.",
                },
            ],
        }

        # Traditional remedies (lower evidence, historical use)
        self.traditional = {
            "oils": [
                {
                    "tip": "Coconut oil penetrates hair shaft and reduces protein loss",
                    "evidence_level": "Low-Medium",
                    "safety_note": "Use in moderation. May weigh down fine hair. Warm before application.",
                },
                {
                    "tip": "Castor oil is traditionally used for hair growth",
                    "evidence_level": "Low-Medium",
                    "safety_note": "Can be sticky. Use sparingly. May cause buildup.",
                },
                {
                    "tip": "Rosemary oil may stimulate hair follicles",
                    "evidence_level": "Low-Medium",
                    "safety_note": "Always dilute. Avoid eyes. May cause irritation in some.",
                },
                {
                    "tip": "Onion juice applied topically may promote growth",
                    "evidence_level": "Low",
                    "safety_note": "Strong smell. Rinse thoroughly. Can cause irritation.",
                },
            ],
            "home_remedies": [
                {
                    "tip": "Aloe vera gel conditions and soothes scalp",
                    "evidence_level": "Low-Medium",
                    "safety_note": "Use fresh gel or pure commercial gel. Rinse after 30 minutes.",
                },
                {
                    "tip": "Egg masks provide protein for hair",
                    "evidence_level": "Low-Medium",
                    "safety_note": "Don't use on colored hair frequently. Rinse with cool water.",
                },
                {
                    "tip": "Apple cider vinegar rinse balances scalp pH",
                    "evidence_level": "Low-Medium",
                    "safety_note": "Dilute 1:1 with water. Don't use on damaged hair.",
                },
            ],
        }

        # Risky tips (use with caution)
        self.risky = [
            {
                "tip": "High-dose biotin can interfere with lab tests",
                "evidence_level": "High (for risk)",
                "safety_note": "WARNING: May mask vitamin B12 deficiency. Inform doctors before blood tests.",
            },
            {
                "tip": "Using unapproved hair growth products can cause harm",
                "evidence_level": "High (for risk)",
                "safety_note": "CAUTION: Only use FDA-approved products. Avoid online 'miracle' products.",
            },
            {
                "tip": "Essential oils must always be diluted",
                "evidence_level": "High (for risk)",
                "safety_note": "WARNING: Never apply undiluted essential oils to scalp. Can cause burns.",
            },
            {
                "tip": "Over-washing can strip natural oils",
                "evidence_level": "Medium (for risk)",
                "safety_note": "Washing daily may be too much for most people. Adjust to your scalp type.",
            },
            {
                "tip": "Tight hairstyles cause traction alopecia",
                "evidence_level": "High (for risk)",
                "safety_note": "CAUTION: Avoid tight ponytails, braids, and weaves. Give hair breaks.",
            },
        ]

    def generate(self, hair_severity: str, root_cause: str) -> Dict:
        """
        Generate categorized tips based on severity and root cause

        Args:
            hair_severity: Current hair loss severity
            root_cause: Primary root cause

        Returns:
            Dictionary with categorized tips:
            - scientifically_proven: List of tips with strong evidence
            - clinically_observed: List of tips with moderate evidence
            - traditional: List of traditional remedies
            - risky: List of tips requiring caution
        """

        # Select tips based on severity
        severity_category = self._get_severity_category(hair_severity)

        result = {
            "scientifically_proven": self._get_relevant_tips(
                self.scientifically_proven, root_cause, severity_category
            ),
            "clinically_observed": self._get_relevant_tips(
                self.clinically_observed, root_cause, severity_category
            ),
            "traditional": self._get_relevant_tips(
                self.traditional, root_cause, severity_category
            ),
            "risky": self._filter_risky_tips(severity_category),
        }

        # Add severity-specific warnings
        result["safety_warnings"] = self._get_severity_warnings(hair_severity)

        return result

    def _get_severity_category(self, severity: str) -> str:
        """Map severity to category"""
        severity = severity.lower()
        if severity in ["severe", "very_severe"]:
            return "high"
        elif severity in ["moderate", "high"]:
            return "moderate"
        else:
            return "low"

    def _get_relevant_tips(
        self, tip_database: Dict, root_cause: str, severity_category: str
    ) -> List[Dict]:
        """Get relevant tips based on root cause and severity"""
        tips = []

        # Get general tips first
        if "general" in tip_database:
            tips.extend(tip_database["general"])

        # Add cause-specific tips
        cause_key = self._get_cause_key(root_cause)
        if cause_key in tip_database:
            tips.extend(tip_database[cause_key])

        # Limit tips for lower severity
        if severity_category == "low":
            tips = tips[:4]
        elif severity_category == "moderate":
            tips = tips[:6]

        return tips

    def _get_cause_key(self, root_cause: str) -> str:
        """Map root cause to tip category key"""
        cause_lower = root_cause.lower()

        if "inflammation" in cause_lower or "dandruff" in cause_lower:
            return "scalp_health"
        elif "nutrition" in cause_lower or "deficiency" in cause_lower:
            return "nutrition"
        elif "stress" in cause_lower or "lifestyle" in cause_lower:
            return "lifestyle"

        return "general"

    def _filter_risky_tips(self, severity_category: str) -> List[Dict]:
        """Filter risky tips based on severity"""
        risky = self.risky.copy()

        # Show more risky tips for higher severity (so user is informed)
        if severity_category == "high":
            return risky
        elif severity_category == "moderate":
            return risky[:3]
        else:
            return risky[:2]

    def _get_severity_warnings(self, severity: str) -> List[str]:
        """Get severity-specific safety warnings"""
        severity = severity.lower()

        warnings = []

        if severity in ["severe", "very_severe"]:
            warnings.extend(
                [
                    "Your severity level requires professional medical evaluation.",
                    "Do not rely solely on home remedies. Consult a dermatologist.",
                    "Prescription treatments may be necessary for your condition.",
                ]
            )
        elif severity in ["high", "moderate"]:
            warnings.extend(
                [
                    "Consider professional consultation if no improvement in 4-6 weeks.",
                    "Monitor your progress with regular photos.",
                    "Be patient - hair growth takes time.",
                ]
            )
        else:
            warnings.extend(
                [
                    "Continue with consistent routine for best results.",
                    "Regular maintenance is key to preventing worsening.",
                ]
            )

        return warnings


def create_evidence_tips_engine() -> EvidenceTipsEngine:
    """Factory function to create EvidenceTipsEngine instance"""
    return EvidenceTipsEngine()


if __name__ == "__main__":
    engine = EvidenceTipsEngine()

    result = engine.generate(hair_severity="moderate", root_cause="Scalp Inflammation")

    print("Evidence Tips:")
    print("\nScientifically Proven:")
    for tip in result["scientifically_proven"]:
        print(f"  - {tip['tip']}")
        print(f"    Evidence: {tip['evidence_level']}, Safety: {tip['safety_note']}")

    print("\nRisky Tips (Use Caution):")
    for tip in result["risky"]:
        print(f"  - {tip['tip']}")
        print(f"    Safety Note: {tip['safety_note']}")
