"""
Simulation Interpreter Module

This module provides the SimulationInterpreter class for interpreting
simulation outputs and generating strategic coaching guidance.
"""

from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any, List

# Type definitions
ImpactLevel = Literal["low", "moderate", "high"]


@dataclass
class ImprovementImpact:
    """Represents an improvement's impact on the simulation."""

    name: str
    impact_level: ImpactLevel
    delta_contribution: float
    leverage_score: float


@dataclass
class SimulationInterpretation:
    """Structured interpretation of simulation results."""

    predicted_score: float
    score_delta: float
    impact_level: ImpactLevel
    highest_leverage_improvement: str
    optimal_combination: List[str]
    improvement_analysis: List[ImprovementImpact]
    strategic_explanation: str
    recommendations: List[str]


class SimulationInterpreter:
    """
    Interpreter for simulation outputs.

    Analyzes simulation results to determine impact levels and
    generate strategic coaching explanations.
    """

    # Thresholds for impact level determination
    HIGH_IMPACT_THRESHOLD = 5.0  # Delta >= 5% = high impact
    MODERATE_IMPACT_THRESHOLD = 2.0  # Delta >= 2% = moderate impact
    # Delta < 2% = low impact

    # Leverage score thresholds
    HIGH_LEVERAGE_THRESHOLD = 0.7  # >= 70% of max = high leverage
    MODERATE_LEVERAGE_THRESHOLD = 0.4  # >= 40% = moderate leverage

    def __init__(self):
        """Initialize the SimulationInterpreter."""
        pass

    def interpret(
        self,
        simulation_output: Dict[str, Any],
        current_score: float = 50.0,
    ) -> SimulationInterpretation:
        """
        Interpret simulation output and generate coaching.

        Args:
            simulation_output: Dictionary containing simulation results
            current_score: Current hair score for baseline

        Returns:
            SimulationInterpretation: Structured interpretation
        """
        # Extract simulation data
        predicted_score = simulation_output.get("predicted_score", current_score)
        score_delta = simulation_output.get("delta", predicted_score - current_score)

        # Get improvements from simulation
        improvements = simulation_output.get("improvements", {})

        # Determine impact level
        impact_level = self._determine_impact_level(score_delta)

        # Analyze each improvement
        improvement_analysis = self._analyze_improvements(improvements)

        # Find highest leverage improvement
        highest_leverage = self._find_highest_leverage(improvement_analysis)

        # Determine optimal combination
        optimal_combination = self._determine_optimal_combination(improvement_analysis)

        # Generate strategic explanation
        strategic_explanation = self._generate_explanation(
            impact_level=impact_level,
            highest_leverage=highest_leverage,
            optimal_combination=optimal_combination,
            score_delta=score_delta,
            predicted_score=predicted_score,
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            improvement_analysis=improvement_analysis,
            optimal_combination=optimal_combination,
        )

        return SimulationInterpretation(
            predicted_score=predicted_score,
            score_delta=score_delta,
            impact_level=impact_level,
            highest_leverage_improvement=highest_leverage,
            optimal_combination=optimal_combination,
            improvement_analysis=improvement_analysis,
            strategic_explanation=strategic_explanation,
            recommendations=recommendations,
        )

    def _determine_impact_level(self, delta: float) -> ImpactLevel:
        """Determine impact level based on score delta."""
        if delta >= self.HIGH_IMPACT_THRESHOLD:
            return "high"
        elif delta >= self.MODERATE_IMPACT_THRESHOLD:
            return "moderate"
        else:
            return "low"

    def _analyze_improvements(
        self, improvements: Dict[str, Any]
    ) -> List[ImprovementImpact]:
        """Analyze each improvement in the simulation."""
        analysis = []

        if not improvements:
            return analysis

        # Find max delta for leverage calculation
        max_delta = (
            max(abs(v.get("delta", 0)) for v in improvements.values())
            if improvements
            else 1.0
        )

        for name, data in improvements.items():
            delta = data.get("delta", 0)
            impact_level = self._determine_impact_level(delta)

            # Calculate leverage score (normalized 0-1)
            leverage = abs(delta) / max_delta if max_delta > 0 else 0

            analysis.append(
                ImprovementImpact(
                    name=name,
                    impact_level=impact_level,
                    delta_contribution=delta,
                    leverage_score=leverage,
                )
            )

        # Sort by leverage score (descending)
        analysis.sort(key=lambda x: x.leverage_score, reverse=True)

        return analysis

    def _find_highest_leverage(self, analysis: List[ImprovementImpact]) -> str:
        """Find the improvement with highest leverage."""
        if not analysis:
            return "none"

        return analysis[0].name

    def _determine_optimal_combination(
        self, analysis: List[ImprovementImpact]
    ) -> List[str]:
        """Determine optimal combination of improvements."""
        if not analysis:
            return []

        # Get improvements with moderate or high leverage
        significant = [
            imp.name
            for imp in analysis
            if imp.leverage_score >= self.MODERATE_LEVERAGE_THRESHOLD
        ]

        # If no significant improvements, take top 2
        if not significant:
            significant = [imp.name for imp in analysis[:2]]

        return significant

    def _generate_explanation(
        self,
        impact_level: ImpactLevel,
        highest_leverage: str,
        optimal_combination: List[str],
        score_delta: float,
        predicted_score: float,
    ) -> str:
        """Generate strategic explanation."""
        impact_descriptions = {
            "high": f"This simulation shows HIGH IMPACT potential (+{score_delta:.1f} points).",
            "moderate": f"This simulation shows MODERATE IMPACT potential (+{score_delta:.1f} points).",
            "low": f"This simulation shows limited impact (+{score_delta:.1f} points).",
        }

        leverage_intro = f"The highest leverage improvement is '{highest_leverage}'. "

        if len(optimal_combination) > 1:
            combo_text = (
                f"Combining {', '.join(optimal_combination[:-1])}, "
                f"and {optimal_combination[-1]} would maximize results."
            )
        else:
            combo_text = (
                f"Focusing on '{optimal_combination[0]}' would provide "
                f"the most efficient path to improvement."
            )

        return f"{impact_descriptions[impact_level]} {leverage_intro}{combo_text}"

    def _generate_recommendations(
        self,
        improvement_analysis: List[ImprovementImpact],
        optimal_combination: List[str],
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Priority recommendations based on leverage
        for imp in improvement_analysis[:3]:
            if imp.impact_level == "high":
                recommendations.append(
                    f"PRIORITY: Implement {imp.name} - high impact change"
                )
            elif imp.impact_level == "moderate":
                recommendations.append(f"Consider {imp.name} - moderate impact")

        # Combination recommendation
        if len(optimal_combination) > 1:
            recommendations.append(
                f"OPTIMAL STRATEGY: Combine {', '.join(optimal_combination)} "
                f"for maximum score improvement"
            )

        return recommendations

    def to_dict(self, interpretation: SimulationInterpretation) -> Dict[str, Any]:
        """Convert interpretation to dictionary."""
        return {
            "predicted_score": interpretation.predicted_score,
            "score_delta": interpretation.score_delta,
            "impact_level": interpretation.impact_level,
            "highest_leverage_improvement": interpretation.highest_leverage_improvement,
            "optimal_combination": interpretation.optimal_combination,
            "improvement_analysis": [
                {
                    "name": imp.name,
                    "impact_level": imp.impact_level,
                    "delta_contribution": imp.delta_contribution,
                    "leverage_score": imp.leverage_score,
                }
                for imp in interpretation.improvement_analysis
            ],
            "strategic_explanation": interpretation.strategic_explanation,
            "recommendations": interpretation.recommendations,
        }


def interpret_simulation(
    simulation_output: Dict[str, Any],
    current_score: float = 50.0,
) -> Dict[str, Any]:
    """
    Convenience function to interpret simulation output.

    Args:
        simulation_output: Simulation results dictionary
        current_score: Current hair score

    Returns:
        Dict: Interpretation as dictionary
    """
    interpreter = SimulationInterpreter()
    interpretation = interpreter.interpret(simulation_output, current_score)
    return interpreter.to_dict(interpretation)