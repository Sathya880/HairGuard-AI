"""
Assistant Engine Routes
========================
Reasoning & coaching layer — registered directly onto the main Flask app.

All engines are instantiated once at import time (singleton pattern) to
avoid paying construction cost on every request.
"""

import logging

from flask import request, jsonify

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Lazy singleton loader
# We defer imports so the server boots instantly even if optional deps are slow.
# ─────────────────────────────────────────────────────────────────────────────

_singletons: dict = {}


def _get(key: str):
    """Return a cached engine instance, creating it on first call."""
    if key not in _singletons:
        if key == "strategy_engine":
            from assistant.strategy_engine import StrategyEngine
            _singletons[key] = StrategyEngine()
        elif key == "simulation_interpreter":
            from assistant.simulation_interpreter import SimulationInterpreter
            _singletons[key] = SimulationInterpreter()
        elif key == "weekly_review_engine":
            from assistant.weekly_review_engine import WeeklyReviewEngine
            _singletons[key] = WeeklyReviewEngine()
        elif key == "behavior_engine":
            from models.assistant_behavior_engine import AssistantBehaviorEngine
            _singletons[key] = AssistantBehaviorEngine()
        else:
            raise KeyError(f"Unknown singleton: {key}")
    return _singletons[key]


# ─────────────────────────────────────────────────────────────────────────────
# Route registration
# ─────────────────────────────────────────────────────────────────────────────

def register_assistant_routes(app):

    # ─────────────────────────────────────────
    # MAIN ASSISTANT RESPONSE
    # ─────────────────────────────────────────
    @app.route("/assistant", methods=["POST"])
    def assistant():
        try:
            from assistant.assistant_controller import create_assistant_response
            from assistant.context_builder import AssistantContextBuilder
            from assistant.hair_coach_engine import generate_coach_greeting

            data = request.get_json(force=True) or {}

            user_reports    = data.get("userReports", [])
            progress_result = data.get("progressResult", {})

            context = AssistantContextBuilder(
                user_reports=user_reports,
                routine_adherence_data=data.get("routineAdherenceData", {}),
                lifestyle_score_trend=data.get("lifestyleScoreTrend", {}),
                root_cause_result=data.get("rootCauseResult", {}),
                progress_result=progress_result,
            ).build()

            response = create_assistant_response(
                user_reports=user_reports,
                routine_adherence_data=data.get("routineAdherenceData", {}),
                lifestyle_score_trend=data.get("lifestyleScoreTrend", {}),
                root_cause_result=data.get("rootCauseResult", {}),
                progress_result=progress_result,
                enable_logging=data.get("enableLogging", True),
            )

            latest_report = user_reports[0] if user_reports else {}
            response["greetingMessage"] = generate_coach_greeting(
                report=latest_report,
                progress_result=progress_result,
                trend=context.trend,
                reports_count=context.reports_count,
            )

            return jsonify({"success": True, "assistant": response})

        except Exception as e:
            logger.error(f"Assistant error: {e}", exc_info=True)
            return jsonify({"success": False, "error": str(e)}), 500

    # ─────────────────────────────────────────
    # STATE CLASSIFIER
    # ─────────────────────────────────────────
    @app.route("/assistant/state", methods=["POST"])
    def assistant_state():
        try:
            from assistant.context_builder import AssistantContextBuilder
            from assistant.state_classifier import classify_state

            data = request.get_json(force=True) or {}

            context = AssistantContextBuilder(
                user_reports=data.get("userReports", []),
                routine_adherence_data=data.get("routineAdherenceData", {}),
                lifestyle_score_trend=data.get("lifestyleScoreTrend", {}),
                root_cause_result=data.get("rootCauseResult", {}),
                progress_result=data.get("progressResult", {}),
            ).build()

            state    = classify_state(context)
            strategy = _get("strategy_engine").get_strategy(state)

            return jsonify({"success": True, "state": state, "strategy": strategy})

        except Exception as e:
            logger.error(f"Assistant state error: {e}", exc_info=True)
            return jsonify({"success": False, "error": str(e)}), 500

    # ─────────────────────────────────────────
    # SIMULATION INTERPRETER
    # ─────────────────────────────────────────
    @app.route("/assistant/simulate", methods=["POST"])
    def assistant_simulate():
        try:
            data           = request.get_json(force=True) or {}
            interp         = _get("simulation_interpreter")
            interpretation = interp.interpret(
                data.get("simulationOutput", {}),
                data.get("currentScore", 50),
            )
            return jsonify({
                "success":        True,
                "interpretation": interp.to_dict(interpretation),
            })

        except Exception as e:
            logger.error(f"Simulation error: {e}", exc_info=True)
            return jsonify({"success": False, "error": str(e)}), 500

    # ─────────────────────────────────────────
    # WEEKLY REVIEW
    # ─────────────────────────────────────────
    @app.route("/assistant/weekly-review", methods=["POST"])
    def assistant_weekly_review():
        try:
            from assistant.context_builder import AssistantContextBuilder
            from assistant.state_classifier import AssistantContext

            data   = request.get_json(force=True) or {}
            engine = _get("weekly_review_engine")

            lc = data.get("latestContext")
            pc = data.get("previousContext")

            if lc and pc:
                def _d2c(d):
                    return AssistantContext(
                        hair_score=float(d.get("hair_score", 50)),
                        previous_score=float(d.get("previous_score", 50)),
                        routine_adherence=float(d.get("routine_adherence", 50)),
                        risk_6_month=float(d.get("risk_6_month", 0)),
                        trend=d.get("trend", "stable"),
                        reports_count=int(d.get("reports_count", 1)),
                        confidence=float(d.get("confidence", 60)),
                        data_strength=d.get("data_strength", "moderate"),
                        root_cause=d.get("root_cause"),
                    )
                review = engine.generate_review(_d2c(lc), _d2c(pc))

            else:
                reports = data.get("reports", [])
                if len(reports) < 2:
                    return jsonify({
                        "success": True,
                        "review": {"summary_message": "Not enough data for a weekly review yet."},
                    })
                mid          = len(reports) // 2
                current_ctx  = AssistantContextBuilder(user_reports=reports[:mid] or reports[:1]).build()
                previous_ctx = AssistantContextBuilder(user_reports=reports[mid:] or reports[:1]).build()
                review       = engine.generate_review(current_ctx, previous_ctx)

            return jsonify({"success": True, "review": engine.to_dict(review)})

        except Exception as e:
            logger.error(f"Weekly review error: {e}", exc_info=True)
            return jsonify({"success": False, "error": str(e)}), 500

    # ─────────────────────────────────────────
    # BEHAVIOR ANALYSIS
    # ─────────────────────────────────────────
    @app.route("/assistant-behavior", methods=["POST"])
    def assistant_behavior():
        try:
            data   = request.get_json(force=True) or {}
            result = _get("behavior_engine").analyze_behavior(
                current_report=data.get("currentReport", {}),
                previous_reports=data.get("previousReports", []),
                routine_adherence=data.get("routineAdherence"),
            )
            return jsonify({"success": True, "behavior": result})

        except Exception as e:
            logger.error(f"Behavior error: {e}", exc_info=True)
            return jsonify({"success": False, "error": str(e)}), 500