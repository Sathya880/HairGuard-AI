"""
Advanced Remedies Engine
UI-Aligned Version
Only returns keys used in Remedies Tab
"""

from typing import Dict, List, Optional


class RemediesEngine:

    # =========================================================
    # MAIN ENTRY
    # =========================================================
    def generate(
        self,
        hairloss_severity: str,
        dandruff_severity: str,
        root_cause: str,
        flashcard_answers: Optional[Dict] = None,
    ) -> Dict:

        hairloss_severity = (hairloss_severity or "unknown").lower()
        dandruff_severity = (dandruff_severity or "unknown").lower()
        root_cause = (root_cause or "").lower()
        flashcard_answers = flashcard_answers or {}

        return self._build_plan(
            hairloss_severity,
            dandruff_severity,
            root_cause,
            flashcard_answers,
        )

    # =========================================================
    # CORE PLAN BUILDER (MATCHES FLUTTER TAB)
    # =========================================================
    def _build_plan(
        self,
        hairloss,
        dandruff,
        root_cause,
        flashcards,
    ) -> Dict:

        return {
            "earlyDetection": self._early_detection_note(hairloss),
            "failureTimeline": self._progression_timeline(hairloss),
            "homeRemedies": {
                "hairloss": self._hairloss_remedies(
                    hairloss, root_cause, flashcards
                ),
                "dandruff": self._dandruff_remedies(
                    dandruff, flashcards
                )
            },
            "treatmentIneffective": self._avoid_list(
                hairloss, dandruff, root_cause
            )
        }

    # =========================================================
    # EARLY DETECTION
    # =========================================================
    def _early_detection_note(self, hairloss):

        if hairloss == "none":
            return "No visible follicle stress."

        if hairloss == "mild":
            return "Early thinning detected. High reversal potential."

        if hairloss == "moderate":
            return "Active follicle miniaturization in progress."

        if hairloss == "severe":
            return "Advanced thinning. Medical therapy likely required."

        return ""

    # =========================================================
    # FAILURE TIMELINE (UI key)
    # =========================================================
    def _progression_timeline(self, hairloss):

        if hairloss == "mild":
            return "Density may visibly reduce within 6–12 months if ignored."

        if hairloss == "moderate":
            return "Noticeable scalp visibility within 4–8 months if untreated."

        if hairloss == "severe":
            return "Permanent follicle shrinkage risk without intervention."

        return ""

    # =========================================================
    # HAIRLOSS REMEDIES
    # =========================================================
    def _hairloss_remedies(self, severity, root_cause, flashcards):

        remedies: List[str] = [
            "Scalp massage 5–10 mins, 4x weekly.",
            "Use sulfate-free shampoo.",
            "Avoid tight hairstyles.",
            "Limit heat styling. Always use heat protectant."
        ]

        if severity in ["moderate", "severe"]:
            remedies.append("Check iron, Vitamin D, B12 levels.")
            remedies.append("Consult dermatologist for medical therapy.")

        if "stress" in root_cause:
            remedies.append("Daily stress reduction (20 min walk + breathing).")

        if "nutrition" in root_cause:
            remedies.append("Increase protein to ~1g per kg body weight daily.")

        if flashcards.get("heat_styling") == "Every day":
            remedies.append("Reduce heat styling to ≤2x per week.")

        if flashcards.get("water_type") and "Hard water" in flashcards.get("water_type"):
            remedies.append("Install shower filter to reduce mineral buildup.")

        return remedies

    # =========================================================
    # DANDRUFF REMEDIES
    # =========================================================
    def _dandruff_remedies(self, severity, flashcards):

        remedies: List[str] = [
            "Wash scalp regularly to prevent oil buildup."
        ]

        if severity in ["mild", "moderate"]:
            remedies.append("Use ketoconazole or zinc shampoo 2x weekly.")

        if severity == "severe":
            remedies.append("Use medicated ketoconazole shampoo.")
            remedies.append("Avoid oiling inflamed scalp.")
            remedies.append("Consult dermatologist if persistent.")

        if flashcards.get("scalp_sweat") == "Yes, a lot":
            remedies.append("Dry scalp after sweating to prevent fungal growth.")

        return remedies

    # =========================================================
    # AVOID THESE (treatmentIneffective)
    # =========================================================
    def _avoid_list(self, hairloss, dandruff, root_cause):

        avoid: List[str] = [
            "Do not rely only on oils for hair regrowth.",
            "Avoid frequent chemical treatments.",
            "Do not ignore persistent shedding."
        ]

        if dandruff == "severe":
            avoid.append("Avoid heavy oiling on inflamed scalp.")

        if hairloss in ["moderate", "severe"]:
            avoid.append("Do not delay medical evaluation.")

        return avoid