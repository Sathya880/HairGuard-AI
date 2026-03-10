"""
Model Registry — Lazy Loading
==============================
Models are NOT loaded at startup. They load on first use and are cached.

Why:
  • Render free tier: 512 MB total RAM
  • PyTorch models are 80–200 MB each
  • Loading all at boot = OOM crash
  • Lazy loading = only pay for what you use, per request

Thread-safety: double-checked locking via threading.Lock
"""

import importlib
import logging
from threading import Lock
from typing import Any, Dict

logger = logging.getLogger(__name__)

_registry:     Dict[str, Any] = {}
_load_errors:  Dict[str, str] = {}
_load_lock = Lock()

# ─────────────────────────────────────────────────────────────────────────────
# Model factories — each returns a ready-to-use instance/callable
# ─────────────────────────────────────────────────────────────────────────────

def _import(module_path: str, class_name: str):
    """Import a class from a dotted module path."""
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


_factories: Dict[str, Any] = {

    # ── AI inference models (PyTorch / sklearn) ──────────────────────────────
    "hairloss_model": lambda: importlib.import_module(
        "analyzer.segment_inference").process_single_image,

    "dandruff_model": lambda: importlib.import_module(
        "analyzer.train_dandruff_detector").process_single_image,

    "hair_density_analyzer": lambda: _import(
        "analyzer.hair_density_analyzer", "HairDensityAnalyzer")(),

    # ── Domain engines ────────────────────────────────────────────────────────
    "lifestyle_analyzer": lambda: _import(
        "analyzer.lifestyle_analyzer", "LifestyleAnalyzer")(),

    "bayesian_root_cause": lambda: _import(
        "models.bayesian_root_cause_engine", "BayesianRootCauseEngine")(),

    "future_risk_model": lambda: _import(
        "models.future_risk_model", "FutureRiskModel")(),

    "adaptive_routine_engine": lambda: _import(
        "models.adaptive_routine_engine", "AdaptiveRoutineEngine")(),

    "suggestions_engine": lambda: _import(
        "models.suggestion_engine_v2", "SuggestionEngineV2")(),

    "remedies_engine": lambda: _import(
        "report.remedies_engine", "RemediesEngine")(),

    "progress_tracker": lambda: _import(
        "timeline.progress_tracker", "ProgressTrackerEngine")(),

    # ── Assistant engines ─────────────────────────────────────────────────────
    "strategy_engine": lambda: _import(
        "assistant.strategy_engine", "StrategyEngine")(),

    "simulation_interpreter": lambda: _import(
        "assistant.simulation_interpreter", "SimulationInterpreter")(),

    "weekly_review_engine": lambda: _import(
        "assistant.weekly_review_engine", "WeeklyReviewEngine")(),

    "behavior_engine": lambda: _import(
        "models.assistant_behavior_engine", "AssistantBehaviorEngine")(),
}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get(name: str) -> Any:
    """
    Return the model/engine instance for *name*.
    Loads it lazily on first call; subsequent calls return the cached instance.
    """
    # Fast path — already loaded
    if name in _registry:
        return _registry[name]

    # Propagate previous load failures immediately
    if name in _load_errors:
        raise RuntimeError(
            f"Model '{name}' previously failed to load: {_load_errors[name]}"
        )

    if name not in _factories:
        raise KeyError(f"Unknown model: '{name}'")

    # Slow path — load with lock (double-checked)
    with _load_lock:
        if name in _registry:          # another thread may have loaded it
            return _registry[name]

        logger.info(f"🔄 Lazy loading: {name}")
        try:
            instance = _factories[name]()
            _registry[name] = instance
            logger.info(f"✅ Ready: {name}")
            return instance
        except Exception as exc:
            logger.error(f"❌ Failed to load '{name}': {exc}")
            _load_errors[name] = str(exc)
            raise


def is_ready(name: str) -> bool:
    return name in _registry


def status() -> Dict[str, str]:
    """Snapshot of every registered model's load state (for /health)."""
    result = {}
    for name in _factories:
        if name in _registry:
            result[name] = "ready"
        elif name in _load_errors:
            result[name] = f"error: {_load_errors[name]}"
        else:
            result[name] = "not_loaded"
    return result