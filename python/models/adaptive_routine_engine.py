"""
Adaptive Routine Engine
Generates dynamic hair care routines based on root cause, severity, and environmental factors
"""

from typing import Dict, List, Optional


class AdaptiveRoutineEngine:
    """
    Generates personalized, adaptive hair care routines based on multiple factors
    including root cause, severity levels, lifestyle, and environmental conditions.
    """

    def __init__(self):
        # Routine templates for different causes
        self.cause_routines = {
            "Genetic Predisposition": {
                "morning": [
                    {
                        "task": "Scalp massage",
                        "duration": "3-5 minutes",
                        "description": "Gentle circular motions to stimulate blood flow",
                    },
                    {
                        "task": "Apply minoxidil (if prescribed)",
                        "duration": "2 minutes",
                        "description": "As directed by healthcare provider",
                    },
                ],
                "mid_day": [
                    {
                        "task": "Avoid tight hairstyles",
                        "duration": "ongoing",
                        "description": "Let hair breathe, avoid tight buns/ponytails",
                    },
                ],
                "night": [
                    {
                        "task": "Scalp cleansing",
                        "duration": "5 minutes",
                        "description": "Gentle shampoo with massaging motions",
                    },
                    {
                        "task": "Apply hair growth serum",
                        "duration": "3 minutes",
                        "description": "Focus on thinning areas",
                    },
                ],
                "weekly": [
                    {
                        "task": "Deep conditioning mask",
                        "duration": "20-30 minutes",
                        "description": "Protein-based treatment",
                    },
                    {
                        "task": "Scalp exfoliation",
                        "duration": "10 minutes",
                        "description": "Remove buildup, unclog pores",
                    },
                ],
                "monthly": [
                    {
                        "task": "Trim split ends",
                        "duration": "15 minutes",
                        "description": "Prevent further damage",
                    },
                    {
                        "task": "Professional scalp analysis",
                        "duration": "30 minutes",
                        "description": "Track progress with specialist",
                    },
                ],
            },
            "Scalp Inflammation": {
                "morning": [
                    {
                        "task": "Gentle scalp rinse",
                        "duration": "3 minutes",
                        "description": "Lukewarm water to soothe scalp",
                    },
                    {
                        "task": "Apply anti-inflammatory serum",
                        "duration": "2 minutes",
                        "description": "Tea tree or aloe vera based",
                    },
                ],
                "mid_day": [
                    {
                        "task": "Avoid touching scalp",
                        "duration": "ongoing",
                        "description": "Reduce irritation from hands",
                    },
                ],
                "night": [
                    {
                        "task": "Medicated shampoo wash",
                        "duration": "5-7 minutes",
                        "description": "Use ketoconazole or salicylic acid shampoo",
                    },
                    {
                        "task": "Cool water rinse",
                        "duration": "2 minutes",
                        "description": "Close pores, reduce inflammation",
                    },
                    {
                        "task": "Apply calming scalp treatment",
                        "duration": "5 minutes",
                        "description": "Leave-in treatment for overnight relief",
                    },
                ],
                "weekly": [
                    {
                        "task": "Apple cider vinegar rinse",
                        "duration": "10 minutes",
                        "description": "1:1 ratio with water, balance pH",
                    },
                    {
                        "task": "Gentle scalp massage with oil",
                        "duration": "10 minutes",
                        "description": "Coconut or jojoba oil",
                    },
                ],
                "monthly": [
                    {
                        "task": "Scalp detox treatment",
                        "duration": "45 minutes",
                        "description": "Professional clarifying treatment",
                    },
                ],
            },
            "Stress & Lifestyle": {
                "morning": [
                    {
                        "task": "5-minute meditation",
                        "duration": "5 minutes",
                        "description": "Reduce cortisol levels",
                    },
                    {
                        "task": "Gentle scalp brushing",
                        "duration": "2 minutes",
                        "description": "Boost circulation without tension",
                    },
                ],
                "mid_day": [
                    {
                        "task": "Stress relief breathing",
                        "duration": "2 minutes",
                        "description": "Deep breathing exercises",
                    },
                ],
                "night": [
                    {
                        "task": "Relaxation routine",
                        "duration": "15 minutes",
                        "description": "Wind down before sleep",
                    },
                    {
                        "task": "Scalp massage with warm oil",
                        "duration": "10 minutes",
                        "description": "Castor or almond oil",
                    },
                    {
                        "task": "Consistent sleep time",
                        "duration": "ongoing",
                        "description": "Maintain 7-8 hours sleep",
                    },
                ],
                "weekly": [
                    {
                        "task": "Yoga or light exercise",
                        "duration": "30 minutes",
                        "description": "Improve blood circulation",
                    },
                    {
                        "task": "Natural hair mask",
                        "duration": "30 minutes",
                        "description": "Avocado, banana, or egg mask",
                    },
                ],
                "monthly": [
                    {
                        "task": "Lifestyle assessment review",
                        "duration": "15 minutes",
                        "description": "Track stress triggers",
                    },
                ],
            },
            "Nutritional Deficiency": {
                "morning": [
                    {
                        "task": "Vitamin supplement with breakfast",
                        "duration": "2 minutes",
                        "description": "Biotin, vitamin D, iron if deficient",
                    },
                    {
                        "task": "Protein-rich breakfast",
                        "duration": "15 minutes",
                        "description": "Eggs, Greek yogurt, or protein shake",
                    },
                ],
                "mid_day": [
                    {
                        "task": "Healthy snack",
                        "duration": "5 minutes",
                        "description": "Nuts, seeds, or protein bar",
                    },
                ],
                "night": [
                    {
                        "task": "Iron-rich dinner",
                        "duration": "30 minutes",
                        "description": "Leafy greens, lean meats",
                    },
                    {
                        "task": "Scalp-nourishing oil application",
                        "duration": "10 minutes",
                        "description": "Vitamin E rich oils",
                    },
                ],
                "weekly": [
                    {
                        "task": "Meal prep for hair-healthy foods",
                        "duration": "60 minutes",
                        "description": "Prepare protein and veggie-rich meals",
                    },
                    {
                        "task": "Protein treatment",
                        "duration": "30 minutes",
                        "description": "Internal and external protein focus",
                    },
                ],
                "monthly": [
                    {
                        "task": "Blood test review",
                        "duration": "30 minutes",
                        "description": "Check vitamin levels with doctor",
                    },
                ],
            },
            "Environmental Factors": {
                "morning": [
                    {
                        "task": "UV protection spray",
                        "duration": "2 minutes",
                        "description": "Protect from sun damage",
                    },
                    {
                        "task": "Anti-pollution hair mist",
                        "duration": "1 minute",
                        "description": "Create barrier against pollutants",
                    },
                ],
                "mid_day": [
                    {
                        "task": "Cover hair when outdoors",
                        "duration": "ongoing",
                        "description": "Hat or scarf in harsh weather",
                    },
                ],
                "night": [
                    {
                        "task": "Deep cleansing shampoo",
                        "duration": "5 minutes",
                        "description": "Remove pollutants and buildup",
                    },
                    {
                        "task": "Hydrating hair mask",
                        "duration": "20 minutes",
                        "description": "Restore moisture from environmental damage",
                    },
                ],
                "weekly": [
                    {
                        "task": "Clarifying treatment",
                        "duration": "15 minutes",
                        "description": "Remove hard water mineral buildup",
                    },
                    {
                        "task": "Cold water rinse",
                        "duration": "3 minutes",
                        "description": "Close cuticles, add shine",
                    },
                ],
                "monthly": [],
            },
            "Hair Care Practices": {
                "morning": [
                    {
                        "task": "Gentle detangling",
                        "duration": "5 minutes",
                        "description": "Start from ends, work up",
                    },
                    {
                        "task": "Heat protectant spray",
                        "duration": "2 minutes",
                        "description": "If using any heat styling",
                    },
                ],
                "mid_day": [
                    {
                        "task": "Avoid heat tools touch-ups",
                        "duration": "ongoing",
                        "description": "Minimize heat damage",
                    },
                ],
                "night": [
                    {
                        "task": "Air dry or diffuse",
                        "duration": "15 minutes",
                        "description": "Avoid towel rubbing",
                    },
                    {
                        "task": "Silk pillowcase sleep",
                        "duration": "ongoing",
                        "description": "Reduce friction and breakage",
                    },
                ],
                "weekly": [
                    {
                        "task": "No-heat styling day",
                        "duration": "all day",
                        "description": "Give hair a break from styling",
                    },
                    {
                        "task": "Deep conditioning",
                        "duration": "30 minutes",
                        "description": "Repair damaged strands",
                    },
                ],
                "monthly": [
                    {
                        "task": "Trim damaged ends",
                        "duration": "15 minutes",
                        "description": "Maintain hair health",
                    },
                ],
            },
        }

        # Severity modifiers
        self.severity_modifiers = {
            "none": {"intensity": 0.5, "frequency": 0.5},
            "low": {"intensity": 0.6, "frequency": 0.6},
            "mild": {"intensity": 0.8, "frequency": 0.8},
            "moderate": {"intensity": 1.0, "frequency": 1.0},
            "high": {"intensity": 1.2, "frequency": 1.2},
            "severe": {"intensity": 1.5, "frequency": 1.5},
            "very_severe": {"intensity": 1.8, "frequency": 1.8},
        }

        # Lifestyle-based additions
        self.lifestyle_additions = {
            "high_stress": [
                {
                    "task": "Breathing exercises",
                    "duration": "5 minutes",
                    "time": "morning",
                    "description": "4-7-8 breathing technique",
                },
                {
                    "task": "Evening meditation",
                    "duration": "10 minutes",
                    "time": "night",
                    "description": "Wind down routine",
                },
            ],
            "poor_sleep": [
                {
                    "task": "Blue light avoidance",
                    "duration": "2 hours",
                    "time": "evening",
                    "description": "No screens before bed",
                },
                {
                    "task": "Sleep-friendly hairstyle",
                    "duration": "5 minutes",
                    "time": "night",
                    "description": "Loose braid or silk wrap",
                },
            ],
            "poor_diet": [
                {
                    "task": "Meal tracking",
                    "duration": "15 minutes",
                    "time": "daily",
                    "description": "Monitor protein and vitamin intake",
                },
                {
                    "task": "Hydration reminder",
                    "duration": "ongoing",
                    "time": "daily",
                    "description": "8 glasses of water minimum",
                },
            ],
            "sedentary": [
                {
                    "task": "Daily walk",
                    "duration": "30 minutes",
                    "time": "morning",
                    "description": "Boost circulation",
                },
                {
                    "task": "Standing desk breaks",
                    "duration": "5 minutes",
                    "time": "mid_day",
                    "description": "Every hour",
                },
            ],
        }

        # Environmental factor handlers
        self.environmental_handlers = {
            "high_humidity": [
                {
                    "task": "Anti-frizz serum",
                    "duration": "2 minutes",
                    "time": "morning",
                    "description": "Control humidity effects",
                },
                {
                    "task": "Lightweight products",
                    "duration": "ongoing",
                    "time": "daily",
                    "description": "Avoid heavy creams",
                },
            ],
            "low_humidity": [
                {
                    "task": "Leave-in conditioner",
                    "duration": "3 minutes",
                    "time": "morning",
                    "description": "Extra moisture lock",
                },
                {
                    "task": "Humidifier at home",
                    "duration": "ongoing",
                    "time": "night",
                    "description": "Add moisture to air",
                },
            ],
            "high_pollution": [
                {
                    "task": "Cover hair outdoors",
                    "duration": "ongoing",
                    "time": "outdoor",
                    "description": "Protect from pollutants",
                },
                {
                    "task": "Antioxidant scalp spray",
                    "duration": "2 minutes",
                    "time": "evening",
                    "description": "Fight free radicals",
                },
            ],
            "hard_water": [
                {
                    "task": "Filtered water rinse",
                    "duration": "5 minutes",
                    "time": "washing",
                    "description": "Use filtered water for final rinse",
                },
                {
                    "task": "Chelating shampoo weekly",
                    "duration": "10 minutes",
                    "time": "weekly",
                    "description": "Remove mineral buildup",
                },
            ],
        }

    def generate(
        self,
        hairloss_severity: str,
        dandruff_severity: str,
        root_cause: str,
        lifestyle_score: int,
        humidity: Optional[str] = "normal",
        pollution_level: Optional[str] = "moderate",
    ) -> Dict:
        """
        Generate adaptive hair care routine

        Args:
            hairloss_severity: Severity of hair loss (none, mild, moderate, severe, etc.)
            dandruff_severity: Severity of dandruff (none, mild, moderate, severe)
            root_cause: Primary root cause identifier
            lifestyle_score: Overall lifestyle score (0-100)
            humidity: Humidity level (low, normal, high)
            pollution_level: Environmental pollution level (low, moderate, high)

        Returns:
            Dictionary with structured routine:
            - morning: List of morning tasks
            - mid_day: List of midday tasks
            - night: List of night tasks
            - weekly: List of weekly tasks
            - monthly: List of monthly tasks
        """

        # Get base routine for root cause
        base_routine = self.cause_routines.get(
            root_cause, self.cause_routines["Hair Care Practices"]  # Default
        )

        # Get severity modifiers
        hair_severity_mod = self.severity_modifiers.get(
            hairloss_severity.lower(), {"intensity": 1.0, "frequency": 1.0}
        )

        # Generate routine with adaptations
        routine = self._build_adaptive_routine(
            base_routine=base_routine,
            severity_modifier=hair_severity_mod,
            lifestyle_score=lifestyle_score,
            root_cause=root_cause,
            humidity=humidity,
            pollution_level=pollution_level,
            dandruff_severity=dandruff_severity,
        )

        return routine

    def _build_adaptive_routine(
        self,
        base_routine: Dict,
        severity_modifier: Dict,
        lifestyle_score: int,
        root_cause: str,
        humidity: str,
        pollution_level: str,
        dandruff_severity: str,
    ) -> Dict:
        """Build the adaptive routine with all modifications"""

        routine = {
            "morning": [],
            "mid_day": [],
            "night": [],
            "weekly": [],
            "monthly": [],
        }

        # Add base routine tasks
        for time_slot, tasks in base_routine.items():
            routine[time_slot] = tasks.copy()

        # Add lifestyle-based additions for low scores
        if lifestyle_score < 50:
            if lifestyle_score < 30:
                # Very poor lifestyle - add all interventions
                routine["morning"].extend(self.lifestyle_additions["high_stress"][:1])
                routine["night"].extend(self.lifestyle_additions["poor_sleep"][:1])
            elif lifestyle_score < 40:
                # Poor lifestyle
                routine["morning"].extend(self.lifestyle_additions["high_stress"][:1])
            # Add diet improvements for any low score
            routine["mid_day"].extend(self.lifestyle_additions["poor_diet"][:1])

        # Add environmental handlers
        if humidity == "high":
            routine["morning"].extend(self.environmental_handlers["high_humidity"][:1])
            routine["night"].extend(self.environmental_handlers["high_humidity"][1:])
        elif humidity == "low":
            routine["morning"].extend(self.environmental_handlers["low_humidity"][:1])
            routine["night"].extend(self.environmental_handlers["low_humidity"][1:])

        if pollution_level == "high":
            routine["mid_day"].extend(self.environmental_handlers["high_pollution"][:1])
            routine["night"].extend(self.environmental_handlers["high_pollution"][1:])

        # Add dandruff-specific modifications
        if dandruff_severity.lower() in ["moderate", "high", "severe"]:
            routine["night"].insert(
                0,
                {
                    "task": "Medicated dandruff treatment",
                    "duration": "10 minutes",
                    "description": "Use anti-dandruff shampoo or treatment",
                },
            )

        intensity = severity_modifier.get("intensity", 1.0)

        if intensity >= 1.3:
            routine["weekly"].append({
                "task": "Extra monitoring photos",
                "duration": "5 minutes",
                "description": "Track aggressive progression"
        })
        # Add stress cause specific routines
        if "Stress" in root_cause:
            routine["mid_day"].append(
                {
                    "task": "Mindfulness break",
                    "duration": "5 minutes",
                    "description": "Quick stress relief technique",
                }
            )

        return routine

    def get_routine_summary(self, routine: Dict) -> Dict:
        """Get a summary of the routine"""

        total_tasks = sum(len(tasks) for tasks in routine.values())

        return {
            "total_tasks": total_tasks,
            "morning_tasks": len(routine.get("morning", [])),
            "mid_day_tasks": len(routine.get("mid_day", [])),
            "night_tasks": len(routine.get("night", [])),
            "weekly_tasks": len(routine.get("weekly", [])),
            "monthly_tasks": len(routine.get("monthly", [])),
        }


def create_adaptive_routine_engine() -> AdaptiveRoutineEngine:
    """Factory function to create AdaptiveRoutineEngine instance"""
    return AdaptiveRoutineEngine()


if __name__ == "__main__":
    # Test the adaptive routine engine
    engine = AdaptiveRoutineEngine()

    routine = engine.generate(
        hairloss_severity="moderate",
        dandruff_severity="mild",
        root_cause="Scalp Inflammation",
        lifestyle_score=65,
        humidity="high",
        pollution_level="moderate",
    )

    print("Adaptive Routine:")
    for time_slot, tasks in routine.items():
        print(f"\n{time_slot.upper()}:")
        for task in tasks:
            print(f"  - {task['task']}: {task['duration']}")
