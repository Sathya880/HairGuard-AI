"""
Suggestion Engine V2
Generates categorized suggestions based on root cause and severity
"""

from typing import Dict, Optional
import logging


class SuggestionEngineV2:
    """
    Generates structured suggestions with effort and impact levels
    for immediate, short-term, and long-term hair care improvements.
    """

    def __init__(self):

        # Root cause normalization map
        # Maps Bayesian engine outputs → SuggestionEngine categories
        self.root_cause_alias_map = {

    # Bayesian engine keys
    "androgenetic_alopecia": "Genetic Predisposition",
    "telogen_effluvium": "Stress & Lifestyle",
    "scalp_inflammation": "Scalp Inflammation",
    "nutritional_deficiency": "Nutritional Deficiency",
    "traction_mechanical": "Hair Care Practices",

    # additional aliases
    "genetic": "Genetic Predisposition",
    "genetic_hair_loss": "Genetic Predisposition",
    "androgenetic alopecia": "Genetic Predisposition",
    "aga": "Genetic Predisposition",

    "dandruff": "Scalp Inflammation",
    "seborrheic dermatitis": "Scalp Inflammation",
    "itchy_scalp": "Scalp Inflammation",

    "stress": "Stress & Lifestyle",
    "stress_lifestyle": "Stress & Lifestyle",
    "sleep": "Stress & Lifestyle",

    "nutrition": "Nutritional Deficiency",
    "diet": "Nutritional Deficiency",
    "vitamin_deficiency": "Nutritional Deficiency",
    "iron_deficiency": "Nutritional Deficiency",

    "environment": "Environmental Factors",
    "pollution": "Environmental Factors",
    "uv": "Environmental Factors",

    "hair_care": "Hair Care Practices",
    "styling_damage": "Hair Care Practices",
    }

        # Root cause suggestions
        self.cause_suggestions = {
            "Genetic Predisposition": {
                "immediate": [
                    {"action": "Use DHT-blocking shampoo (ketoconazole or saw palmetto)", "effort_level": "low", "impact_level": "medium"},
                    {"action": "Avoid tight hairstyles that stress follicles", "effort_level": "low", "impact_level": "medium"},
                    {"action": "Photograph hairline monthly to track progression", "effort_level": "low", "impact_level": "low"},
                ],
                "7_day": [
                    {"action": "Begin scalp massage 5 min/day to stimulate blood flow", "effort_level": "low", "impact_level": "medium"},
                    {"action": "Start biotin + zinc supplementation", "effort_level": "low", "impact_level": "medium"},
                    {"action": "Research minoxidil as an evidence-based option", "effort_level": "low", "impact_level": "high"},
                ],
                "30_day": [
                    {"action": "Consult a dermatologist for finasteride / dutasteride evaluation", "effort_level": "medium", "impact_level": "high"},
                    {"action": "Consider PRP (Platelet-Rich Plasma) therapy assessment", "effort_level": "high", "impact_level": "high"},
                    {"action": "Evaluate low-level laser therapy (LLLT) devices", "effort_level": "medium", "impact_level": "medium"},
                ],
            },
            "Stress & Lifestyle": {
                "immediate": [
                    {"action": "Begin daily 10-minute meditation or deep-breathing exercise", "effort_level": "low", "impact_level": "medium"},
                    {"action": "Reduce caffeine and alcohol intake", "effort_level": "medium", "impact_level": "medium"},
                    {"action": "Ensure 7-8 hours of sleep per night", "effort_level": "medium", "impact_level": "high"},
                ],
                "7_day": [
                    {"action": "Start a consistent sleep schedule (same bedtime daily)", "effort_level": "low", "impact_level": "high"},
                    {"action": "Add 20 min of light exercise daily (walk, yoga)", "effort_level": "low", "impact_level": "medium"},
                    {"action": "Take ashwagandha or magnesium to reduce cortisol", "effort_level": "low", "impact_level": "medium"},
                ],
                "30_day": [
                    {"action": "Establish a stress management routine (journaling, therapy)", "effort_level": "medium", "impact_level": "high"},
                    {"action": "Get blood tests for cortisol and thyroid levels", "effort_level": "medium", "impact_level": "high"},
                    {"action": "Review and reduce work/lifestyle stressors with a counsellor", "effort_level": "high", "impact_level": "high"},
                ],
            },
            "Scalp Inflammation": {
                "immediate": [
                    {"action": "Switch to a sulphate-free, anti-dandruff shampoo", "effort_level": "low", "impact_level": "high"},
                    {"action": "Apply diluted tea tree oil to scalp 3x/week", "effort_level": "low", "impact_level": "medium"},
                    {"action": "Avoid scratching - use fingertip pads during washing", "effort_level": "low", "impact_level": "medium"},
                ],
                "7_day": [
                    {"action": "Use ketoconazole 2% shampoo twice per week for 4 weeks", "effort_level": "low", "impact_level": "high"},
                    {"action": "Apply salicylic acid scalp serum to loosen flakes", "effort_level": "low", "impact_level": "medium"},
                    {"action": "Avoid oily/heavy hair products that clog follicles", "effort_level": "low", "impact_level": "medium"},
                ],
                "30_day": [
                    {"action": "See a dermatologist if flaking/redness persists after 2 weeks", "effort_level": "medium", "impact_level": "high"},
                    {"action": "Try a zinc pyrithione treatment shampoo rotation", "effort_level": "low", "impact_level": "medium"},
                    {"action": "Review diet for omega-3 and zinc deficiencies linked to seborrheic dermatitis", "effort_level": "medium", "impact_level": "medium"},
                ],
            },
            "Nutritional Deficiency": {
                "immediate": [
                    {"action": "Start iron + vitamin C supplement (iron needs C for absorption)", "effort_level": "low", "impact_level": "high"},
                    {"action": "Add protein-rich foods to every meal (eggs, lentils, chicken)", "effort_level": "medium", "impact_level": "high"},
                    {"action": "Begin biotin 5000 mcg/day", "effort_level": "low", "impact_level": "medium"},
                ],
                "7_day": [
                    {"action": "Get blood tests: ferritin, B12, vitamin D, zinc", "effort_level": "medium", "impact_level": "high"},
                    {"action": "Replace processed snacks with nuts and seeds (zinc, selenium)", "effort_level": "medium", "impact_level": "medium"},
                    {"action": "Add leafy greens daily for folate and iron", "effort_level": "low", "impact_level": "medium"},
                ],
                "30_day": [
                    {"action": "Work with a nutritionist to create a hair-supportive meal plan", "effort_level": "high", "impact_level": "high"},
                    {"action": "Address any deficiency found in bloodwork with targeted supplements", "effort_level": "medium", "impact_level": "high"},
                    {"action": "Maintain consistent meal timing to stabilise nutrient absorption", "effort_level": "medium", "impact_level": "medium"},
                ],
            },
            "Environmental Factors": {
                "immediate": [
                    {"action": "Rinse hair with filtered water if using hard/tap water", "effort_level": "low", "impact_level": "medium"},
                    {"action": "Apply UV-protection hair serum before sun exposure", "effort_level": "low", "impact_level": "medium"},
                    {"action": "Wear a light cap in high-pollution or dusty environments", "effort_level": "low", "impact_level": "medium"},
                ],
                "7_day": [
                    {"action": "Install a shower head filter to reduce chlorine and hard minerals", "effort_level": "medium", "impact_level": "medium"},
                    {"action": "Do a clarifying scalp wash twice a week to remove pollution build-up", "effort_level": "low", "impact_level": "medium"},
                    {"action": "Limit direct sun exposure to hair between 10am-3pm", "effort_level": "low", "impact_level": "low"},
                ],
                "30_day": [
                    {"action": "Use an antioxidant scalp serum (vitamin E, niacinamide) regularly", "effort_level": "low", "impact_level": "medium"},
                    {"action": "Review air quality at home and consider an air purifier", "effort_level": "high", "impact_level": "medium"},
                    {"action": "Track whether hair health improves after environmental changes", "effort_level": "low", "impact_level": "low"},
                ],
            },
            "Hair Care Practices": {
                "immediate": [
                    {"action": "Stop using heat tools (straightener, dryer) above 150 C", "effort_level": "medium", "impact_level": "high"},
                    {"action": "Switch to a wide-tooth comb and detangle gently when wet", "effort_level": "low", "impact_level": "medium"},
                    {"action": "Avoid tight ponytails, braids, or buns that pull at the root", "effort_level": "low", "impact_level": "medium"},
                ],
                "7_day": [
                    {"action": "Use a heat protectant spray every time before heat styling", "effort_level": "low", "impact_level": "medium"},
                    {"action": "Reduce wash frequency to every 2-3 days to preserve natural oils", "effort_level": "low", "impact_level": "medium"},
                    {"action": "Switch to a silk or satin pillowcase to reduce friction", "effort_level": "low", "impact_level": "low"},
                ],
                "30_day": [
                    {"action": "Deep condition hair weekly with a protein-moisture treatment", "effort_level": "low", "impact_level": "medium"},
                    {"action": "Audit all hair products for alcohol, sulphates, and parabens", "effort_level": "medium", "impact_level": "medium"},
                    {"action": "Trim split ends every 6-8 weeks to prevent breakage travelling up shaft", "effort_level": "low", "impact_level": "low"},
                ],
            },
        }

        # Severity modifiers
        self.severity_modifiers = {
            "severe": {"add_urgent": True, "escalate_impact": True},
            "high": {"add_urgent": True, "escalate_impact": False},
            "moderate": {"add_urgent": False, "escalate_impact": False},
            "mild": {"add_urgent": False, "escalate_impact": False},
            "low": {"add_urgent": False, "escalate_impact": False},
            "none": {"add_urgent": False, "escalate_impact": False},
        }

        # Clinical consultation triggers
        self.clinical_triggers = {
            "Genetic Predisposition": "high",
            "Scalp Inflammation": "moderate",
            "Stress & Lifestyle": "low",
            "Nutritional Deficiency": "moderate",
            "Environmental Factors": "low",
            "Hair Care Practices": "low",
        }

        self.logger = logging.getLogger(__name__)

    # --------------------------------------------------
    # Root cause normalization
    # --------------------------------------------------

    def _normalize_root_cause(self, root_cause: Optional[str]) -> str:

        if not root_cause:
            return "Hair Care Practices"

        rc = str(root_cause).strip()

        # Direct match
        if rc in self.cause_suggestions:
            return rc

        rc_lower = rc.lower()

        # Alias mapping
        if rc_lower in self.root_cause_alias_map:
            return self.root_cause_alias_map[rc_lower]

        # Fuzzy containment
        for key, mapped in self.root_cause_alias_map.items():
            if key in rc_lower:
                return mapped

        # Log unknown cause
        self.logger.warning(f"Unknown root cause received: {root_cause}")

        return "Hair Care Practices"

    # --------------------------------------------------
    # Main suggestion generator
    # --------------------------------------------------

    def generate(
        self,
        root_cause: str,
        hair_severity: str,
        dandruff_severity: str,
        lifestyle_score: int,
    ) -> Dict:

        # Normalize root cause
        normalized_root_cause = self._normalize_root_cause(root_cause)

        # Get base suggestions
        suggestions = self.cause_suggestions.get(
            normalized_root_cause,
            self.cause_suggestions["Hair Care Practices"]
        )
        
        # Severity modifier
        modifier = self.severity_modifiers.get(
            hair_severity.lower(),
            {"add_urgent": False, "escalate_impact": False}
        )

        # Build result
        result = {
            "immediate_actions": suggestions.get("immediate", []).copy(),
            "7_day_corrective_actions": suggestions.get("7_day", []).copy(),
            "30_day_rebuild_actions": suggestions.get("30_day", []).copy(),
        }

        # Urgent dermatologist suggestion
        if modifier.get("add_urgent"):
            result["immediate_actions"].insert(
                0,
                {
                    "action": "Schedule urgent dermatologist appointment",
                    "effort_level": "high",
                    "impact_level": "high",
                },
            )

        # Escalate impact
        if modifier.get("escalate_impact"):
            result = self._escalate_impacts(result)

        # Dandruff suggestions
        if dandruff_severity.lower() in ["moderate", "high", "severe"]:
            result["immediate_actions"].append(
                {
                    "action": "Use anti-dandruff shampoo immediately",
                    "effort_level": "low",
                    "impact_level": "high",
                }
            )

        # Clinical recommendation
        result["clinical_consult_recommendation"] = self._get_clinical_recommendation(
            normalized_root_cause,
            hair_severity,
            lifestyle_score
        )

        return result

    # --------------------------------------------------
    # Impact escalation
    # --------------------------------------------------

    def _escalate_impacts(self, suggestions: Dict) -> Dict:

        for key in [
            "immediate_actions",
            "7_day_corrective_actions",
            "30_day_rebuild_actions",
        ]:
            for item in suggestions.get(key, []):
                if item.get("impact_level") == "medium":
                    item["impact_level"] = "high"

        return suggestions

    # --------------------------------------------------
    # Clinical recommendation
    # --------------------------------------------------

    def _get_clinical_recommendation(
        self,
        root_cause: str,
        hair_severity: str,
        lifestyle_score: int
    ) -> str:

        base_trigger = self.clinical_triggers.get(root_cause, "low")

        if hair_severity.lower() in ["severe", "very_severe"]:
            return "URGENT: Consult a dermatologist immediately."

        elif hair_severity.lower() == "high" or base_trigger == "high":
            return "RECOMMENDED: Consult a dermatologist within 2 weeks."

        elif hair_severity.lower() == "moderate" or lifestyle_score < 40:
            return "SUGGESTED: Dermatology consultation would be beneficial."

        else:
            return "OPTIONAL: Continue current routine and review in 30 days."


def create_suggestion_engine_v2() -> SuggestionEngineV2:
    return SuggestionEngineV2()