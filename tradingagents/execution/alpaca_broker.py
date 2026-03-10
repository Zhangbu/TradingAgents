"""
Alpaca Broker Implementation - Real trading with Alpaca Markets API.

Alpaca provides:
- Commission-free stock trading
- Crypto trading
- Paper trading accounts
- Real-time market data
- Historical data API
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal

try:
    import alpaca
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import (
        MarketOrderRequest,
        LimitOrderRequest,
        StopOrderRequest,
        StopLimitOrderRequest,
        GetOrdersRequest,
        GetPortfolioHistoryRequest,
    )
    from alpaca.trading.enums import (
        OrderSide,
        OrderType,
        TimeInForce,
        OrderStatus,
        QueryOrderStatus,
    )
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
    from alpaca.data.timeframe import TimeFrame
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    TradingClient = None

from .base_broker import (
    BaseBroker,
    Order,
    OrderType as BrokerOrderType,
    OrderSide as BrokerOrderSide,
    OrderStatus as BrokerOrderStatus,
    Position,
    Account,
    TradeResult,
    TimeInForce as BrokerTimeInForce,
)

logger = logging.getLogger(__name__)


class AlpacaBroker(BaseBroker):
    """
    Alpaca Markets broker implementation.
    
    Features:
    - Commission-free stock trading
    - Paper trading support
    - Real-time and historical data
    - Fractional shares
    
    Requirements:
    - pip install alpaca-py
    - Alpaca account (paper or live)
    """
    
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        paper: bool = True,
        **kwargs
    ):
        """
        Initialize Alpaca broker.
        
        Args:
            api_key: Alpaca API key
            secret_key: Alpaca secret key
            paper: Use paper trading account (default: True)
            **kwargs: Additional arguments passed to BaseBroker
        """
        if not ALPACA_AVAILABLE:
            raise ImportError(
                "alpaca-py is required. Install with: pip install alpaca-py"
            )
        
        super().__init__(**kwargs)
        
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper = paper
        
        # Clients
        self._trading_client: Optional[TradingClient] = None
        self._data_client: Optional[StockHistoricalDataClient] = None
        
        # Order tracking
        self._alpaca_orders: Dict[str, Any] = {}
    
    @property
    def name(self) -> str:
        return f"Alpaca({'Paper' if self.paper else 'Live'})"
    
    def connect(self) -> bool:
        """Connect to Alpaca API"""
        try:
            self._trading_client = TradingClient(
                api_key=self.api_key,
                secret_key=self.secret_key,
                paper=self.paper,
            )
            
            self._data_client = StockHistoricalDataClient(
                api_key=self.api_key,
                secret_key=self.secret_key,
            )
            
            # Test connection by getting account
            account = self._trading_client.get_account()
            self._connected = True
            
            logger.info(f"Connected to Alpaca ({'Paper' if self.paper else 'Live'})")
            logger.info(f"Account status: {account.status}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Alpaca: {e}")
            self._connected = False
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from Alpaca"""
        self._trading_client = None
        self._data_client = None
        self._connected = False
        logger.info("Disconnected from Alpaca")
        return True
    
    # ==================== Account ====================
    
    def get_account(self) -> Account:
        """Get account information"""
        if not self._connected:
            raise ConnectionError("Not connected to Alpaca")
        
        try:
            acc = self._trading_client.get_account()
            
            return Account(
                account_id=acc.id,
                currency="USD",
                cash=float(acc.cash),
                cash_available=float(acc.cash),
                buying_power=float(acc.buying_power),
                equity=float(acc.equity),
                margin_used=float(acc.initial_margin) if acc.initial_margin else 0.0,
                margin_available=float(acc.maintenance_margin) if acc.maintenance_margin else 0.0,
                last_updated=datetime.now(timezone.utc),
            )
            
        except Exception as e:
            logger.error(f"Failed to get account: {e}")
            raise
    
    # ==================== Orders ====================
    
    def buy_market(
        self,
        symbol: str,
        quantity: Optional[float] = None,
        amount: Optional[float] = None,
        **kwargs
    ) -> TradeResult:
        """Execute market buy order"""
        return self._execute_order(
            symbol=symbol,
            side=BrokerOrderSide.BUY,
            order_type=BrokerOrderType.MARKET,
            quantity=quantity,
            amount=amount,
            **kwargs
        )
    
    def sell_market(
        self,
        symbol: str,
        quantity: Optional[float] = None,
        amount: Optional[float] = None,
        **kwargs
    ) -> TradeResult:
        """Execute market sell order"""
        return self._execute_order(
            symbol=symbol,
            side=BrokerOrderSide.SELL,
            order_type=BrokerOrderType.MARKET,
            quantity=quantity,
            amount=amount,
            **kwargs
        )
    
    def buy_limit(
        self,
        symbol: str,
        price: float,
        quantity: Optional[float] = None,
        amount: Optional[float] = None,
        **kwargs
    ) -> TradeResult:
        """Execute limit buy order"""
        return self._execute_order(
            symbol=symbol,
            side=BrokerOrderSide.BUY,
            order_type=BrokerOrderType.LIMIT,
            price=price,
            quantity=quantity,
            amount=amount,
            **kwargs
        )
    
    def sell_limit(
        self,
        symbol: str,
        price: float,
        quantity: Optional[float] = None,
        amount: Optional[float] = None,
        **kwargs
    ) -> TradeResult:
        """Execute limit sell order"""
        return self._execute_order(
            symbol=symbol,
            side=BrokerOrderSide.SELL,
            order_type=BrokerOrderType.LIMIT,
            price=price,
            quantity=quantity,
            amount=amount,
            **kwargs
        )
    
    def buy_stop(
        self,
        symbol: str,
        stop_price: float,
        quantity: Optional[float] = None,
        amount: Optional[float] = None,
        **kwargs
    ) -> TradeResult:
        """Execute stop buy order"""
        return self._execute_order(
            symbol=symbol,
            side=BrokerOrderSide.BUY,
            order_type=BrokerOrderType.STOP,
            stop_price=stop_price,
            quantity=quantity,
            amount=amount,
            **kwargs
        )
    
    def sell_stop(
        self,
        symbol: str,
        stop_price: float,
        quantity: Optional[float] = None,
        amount: Optional[float] = None,
        **kwargs
    ) -> TradeResult:
        """Execute stop sell order"""
        return self._execute_order(
            symbol=symbol,
            side=BrokerOrderSide.SELL,
            order_type=BrokerOrderType.STOP,
            stop_price=stop_price,
            quantity=quantity,
            amount=amount,
            **kwargs
        )
    
    def _execute_order(
        self,
        symbol: str,
        side: BrokerOrderSide,
        order_type: BrokerOrderType,
        quantity: Optional[float] = None,
        amount: Optional[float] = None,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: BrokerTimeInForce = BrokerTimeInForce.DAY,
        **kwargs
    ) -> TradeResult:
        """Execute order through Alpaca API"""
        if not self._connected:
            return TradeResult(
                success=False,
                message="Not connected to Alpaca",
            )
        
        try:
            # Determine quantity
            if quantity is None and amount is not None:
                current_price = self._get_current_price(symbol)
                if current_price is None:
                    return TradeResult(
                        success=False,
                        message=f"Could not get current price for {symbol}",
                    )
                quantity = amount / current_price
            
            if quantity is None or quantity <= 0:
                return TradeResult(
                    success=False,
                    message="Invalid quantity",
                )
            
            # Map time in force
            tif_map = {
                BrokerTimeInForce.DAY: TimeInForce.DAY,
                BrokerTimeInForce.GTC: TimeInForce.GTC,
                BrokerTimeInForce.IOC: TimeInForce.IOC,
                BrokerTimeInForce.FOK: TimeInForce.FOK,
            }
            alpaca_tif = tif_map.get(time_in_force, TimeInForce.DAY)
            
            # Map order side
            alpaca_side = OrderSide.BUY if side == BrokerOrderSide.BUY else OrderSide.SELL
            
            # Create order request based on type
            if order_type == BrokerOrderType.MARKET:
                order_request = MarketOrderRequest(
                    symbol=symbol.upper(),
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                )
            elif order_type == BrokerOrderType.LIMIT:
                if price is None:
                    return TradeResult(
                        success=False,
                        message="Limit order requires price",
                    )
                order_request = LimitOrderRequest(
                    symbol=symbol.upper(),
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                    limit_price=price,
                )
            elif order_type == BrokerOrderType.STOP:
                if stop_price is None:
                    return TradeResult(
                        success=False,
                        message="Stop order requires stop_price",
                    )
                order_request = StopOrderRequest(
                    symbol=symbol.upper(),
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                    stop_price=stop_price,
                )
            elif order_type == BrokerOrderType.STOP_LIMIT:
                if price is None or stop_price is None:
                    return TradeResult(
                        success=False,
                        message="Stop-limit order requires both price and stop_price",
                    )
                order_request = StopLimitOrderRequest(
                    symbol=symbol.upper(),
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                    limit_price=price,
                    stop_price=stop_price,
                )
            else:
                return TradeResult(
                    success=False,
                    message=f"Unsupported order type: {order_type}",
                )
            
            # Submit order
            alpaca_order = self._trading_client.submit_order(order_request)
            
            # Store order
            self._alpaca_orders[alpaca_order.id] = alpaca_order
            
            # Create our order object
            order = self._convert_alpaca_order(alpaca_order)
            self._orders[order.order_id] = order
            
            logger.info(f"Submitted {side.value} {order_type.value} order for {quantity} {symbol}")
            
            return TradeResult(
                success=True,
                message=f"Order submitted: {alpaca_order.id}",
                order=order,
            )
            
        except Exception as e:
            logger.error(f"Order execution failed: {e}")
            return TradeResult(
                success=False,
                message=f"Order failed: {str(e)}",
            )
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        if not self._connected:
            return False
        
        try:
            self._trading_client.cancel_order_by_id(order_id)
            logger.info(f"Cancelled order {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        if not self._connected:
            return None
        
        try:
            alpaca_order = self._trading_client.get_order_by_id(order_id)
            return self._convert_alpaca_order(alpaca_order)
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            return None
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders"""
        if not self._connected:
            return []
        
        try:
            request = GetOrdersRequest(status=QueryOrderStatus.OPEN)
            orders = self._trading_client.get_orders(request)
            result = [self._convert_alpaca_order(o) for o in orders]
            
            if symbol:
                result = [o for o in result if o.symbol == symbol.upper()]
            
            return result
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []
    
    # ==================== Positions ====================
    
    def get_positions(self) -> Dict[str, Position]:
        """Get all positions"""
        if not self._connected:
            return {}
        
        try:
            positions = self._trading_client.get_all_positions()
            result = {}
            
            for pos in positions:
                position = Position(
                    symbol=pos.symbol,
                    quantity=float(pos.qty),
                    available=float(pos.qty_available) if pos.qty_available else float(pos.qty),
                    avg_cost=float(pos.avg_entry_price),
                    current_price=float(pos.current_price),
                    market_value=float(pos.market_value),
                    unrealized_pnl=float(pos.unrealized_pl),
                    unrealized_pnl_pct=float(pos.unrealized_plpc),
                    side="LONG" if float(pos.qty) > 0 else "SHORT",
                )
                result[pos.symbol] = position
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return {}
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a symbol"""
        if not self._connected:
            return None
        
        try:
            pos = self._trading_client.get_open_position(symbol.upper())
            return Position(
                symbol=pos.symbol,
                quantity=float(pos.qty),
                available=float(pos.qty_available) if pos.qty_available else float(pos.qty),
                avg_cost=float(pos.avg_entry_price),
                current_price=float(pos.current_price),
                market_value=float(pos.market_value),
                unrealized_pnl=float(pos.unrealized_pl),
                unrealized_pnl_pct=float(pos.unrealized_plpc),
                side="LONG" if float(pos.qty) > 0 else "SHORT",
            )
        except Exception as e:
            # Position doesn't exist
            return None
    
    def close_position(self, symbol: str, quantity: Optional[float] = None) -> TradeResult:
        """Close position for a symbol"""
        if not self._connected:
            return TradeResult(
                success=False,
                message="Not connected to Alpaca",
            )
        
        try:
            if quantity:
                order = self._trading_client.close_position(
                    symbol.upper(),
                    qty=quantity,
                )
            else:
                order = self._trading_client.close_position(symbol.upper())
            
            return TradeResult(
                success=True,
                message=f"Position close order submitted: {order.id}",
                order=self._convert_alpaca_order(order),
            )
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            return TradeResult(
                success=False,
                message=f"Failed to close position: {str(e)}",
            )
    
    # ==================== Market Data ====================
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        return self._get_current_price(symbol)
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Internal method to get current price"""
        if not self._connected or self._data_client is None:
            return None
        
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol.upper())
            quote = self._data_client.get_stock_latest_quote(request)
            
            if symbol.upper() in quote:
                q = quote[symbol.upper()]
                # Use mid price
                return (float(q.bid_price) + float(q.ask_price)) / 2
            
            return None
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return None
    
    def get_portfolio_history(
        self,
        period: str = "1M",
        timeframe: str = "1D",
    ) -> Dict:
        """Get portfolio performance history"""
        if not self._connected:
            return {}
        
        try:
            # Map timeframe
            tf_map = {
                "1Min": TimeFrame.Minute,
                "5Min": TimeFrame.Minute,  # Will need adjustment
                "15Min": TimeFrame.Minute,
                "1H": TimeFrame.Hour,
                "1D": TimeFrame.Day,
                "1W": TimeFrame.Week,
                "1M": TimeFrame.Month,
            }
            
            request = GetPortfolioHistoryRequest(
                period=period,
                timeframe=tf_map.get(timeframe, TimeFrame.Day),
            )
            
            history = self._trading_client.get_portfolio_history(request)
            
            return {
                "timestamps": [datetime.fromtimestamp(ts, tz=timezone.utc) for ts in history.timestamp],
                "equity": history.equity,
                "profit_loss": history.profit_loss,
                "profit_loss_pct": history.profit_loss_pct,
            }
            
        except Exception as e:
            logger.error(f"Failed to get portfolio history: {e}")
            return {}
    
    # ==================== Helpers ====================
    
    def _convert_alpaca_order(self, alpaca_order) -> Order:
        """Convert Alpaca order to our Order type"""
        # Map status
        status_map = {
            OrderStatus.NEW: BrokerOrderStatus.PENDING,
            OrderStatus.PARTIALLY_FILLED: BrokerOrderStatus.PARTIALLY_FILLED,
            OrderStatus.FILLED: BrokerOrderStatus.FILLED,
            OrderStatus.CANCELED: BrokerOrderStatus.CANCELLED,
            OrderStatus.EXPIRED: BrokerOrderStatus.EXPIRED,
            OrderStatus.REJECTED: BrokerOrderStatus.REJECTED,
            OrderStatus.PENDING_NEW: BrokerOrderStatus.PENDING,
            OrderStatus.PENDING_CANCEL: BrokerOrderStatus.PENDING,
            OrderStatus.PENDING_REPLACE: BrokerOrderStatus.PENDING,
        }
        
        # Map order type
        type_map = {
            OrderType.MARKET: BrokerOrderType.MARKET,
            OrderType.LIMIT: BrokerOrderType.LIMIT,
            OrderType.STOP: BrokerOrderType.STOP,
            OrderType.STOP_LIMIT: BrokerOrderType.STOP_LIMIT,
        }
        
        # Map side
        side_map = {
            OrderSide.BUY: BrokerOrderSide.BUY,
            OrderSide.SELL: BrokerOrderSide.SELL,
        }
        
        return Order(
            order_id=alpaca_order.id,
            client_order_id=alpaca_order.client_order_id,
            symbol=alpaca_order.symbol,
            side=side_map.get(alpaca_order.side, BrokerOrderSide.BUY),
            order_type=type_map.get(alpaca_order.order_type, BrokerOrderType.MARKET),
            quantity=float(alpaca_order.qty) if alpaca_order.qty else 0,
            filled_quantity=float(alpaca_order.filled_qty) if alpaca_order.filled_qty else 0,
            price=float(alpaca_order.limit_price) if alpaca_order.limit_price else None,
            stop_price=float(alpaca_order.stop_price) if alpaca_order.stop_price else None,
            avg_fill_price=float(alpaca_order.filled_avg_price) if alpaca_order.filled_avg_price else None,
            status=status_map.get(alpaca_order.status, BrokerOrderStatus.PENDING),
            created_at=alpaca_order.created_at,
            updated_at=alpaca_order.updated_at,
        )