from __future__ import annotations

from datetime import date, datetime
from typing import Any

from dotenv import load_dotenv

from backend.app.schemas.analysis import AnalysisArtifacts, AnalysisExecutionResult, AnalysisRequest
from tradingagents.default_config import build_default_config
from tradingagents.graph.trading_graph import TradingAgentsGraph


class TradingAgentsAnalysisRunner:
    """Runs the current TradingAgents graph and normalizes output for the API."""

    def __init__(self) -> None:
        load_dotenv()
        load_dotenv(".env.enterprise", override=False)

    def run(self, request: AnalysisRequest) -> AnalysisExecutionResult:
        config = build_default_config()

        if request.llm_provider:
            config["llm_provider"] = request.llm_provider
        if request.deep_think_llm:
            config["deep_think_llm"] = request.deep_think_llm
        if request.quick_think_llm:
            config["quick_think_llm"] = request.quick_think_llm
        if request.max_debate_rounds is not None:
            config["max_debate_rounds"] = request.max_debate_rounds
        if request.max_risk_discuss_rounds is not None:
            config["max_risk_discuss_rounds"] = request.max_risk_discuss_rounds

        graph = TradingAgentsGraph(
            selected_analysts=request.selected_analysts,
            debug=False,
            config=config,
        )
        trade_date = request.trade_date or "latest"
        final_state, processed_signal = graph.propagate(request.symbol, trade_date)

        artifacts = AnalysisArtifacts(
            market_report=final_state.get("market_report"),
            sentiment_report=final_state.get("sentiment_report"),
            news_report=final_state.get("news_report"),
            fundamentals_report=final_state.get("fundamentals_report"),
            investment_plan=final_state.get("investment_plan"),
            trader_investment_plan=final_state.get("trader_investment_plan"),
            final_trade_decision=final_state.get("final_trade_decision"),
            processed_signal=processed_signal,
            raw_state=self._make_json_safe(final_state),
        )
        return AnalysisExecutionResult(artifacts=artifacts)

    def _make_json_safe(self, value: Any) -> Any:
        """Convert graph state to a JSON-safe structure for durable storage."""
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, dict):
            return {str(key): self._make_json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._make_json_safe(item) for item in value]
        return repr(value)
