from flask import request, jsonify
import logging

from assistant.assistant_controller import create_assistant_response
from assistant.context_builder import AssistantContextBuilder
from assistant.hair_coach_engine import generate_coach_greeting
from assistant.state_classifier import classify_state, AssistantContext
from assistant.strategy_engine import StrategyEngine
from assistant.simulation_interpreter import SimulationInterpreter
from assistant.weekly_review_engine import WeeklyReviewEngine
from models.assistant_behavior_engine import AssistantBehaviorEngine

# ─────────────────────────────────────────────────────────────────────────────
# MODULE-LEVEL SINGLETONS  ← the latency fix
#
# Assistant engines are instantiated once at import time (server startup).
# Route handlers reuse the same warm objects on every request instead of
# paying the construction cost (~1–2 s) on the first call.
# ─────────────────────────────────────────────────────────────────────────────
_strategy_engine        = StrategyEngine()
_simulation_interpreter = SimulationInterpreter()
_weekly_review_engine   = WeeklyReviewEngine()
_behavior_engine        = AssistantBehaviorEngine()

logger = logging.getLogger(__name__)


def register_assistant_routes(app):

    # ─────────────────────────────────────────
    # MAIN ASSISTANT RESPONSE
    # ─────────────────────────────────────────
    @app.route("/assistant", methods=["POST"])
    def assistant():
        try:
            data = request.get_json(force=True)

            user_reports     = data.get("userReports", [])
            progress_result  = data.get("progressResult", {})

            context_builder = AssistantContextBuilder(
                user_reports=user_reports,
                routine_adherence_data=data.get("routineAdherenceData", {}),
                lifestyle_score_trend=data.get("lifestyleScoreTrend", {}),
                root_cause_result=data.get("rootCauseResult", {}),
                progress_result=progress_result
            )

            context = context_builder.build()

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

            return jsonify({
                "success": True,
                "assistant": response
            })

        except Exception as e:
            logger.error(f"Assistant error: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500


    # ─────────────────────────────────────────
    # ASSISTANT STATE CLASSIFIER
    # ─────────────────────────────────────────
    @app.route("/assistant/state", methods=["POST"])
    def assistant_state():
        try:
            data = request.get_json(force=True)

            context = AssistantContextBuilder(
                user_reports=data.get("userReports", []),
                routine_adherence_data=data.get("routineAdherenceData", {}),
                lifestyle_score_trend=data.get("lifestyleScoreTrend", {}),
                root_cause_result=data.get("rootCauseResult", {}),
                progress_result=data.get("progressResult", {})
            ).build()

            state    = classify_state(context)
            strategy = _strategy_engine.get_strategy(state)

            return jsonify({
                "success":  True,
                "state":    state,
                "strategy": strategy
            })

        except Exception as e:
            logger.error(f"Assistant state error: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500


    # ─────────────────────────────────────────
    # ASSISTANT SIMULATION INTERPRETER
    # ─────────────────────────────────────────
    @app.route("/assistant/simulate", methods=["POST"])
    def assistant_simulate():
        try:
            data = request.get_json(force=True)

            interpretation = _simulation_interpreter.interpret(
                data.get("simulationOutput", {}),
                data.get("currentScore", 50)
            )

            return jsonify({
                "success":        True,
                "interpretation": _simulation_interpreter.to_dict(interpretation)
            })

        except Exception as e:
            logger.error(f"Simulation interpreter error: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500


    # ─────────────────────────────────────────
    # WEEKLY REVIEW
    # ─────────────────────────────────────────
    @app.route("/assistant/weekly-review", methods=["POST"])
    def assistant_weekly_review():
        try:
            data = request.get_json(force=True)

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

                review = _weekly_review_engine.generate_review(_d2c(lc), _d2c(pc))

            else:
                reports = data.get("reports", [])

                if len(reports) < 2:
                    return jsonify({
                        "success": True,
                        "review": {
                            "summary_message": "Not enough data for a weekly review yet."
                        }
                    })

                mid = len(reports) // 2

                current_ctx = AssistantContextBuilder(
                    user_reports=reports[:mid] if mid > 0 else reports[:1]
                ).build()

                previous_ctx = AssistantContextBuilder(
                    user_reports=reports[mid:] if mid < len(reports) else reports[:1]
                ).build()

                review = _weekly_review_engine.generate_review(current_ctx, previous_ctx)

            return jsonify({
                "success": True,
                "review":  _weekly_review_engine.to_dict(review)
            })

        except Exception as e:
            logger.error(f"Weekly review error: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500


    # ─────────────────────────────────────────
    # ASSISTANT BEHAVIOR ANALYSIS
    # ─────────────────────────────────────────
    @app.route("/assistant-behavior", methods=["POST"])
    def assistant_behavior():
        try:
            data = request.get_json(force=True)

            result = _behavior_engine.analyze_behavior(
                current_report=data.get("currentReport", {}),
                previous_reports=data.get("previousReports", []),
                routine_adherence=data.get("routineAdherence"),
            )

            return jsonify({
                "success":  True,
                "behavior": result
            })

        except Exception as e:
            logger.error(f"Assistant behavior error: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500