"""
Assistant Controller Module

This module provides the AssistantController class for orchestrating
the behavioral AI assistant logic with production-level architecture.

Features:
- Clean imports
- Proper dependency injection
- Logging hooks
- Scalable design
- Ready for API integration
"""

import logging
from dataclasses import dataclass, field
from typing import Literal, Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from functools import wraps

# =====================================================
# LOGGING CONFIGURATION
# =====================================================
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =====================================================
# TYPE DEFINITIONS
# =====================================================
ToneType = Literal[
    "urgent", "firm", "supportive", "encouraging", "analytical", "neutral"
]
PriorityLevel = Literal["critical", "high", "medium", "low"]
StateType = Literal[
    "improving",
    "plateau",
    "declining",
    "high_risk",
    "low_discipline",
    "uncertain",
    "neutral",
]
StrategyMode = Literal[
    "urgency",
    "intervention",
    "optimization",
    "accountability",
    "reinforcement",
    "data_collection",
    "monitoring",
]


# =====================================================
# LOGGING HOOKS
# =====================================================
class LoggingHooks:
    """Centralized logging hooks for the assistant."""

    @staticmethod
    def on_context_built(context: Dict[str, Any]) -> None:
        logger.info(
            f"Context built: hair_score={context.get('hair_score')}, "
            f"trend={context.get('trend')}"
        )

    @staticmethod
    def on_state_classified(state: StateType) -> None:
        logger.info(f"State classified: {state}")

    @staticmethod
    def on_strategy_selected(strategy: StrategyMode) -> None:
        logger.info(f"Strategy selected: {strategy}")

    @staticmethod
    def on_escalation(
        state: StateType, old_strategy: StrategyMode, new_strategy: StrategyMode
    ) -> None:
        logger.warning(
            f"Escalation triggered: {state} - " f"{old_strategy} -> {new_strategy}"
        )

    @staticmethod
    def on_coaching_generated(tone: ToneType, priority: PriorityLevel) -> None:
        logger.info(f"Coaching generated: tone={tone}, priority={priority}")

    @staticmethod
    def on_memory_updated(entry_count: int) -> None:
        logger.debug(f"Memory updated: {entry_count} entries")


# =====================================================
# MEMORY ENGINE (Dependency Injected)
# =====================================================
@dataclass
class MemoryEntry:
    """Entry for tracking assistant memory."""

    timestamp: datetime
    state: StateType
    strategy: StrategyMode
    message_preview: str
    was_escalated: bool = False


class MemoryEngine:
    """
    Memory engine for tracking assistant interactions.

    Can be injected or used standalone.
    """

    MAX_HISTORY = 10
    REPETITION_THRESHOLD = 3

    def __init__(self, max_history: int = 10, repetition_threshold: int = 3):
        """Initialize with configurable parameters."""
        self.history: List[MemoryEntry] = []
        self.MAX_HISTORY = max_history
        self.REPETITION_THRESHOLD = repetition_threshold
        logger.debug(f"MemoryEngine initialized with max_history={max_history}")

    def check_repetition(self, state: StateType, strategy: StrategyMode) -> bool:
        """Check if the same state/strategy combination is being repeated."""
        if len(self.history) < self.REPETITION_THRESHOLD:
            return False

        recent_entries = self.history[-self.REPETITION_THRESHOLD :]
        matching = [
            e for e in recent_entries if e.state == state and e.strategy == strategy
        ]

        return len(matching) >= self.REPETITION_THRESHOLD

    def should_escalate(self, state: StateType, strategy: StrategyMode) -> bool:
        """Determine if strategy should be escalated."""
        if self.check_repetition(state, strategy):
            return True

        if strategy in ["urgency", "intervention"]:
            recent_escalated = [e for e in self.history[-5:] if e.was_escalated]
            if not recent_escalated:
                return True

        return False

    def get_escalated_strategy(self, current_strategy: StrategyMode) -> StrategyMode:
        """Get an escalated version of the current strategy."""
        escalation_map = {
            "monitoring": "data_collection",
            "data_collection": "accountability",
            "accountability": "intervention",
            "intervention": "urgency",
            "reinforcement": "monitoring",
            "optimization": "accountability",
            "urgency": "urgency",
        }
        return escalation_map.get(current_strategy, "monitoring")

    def add_entry(
        self,
        state: StateType,
        strategy: StrategyMode,
        message: str,
        was_escalated: bool = False,
    ) -> None:
        """Add an entry to memory."""
        entry = MemoryEntry(
            timestamp=datetime.now(),
            state=state,
            strategy=strategy,
            message_preview=message[:50] if message else "",
            was_escalated=was_escalated,
        )
        self.history.append(entry)

        if len(self.history) > self.MAX_HISTORY:
            self.history = self.history[-self.MAX_HISTORY :]

        LoggingHooks.on_memory_updated(len(self.history))

    def get_recent_states(self, count: int = 5) -> List[StateType]:
        """Get recent states from memory."""
        return [e.state for e in self.history[-count:]]

    def clear(self) -> None:
        """Clear memory history."""
        self.history = []
        logger.debug("Memory cleared")


