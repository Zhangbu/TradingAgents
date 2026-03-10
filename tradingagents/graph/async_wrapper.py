"""Async wrapper for TradingAgentsGraph to integrate with FastAPI."""

import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import date
from concurrent.futures import ThreadPoolExecutor
import logging

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.default_config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class AsyncCallbackHandler:
    """Handler for async callbacks during agent execution."""
    
    def __init__(self):
        self.callbacks: List[Callable] = []
    
    def add_callback(self, callback: Callable):
        """Add a callback function."""
        self.callbacks.append(callback)
    
    async def emit(self, event_type: str, data: Dict[str, Any]):
        """Emit an event to all registered callbacks."""
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_type, data)
                else:
                    callback(event_type, data)
            except Exception as e:
                logger.error(f"Callback error: {e}")


class AgentEventType:
    """Event types for agent execution."""
    AGENT_START = "agent_start"
    AGENT_THINKING = "agent_thinking"
    AGENT_TOOL_CALL = "agent_tool_call"
    AGENT_COMPLETE = "agent_complete"
    PROPOSAL_CREATED = "proposal_created"
    ERROR = "error"


class AsyncTradingAgentsGraph:
    """
    Async wrapper for TradingAgentsGraph.
    
    This class wraps the synchronous TradingAgentsGraph to work with
    FastAPI's async event loop using run_in_executor.
    """
    
    # Semaphore to limit concurrent agent executions
    _semaphore: Optional[asyncio.Semaphore] = None
    _executor: Optional[ThreadPoolExecutor] = None
    
    @classmethod
    def initialize(cls, max_concurrent: int = 3):
        """Initialize the class-level semaphore and executor."""
        cls._semaphore = asyncio.Semaphore(max_concurrent)
        cls._executor = ThreadPoolExecutor(max_workers=max_concurrent)
    
    @classmethod
    def shutdown(cls):
        """Shutdown the executor."""
        if cls._executor:
            cls._executor.shutdown(wait=True)
            cls._executor = None
    
    def __init__(
        self,
        selected_analysts: List[str] = None,
        debug: bool = False,
        config: Dict[str, Any] = None,
        callback_handler: Optional[AsyncCallbackHandler] = None,
    ):
        """
        Initialize the async wrapper.
        
        Args:
            selected_analysts: List of analyst types to include
            debug: Whether to run in debug mode
            config: Configuration dictionary
            callback_handler: Optional callback handler for events
        """
        if AsyncTradingAgentsGraph._semaphore is None:
            AsyncTradingAgentsGraph.initialize()
        
        self.selected_analysts = selected_analysts or ["market", "social", "news", "fundamentals"]
        self.debug = debug
        self.config = config or DEFAULT_CONFIG
        self.callback_handler = callback_handler or AsyncCallbackHandler()
        
        # Lazy initialization of the sync graph
        self._sync_graph: Optional[TradingAgentsGraph] = None
    
    @property
    def sync_graph(self) -> TradingAgentsGraph:
        """Lazy initialization of the synchronous TradingAgentsGraph."""
        if self._sync_graph is None:
            self._sync_graph = TradingAgentsGraph(
                selected_analysts=self.selected_analysts,
                debug=self.debug,
                config=self.config,
            )
        return self._sync_graph
    
    async def propagate(
        self,
        company_name: str,
        trade_date: date,
    ) -> tuple:
        """
        Run the trading agents graph asynchronously.
        
        Args:
            company_name: Stock symbol to analyze
            trade_date: Date for analysis
            
        Returns:
            Tuple of (final_state, processed_signal)
        """
        async with AsyncTradingAgentsGraph._semaphore:
            # Emit start event
            await self.callback_handler.emit(
                AgentEventType.AGENT_START,
                {
                    "symbol": company_name,
                    "date": str(trade_date),
                }
            )
            
            try:
                # Run the synchronous propagate in a thread pool
                loop = asyncio.get_event_loop()
                final_state, signal = await loop.run_in_executor(
                    AsyncTradingAgentsGraph._executor,
                    self.sync_graph.propagate,
                    company_name,
                    trade_date,
                )
                
                # Emit completion event
                await self.callback_handler.emit(
                    AgentEventType.AGENT_COMPLETE,
                    {
                        "symbol": company_name,
                        "signal": signal,
                        "final_decision": final_state.get("final_trade_decision", ""),
                    }
                )
                
                return final_state, signal
                
            except Exception as e:
                logger.error(f"Agent execution error: {e}")
                await self.callback_handler.emit(
                    AgentEventType.ERROR,
                    {
                        "symbol": company_name,
                        "error": str(e),
                    }
                )
                raise
    
    async def create_proposal(
        self,
        company_name: str,
        trade_date: date,
        exchange: str = "paper",
    ) -> Dict[str, Any]:
        """
        Run agents and create a trade proposal.
        
        Args:
            company_name: Stock symbol
            trade_date: Analysis date
            exchange: Target exchange
            
        Returns:
            Proposal dictionary with decision details
        """
        final_state, signal = await self.propagate(company_name, trade_date)
        
        # Extract decision from signal
        decision = self._parse_signal(signal)
        
        proposal = {
            "symbol": company_name.upper(),
            "side": decision.get("side", "hold"),
            "quantity": decision.get("quantity", 0),
            "confidence": decision.get("confidence", 0.0),
            "reasoning": final_state.get("final_trade_decision", ""),
            "market_report": final_state.get("market_report", ""),
            "sentiment_report": final_state.get("sentiment_report", ""),
            "news_report": final_state.get("news_report", ""),
            "fundamentals_report": final_state.get("fundamentals_report", ""),
            "investment_debate": final_state.get("investment_debate_state", {}).get("judge_decision", ""),
            "risk_debate": final_state.get("risk_debate_state", {}).get("judge_decision", ""),
            "exchange": exchange,
        }
        
        # Emit proposal created event
        await self.callback_handler.emit(
            AgentEventType.PROPOSAL_CREATED,
            proposal
        )
        
        return proposal
    
    def _parse_signal(self, signal: str) -> Dict[str, Any]:
        """Parse the trading signal to extract decision details."""
        signal_lower = signal.lower() if signal else ""
        
        # Determine side
        if "buy" in signal_lower:
            side = "buy"
        elif "sell" in signal_lower:
            side = "sell"
        else:
            side = "hold"
        
        # Default quantity (should be determined by position sizing)
        quantity = 1.0
        
        # Extract confidence if mentioned
        confidence = 0.5  # Default confidence
        
        return {
            "side": side,
            "quantity": quantity,
            "confidence": confidence,
            "raw_signal": signal,
        }
    
    async def reflect_and_remember(
        self,
        returns_losses: float,
    ) -> None:
        """
        Reflect on decisions and update memory.
        
        Args:
            returns_losses: The actual returns/losses from the trade
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            AsyncTradingAgentsGraph._executor,
            self.sync_graph.reflect_and_remember,
            returns_losses,
        )