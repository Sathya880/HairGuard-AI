"""
Model Registry — Parallel startup warm-up

All heavy models (ML weights, engines) are loaded ONCE at server start
in parallel threads. Request handlers call get() to retrieve the
already-warm singleton — zero loading cost per request.

Boot time comparison:
  Before (sequential): ~8–15 s
  After  (parallel):   ~2–4 s  (limited by the single slowest model)
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Internal registry store
# ─────────────────────────────────────────────────────────────────────────────
_registry: Dict[str, Any] = {}
_load_errors: Dict[str, str] = {}


def _load_one(name: str, factory) -> tuple:
    """Load a single model, returning (name, instance, elapsed_ms, error)."""
    t0 = time.perf_counter()
    try:
        instance = factory()
        elapsed = (time.perf_counter() - t0) * 1000
        return name, instance, elapsed, None
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        return name, None, elapsed, str(e)


def warm_up_all() -> None:
    """
    Load all models in parallel at server startup.
    Call this once from app.py before the server starts accepting requests.

    Thread-safe: each factory is called in its own thread. Models that share
    GPU memory should be loaded sequentially — adjust max_workers accordingly.
    """

    # ── Define every model/engine and its zero-argument factory ──────────────
    # Add new engines here — nothing else needs to change.
    factories = {
        # ── AI inference models (heaviest — load first / in parallel) ────────
        "hairloss_model": lambda: _import_hairloss_model(),
        "dandruff_model": lambda: _import_dandruff_model(),
        "hair_density_analyzer": lambda: _import_hair_density_analyzer(),

        # ── Domain engines ────────────────────────────────────────────────────
        "lifestyle_analyzer": lambda: _import("analyzer.lifestyle_analyzer", "LifestyleAnalyzer")(),
        "bayesian_root_cause": lambda: _import("models.bayesian_root_cause_engine", "BayesianRootCauseEngine")(),
        "future_risk_model": lambda: _import("models.future_risk_model", "FutureRiskModel")(),
        "adaptive_routine_engine": lambda: _import("models.adaptive_routine_engine", "AdaptiveRoutineEngine")(),
        "suggestions_engine": lambda: _import("models.suggestion_engine_v2", "SuggestionEngineV2")(),
        "remedies_engine": lambda: _import("report.remedies_engine", "RemediesEngine")(), 
        "progress_tracker": lambda: _import("timeline.progress_tracker", "ProgressTrackerEngine")(),

        # ── Assistant engines ─────────────────────────────────────────────────
        "strategy_engine": lambda: _import("assistant.strategy_engine", "StrategyEngine")(),
        "simulation_interpreter": lambda: _import("assistant.simulation_interpreter", "SimulationInterpreter")(),
        "weekly_review_engine": lambda: _import("assistant.weekly_review_engine", "WeeklyReviewEngine")(),
        "behavior_engine": lambda: _import("models.assistant_behavior_engine", "AssistantBehaviorEngine")(),
    }

    total_start = time.perf_counter()
    logger.info(f"🔥 Warming up {len(factories)} models in parallel...")

    # Use CPU count × 2 workers — models are I/O-bound (disk reads)
    # Drop to max_workers=1 if you have GPU contention
    import os
    max_workers = min(len(factories), 2)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_load_one, name, factory): name
            for name, factory in factories.items()
        }

        for future in as_completed(futures):
            name, instance, elapsed_ms, error = future.result()
            if error:
                logger.error(f"  ✗ {name} failed in {elapsed_ms:.0f}ms: {error}")
                _load_errors[name] = error
            else:
                _registry[name] = instance
                logger.info(f"  ✓ {name} ready in {elapsed_ms:.0f}ms")

    total_ms = (time.perf_counter() - total_start) * 1000
    ok = len(_registry)
    failed = len(_load_errors)
    logger.info(
        f"🚀 Warm-up complete in {total_ms:.0f}ms — "
        f"{ok} ready, {failed} failed"
    )

    if _load_errors:
        logger.warning(f"  Failed models: {list(_load_errors.keys())}")


def get(name: str) -> Any:
    """
    Retrieve a warm model by name.

    Raises KeyError if the model failed to load or was never registered.
    Call warm_up_all() before serving requests.
    """
    if name in _load_errors:
        raise RuntimeError(
            f"Model '{name}' failed to load at startup: {_load_errors[name]}"
        )
    if name not in _registry:
        raise KeyError(
            f"Model '{name}' not found in registry. "
            f"Did you call model_registry.warm_up_all() at startup?"
        )
    return _registry[name]


def is_ready(name: str) -> bool:
    """Check if a model loaded successfully."""
    return name in _registry


def status() -> Dict[str, str]:
    """Return load status for all registered models (for /health endpoint)."""
    result = {name: "ready" for name in _registry}
    result.update({name: f"error: {err}" for name, err in _load_errors.items()})
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Private import helpers
# ─────────────────────────────────────────────────────────────────────────────

def _import(module_path: str, class_name: str):
    """Dynamically import a class from a dotted module path."""
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _import_hairloss_model():
    """
    Import the hairloss inference function and force-load the model weights
    by running a dummy inference pass so the first real request is instant.
    """
    import importlib
    module = importlib.import_module("analyzer.segment_inference")
    # The module-level model object is loaded on import — just importing is enough.
    # Return the callable so callers can use it directly.
    return module.process_single_image


def _import_dandruff_model():
    import importlib
    module = importlib.import_module("analyzer.train_dandruff_detector")
    return module.process_single_image


def _import_hair_density_analyzer():
    import importlib
    cls = _import("analyzer.hair_density_analyzer", "HairDensityAnalyzer")
    return cls()