# =====================================================
# DEPENDENCY INJECTION CONTAINER
# =====================================================
class DIContainer:
    """
    Simple dependency injection container for the assistant.
    """

    def __init__(self):
        self._services: Dict[str, Any] = {}

    def register(self, name: str, service: Any) -> None:
        """Register a service."""
        self._services[name] = service
        logger.debug(f"Registered service: {name}")

    def get(self, name: str) -> Any:
        """Get a registered service."""
        return self._services.get(name)

    def has(self, name: str) -> bool:
        """Check if service is registered."""
        return name in self._services


# Global container for dependency injection
_container = DIContainer()


def register_services(
    context_builder: Any = None,
    state_classifier: Any = None,
    strategy_engine: Any = None,
    coaching_engine: Any = None,
    memory_engine: MemoryEngine = None,
) -> None:
    """Register services in the global container."""
    if context_builder:
        _container.register("context_builder", context_builder)
    if state_classifier:
        _container.register("state_classifier", state_classifier)
    if strategy_engine:
        _container.register("strategy_engine", strategy_engine)
    if coaching_engine:
        _container.register("coaching_engine", coaching_engine)
    if memory_engine:
        _container.register("memory_engine", memory_engine)


# =====================================================
# ASSISTANT RESPONSE
# =====================================================
@dataclass
class AssistantResponse:
    """Structured response from the assistant controller."""

    state: StateType
    strategy: StrategyMode
    tone: ToneType
    priority: PriorityLevel
    message: str
    was_escalated: bool = False
    memory_snapshot: List[Dict[str, Any]] = field(default_factory=list)
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =====================================================
# ASSISTANT CONTROLLER
# =====================================================
class AssistantController:
    """
    Controller for orchestrating the behavioral AI assistant.

    Supports dependency injection for all components.
    Ready for API integration.
    """

    def __init__(
        self,
        # Data inputs
        user_reports: Optional[List[Dict[str, Any]]] = None,
        routine_adherence_data: Optional[Dict[str, Any]] = None,
        lifestyle_score_trend: Optional[Dict[str, Any]] = None,
        root_cause_result: Optional[Dict[str, Any]] = None,
        progress_result: Optional[Dict[str, Any]] = None,
        # Dependency injection
        context_builder: Any = None,
        state_classifier: Any = None,
        strategy_engine: Any = None,
        coaching_engine: Any = None,
        memory_engine: MemoryEngine = None,
        # Configuration
        enable_logging: bool = True,
    ):
        self._enable_logging = enable_logging

        # Store raw inputs
        self._user_reports = user_reports or []
        self._routine_adherence_data = routine_adherence_data or {}
        self._lifestyle_score_trend = lifestyle_score_trend or {}
        self._root_cause_result = root_cause_result or {}
        self._progress_result = progress_result or {}

        # Initialize or inject dependencies
        self._init_dependencies(
            context_builder=context_builder,
            state_classifier=state_classifier,
            strategy_engine=strategy_engine,
            coaching_engine=coaching_engine,
            memory_engine=memory_engine,
        )

        logger.info("AssistantController initialized")

    def _init_dependencies(
        self,
        context_builder: Any,
        state_classifier: Any,
        strategy_engine: Any,
        coaching_engine: Any,
        memory_engine: MemoryEngine,
    ) -> None:
        """Initialize dependencies with injection priority."""
        # Context Builder
        if context_builder:
            self.context_builder = context_builder
        else:
            from .context_builder import AssistantContextBuilder

            self.context_builder = AssistantContextBuilder(
                user_reports=self._user_reports,
                routine_adherence_data=self._routine_adherence_data,
                lifestyle_score_trend=self._lifestyle_score_trend,
                root_cause_result=self._root_cause_result,
                progress_result=self._progress_result,
            )

        # State Classifier
        if state_classifier:
            self.state_classifier = state_classifier
        else:
            from .state_classifier import StateClassifier, classify_state

            self.state_classifier = StateClassifier
            self._classify_state = classify_state

        # Strategy Engine
        if strategy_engine:
            self.strategy_engine = strategy_engine
        else:
            from .strategy_engine import StrategyEngine

            self.strategy_engine = StrategyEngine()

        # Coaching Engine
        if coaching_engine:
            self.coaching_engine = coaching_engine
        else:
            from .coaching_engine import CoachingEngine

            self.coaching_engine = CoachingEngine()

        # Memory Engine
        if memory_engine:
            self.memory_engine = memory_engine
        else:
            container_memory = _container.get("memory_engine")
            if container_memory:
                self.memory_engine = container_memory
            else:
                self.memory_engine = MemoryEngine()

    def process(self) -> AssistantResponse:
        """Process the assistant flow and generate a response."""
        logger.info("Starting assistant processing flow")

        # Step 1: Build context
        context = self.context_builder.build()
        context_dict = (
            self.context_builder.to_dict()
            if hasattr(self.context_builder, "to_dict")
            else {}
        )

        if self._enable_logging:
            LoggingHooks.on_context_built(context_dict)

        # Step 2: Classify state
        state = self._classify_state(context)

        if self._enable_logging:
            LoggingHooks.on_state_classified(state)

        # Step 3: Select strategy
        strategy = self.strategy_engine.get_strategy(state)

        if self._enable_logging:
            LoggingHooks.on_strategy_selected(strategy)

        # Step 4: Check memory for repetition
        was_escalated = False
        if self.memory_engine.should_escalate(state, strategy):
            old_strategy = strategy
            strategy = self.memory_engine.get_escalated_strategy(strategy)
            was_escalated = True

            if self._enable_logging:
                LoggingHooks.on_escalation(state, old_strategy, strategy)

        # Step 5: Generate coaching response
        coaching_response = self.coaching_engine.generate_coaching(strategy, context)

        if self._enable_logging:
            LoggingHooks.on_coaching_generated(
                coaching_response.tone_type, coaching_response.priority_level
            )

        # Step 6: Update memory
        self.memory_engine.add_entry(
            state, strategy, coaching_response.message, was_escalated
        )

        # Build response
        response = AssistantResponse(
            state=state,
            strategy=strategy,
            tone=coaching_response.tone_type,
            priority=coaching_response.priority_level,
            message=coaching_response.message,
            was_escalated=was_escalated,
            memory_snapshot=[
                {
                    "timestamp": e.timestamp.isoformat(),
                    "state": e.state,
                    "strategy": e.strategy,
                    "was_escalated": e.was_escalated,
                }
                for e in self.memory_engine.history[-5:]
            ],
            context_snapshot=context_dict,
            metadata={
                "processed_at": datetime.now().isoformat(),
                "reports_count": len(self._user_reports),
            },
        )

        logger.info(
            f"Assistant processing complete: state={state}, strategy={strategy}"
        )

        return response

    def process_with_context(self, context: Any) -> AssistantResponse:
        """Process with pre-built context."""
        state = self._classify_state(context)

        if self._enable_logging:
            LoggingHooks.on_state_classified(state)

        strategy = self.strategy_engine.get_strategy(state)

        if self._enable_logging:
            LoggingHooks.on_strategy_selected(strategy)

        was_escalated = False
        if self.memory_engine.should_escalate(state, strategy):
            old_strategy = strategy
            strategy = self.memory_engine.get_escalated_strategy(strategy)
            was_escalated = True

            if self._enable_logging:
                LoggingHooks.on_escalation(state, old_strategy, strategy)

        coaching_response = self.coaching_engine.generate_coaching(strategy, context)

        if self._enable_logging:
            LoggingHooks.on_coaching_generated(
                coaching_response.tone_type, coaching_response.priority_level
            )

        self.memory_engine.add_entry(
            state, strategy, coaching_response.message, was_escalated
        )

        return AssistantResponse(
            state=state,
            strategy=strategy,
            tone=coaching_response.tone_type,
            priority=coaching_response.priority_level,
            message=coaching_response.message,
            was_escalated=was_escalated,
            memory_snapshot=[
                {
                    "timestamp": e.timestamp.isoformat(),
                    "state": e.state,
                    "strategy": e.strategy,
                    "was_escalated": e.was_escalated,
                }
                for e in self.memory_engine.history[-5:]
            ],
            metadata={
                "processed_at": datetime.now().isoformat(),
            },
        )

    def get_memory(self) -> List[Dict[str, Any]]:
        """Get current memory snapshot."""
        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "state": e.state,
                "strategy": e.strategy,
                "message_preview": e.message_preview,
                "was_escalated": e.was_escalated,
            }
            for e in self.memory_engine.history
        ]

    def clear_memory(self) -> None:
        """Clear the memory engine."""
        self.memory_engine.clear()

    def to_dict(self, response: AssistantResponse) -> Dict[str, Any]:
        """Convert response to dictionary for API output."""
        return {
            "state": response.state,
            "strategy": response.strategy,
            "tone": response.tone,
            "priority": response.priority,
            "message": response.message,
            "was_escalated": response.was_escalated,
            "memory_snapshot": response.memory_snapshot,
            "metadata": response.metadata,
        }


