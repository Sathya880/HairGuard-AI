"""
Strategy Engine Module

This module provides the StrategyEngine class for mapping assistant states
to appropriate strategy modes.
"""

from typing import Literal, Optional, Dict

# Strategy mode types
StrategyMode = Literal[
    "urgency",
    "intervention",
    "optimization",
    "accountability",
    "reinforcement",
    "data_collection",
    "monitoring",
]

# State types (imported from state_classifier for consistency)
StateType = Literal[
    "improving",
    "plateau",
    "declining",
    "high_risk",
    "low_discipline",
    "uncertain",
    "neutral",
]


class StrategyEngine:
    """
    Engine for mapping assistant states to strategy modes.

    This engine provides a mapping from user states to appropriate
    strategy responses, enabling the assistant to take appropriate
    actions based on the user's current situation.

    State to Strategy Mapping:
        - high_risk → urgency: Requires immediate attention and action
        - declining → intervention: Needs corrective measures
        - plateau → optimization: Focus on maximizing results
        - low_discipline → accountability: Emphasis on adherence
        - improving → reinforcement: Encourage continued progress
        - uncertain → data_collection: Gather more information
        - neutral → monitoring: Standard observation mode
    """

    # Default state to strategy mode mapping
    _DEFAULT_STRATEGY_MAP: Dict[StateType, StrategyMode] = {
        "high_risk": "urgency",
        "declining": "intervention",
        "plateau": "optimization",
        "low_discipline": "accountability",
        "improving": "reinforcement",
        "uncertain": "data_collection",
        "neutral": "monitoring",
    }

    def __init__(
        self, custom_strategy_map: Optional[Dict[StateType, StrategyMode]] = None
    ):
        """
        Initialize the StrategyEngine with optional custom strategy mapping.

        Args:
            custom_strategy_map: Optional custom mapping of states to strategies.
                                 If provided, will be merged with default mapping,
                                 with custom values taking precedence.
        """
        # Start with default mapping
        self._strategy_map = self._DEFAULT_STRATEGY_MAP.copy()

        # Apply custom mapping if provided
        if custom_strategy_map:
            self._strategy_map.update(custom_strategy_map)

    def get_strategy(self, state: StateType) -> StrategyMode:
        """
        Get the strategy mode for the given state.

        Args:
            state: The current assistant state

        Returns:
            StrategyMode: The selected strategy mode string
        """
        return self._strategy_map.get(state, "monitoring")

    def add_strategy(self, state: StateType, strategy: StrategyMode) -> None:
        """
        Add or update a strategy mapping for a state.

        This method allows extensibility by enabling the addition
        of new state-strategy mappings.

        Args:
            state: The state to map
            strategy: The corresponding strategy mode
        """
        self._strategy_map[state] = strategy

    def remove_strategy(self, state: StateType) -> bool:
        """
        Remove a strategy mapping for a state.

        Args:
            state: The state to remove the mapping for

        Returns:
            bool: True if the mapping was removed, False if it didn't exist
        """
        if state in self._strategy_map:
            del self._strategy_map[state]
            return True
        return False

    def get_available_strategies(self) -> Dict[StateType, StrategyMode]:
        """
        Get all current strategy mappings.

        Returns:
            Dict[StateType, StrategyMode]: Copy of the current strategy map
        """
        return self._strategy_map.copy()


def get_strategy_for_state(state: StateType) -> StrategyMode:
    """
    Convenience function to get strategy mode for a given state.

    Args:
        state: The current assistant state

    Returns:
        StrategyMode: The selected strategy mode string
    """
    engine = StrategyEngine()
    return engine.get_strategy(state)