# =====================================================
# CONVENIENCE FUNCTIONS
# =====================================================
def create_assistant_response(
    user_reports: Optional[List[Dict[str, Any]]] = None,
    routine_adherence_data: Optional[Dict[str, Any]] = None,
    lifestyle_score_trend: Optional[Dict[str, Any]] = None,
    root_cause_result: Optional[Dict[str, Any]] = None,
    progress_result: Optional[Dict[str, Any]] = None,
    enable_logging: bool = True,
) -> Dict[str, Any]:
    """
    Convenience function to create an assistant response.
    """
    controller = AssistantController(
        user_reports=user_reports,
        routine_adherence_data=routine_adherence_data,
        lifestyle_score_trend=lifestyle_score_trend,
        root_cause_result=root_cause_result,
        progress_result=progress_result,
        enable_logging=enable_logging,
    )
    response = controller.process()
    return controller.to_dict(response)


def create_assistant_controller_with_injection(
    context_builder: Any = None,
    state_classifier: Any = None,
    strategy_engine: Any = None,
    coaching_engine: Any = None,
    memory_engine: MemoryEngine = None,
    enable_logging: bool = True,
) -> AssistantController:
    """
    Factory function for creating controller with dependency injection.
    """
    return AssistantController(
        context_builder=context_builder,
        state_classifier=state_classifier,
        strategy_engine=strategy_engine,
        coaching_engine=coaching_engine,
        memory_engine=memory_engine,
        enable_logging=enable_logging,
    )


# =====================================================
# EXPORTS
# =====================================================
__all__ = [
    "AssistantController",
    "AssistantResponse",
    "MemoryEngine",
    "MemoryEntry",
    "LoggingHooks",
    "DIContainer",
    "create_assistant_response",
    "create_assistant_controller_with_injection",
    "register_services",
]