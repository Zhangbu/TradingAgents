"""CCXT exchange implementation for cryptocurrency trading."""

import asyncio
from decimal import Decimal
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

try:
    import ccxt.async_support as ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    ccxt = None

from tradingagents.execution.base_exchange import AbstractExchange, Balance, OrderResult, OrderSide, OrderType

logger = logging.getLogger(__name__)


class CCXTExchange(AbstractExchange):
    """
    CCXT-based exchange implementation for cryptocurrency trading.
    
    Supports multiple crypto exchanges: Binance, OKX, Bybit, etc.
    """
    
    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: str = None,
        api_secret: str = None,
        password: str = None,  # Required for some exchanges like OKX
        sandbox: bool = True,
        default_quote: str = "USDT",
    ):
        """
        Initialize CCXT exchange.
        
        Args:
            exchange_id: Exchange identifier (e.g., 'binance', 'okx', 'bybit')
            api_key: API key
            api_secret: API secret
            password: API password (for OKX, etc.)
            sandbox: Whether to use sandbox/testnet mode
            default_quote: Default quote currency for trading
        """
        super().__init__()
        
        if not CCXT_AVAILABLE:
            raise ImportError("ccxt is not installed. Install with: pip install ccxt")
        
        self.exchange_id = exchange_id.lower()
        self.sandbox = sandbox
        self.default_quote = default_quote
        self._exchange = None
        
        # Exchange configuration
        self.config = {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",
            }
        }
        
        if password:
            self.config["password"] = password
        
        if sandbox:
            self.config["options"]["sandboxMode"] = True
    
    @property
    def exchange(self):
        """Lazy initialization of exchange instance."""
        if self._exchange is None:
            exchange_class = getattr(ccxt, self.exchange_id)
            self._exchange = exchange_class(self.config)
        return self._exchange
    
    async def initialize(self):
        """Initialize the exchange connection."""
        await self.exchange.load_markets()
        logger.info(f"Initialized {self.exchange_id} exchange with {len(self.exchange.markets)} markets")
    
    async def close(self):
        """Close the exchange connection."""
        if self._exchange:
            await self._exchange.close()
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def get_price(self, symbol: str) -> Decimal:
        """Get current price for a symbol."""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return Decimal(str(ticker["last"]))
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            raise
    
    async def get_balance(self) -> Balance:
        """Get account balance."""
        try:
            balances = await self.exchange.fetch_balance()
            
            # Filter out zero balances
            non_zero = {
                asset: Decimal(str(amount))
                for asset, amount in balances.get("total", {}).items()
                if amount and float(amount) > 0
            }
            
            return Balance(
                available=non_zero,
                total=non_zero,
            )
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            raise
    
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[Decimal] = None,
        **kwargs,
    ) -> OrderResult:
        """
        Place an order on the exchange.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            side: Order side (BUY/SELL)
            quantity: Order quantity
            order_type: Order type (MARKET/LIMIT)
            price: Limit price (required for LIMIT orders)
            **kwargs: Additional exchange-specific parameters
            
        Returns:
            OrderResult with execution details
        """
        try:
            ccxt_side = "buy" if side == OrderSide.BUY else "sell"
            ccxt_type = "market" if order_type == OrderType.MARKET else "limit"
            
            params = {
                "symbol": symbol,
                "type": ccxt_type,
                "side": ccxt_side,
                "amount": float(quantity),
            }
            
            if order_type == OrderType.LIMIT:
                if price is None:
                    raise ValueError("Price is required for LIMIT orders")
                params["price"] = float(price)
            
            # Generate client order ID
            client_order_id = kwargs.pop("client_order_id", None)
            if client_order_id:
                params["clientOrderId"] = client_order_id
            
            order = await self.exchange.create_order(**params)
            
            return OrderResult(
                order_id=order["id"],
                client_order_id=order.get("clientOrderId"),
                symbol=symbol,
                side=side,
                quantity=Decimal(str(order["amount"])),
                price=Decimal(str(order.get("price") or order.get("average") or 0)),
                status=order["status"],
                executed_at=datetime.fromtimestamp(order["timestamp"] / 1000),
                exchange_response=order,
            )
            
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order."""
        try:
            await self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Cancelled order {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    async def get_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Get order details."""
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            return order
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            raise
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all open orders."""
        try:
            orders = await self.exchange.fetch_open_orders(symbol)
            return orders
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            raise
    
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """Cancel all open orders and return count of cancelled orders."""
        try:
            orders = await self.get_open_orders(symbol)
            cancelled = 0
            for order in orders:
                if await self.cancel_order(order["id"], order["symbol"]):
                    cancelled += 1
            return cancelled
        except Exception as e:
            logger.error(f"Failed to cancel all orders: {e}")
            return 0
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions (for spot, returns balances)."""
        balance = await self.get_balance()
        
        # For spot trading, positions are just non-quote balances
        positions = []
        for asset, amount in balance.total.items():
            if asset != self.default_quote and amount > 0:
                try:
                    # Try to get current price
                    symbol = f"{asset}/{self.default_quote}"
                    price = await self.get_price(symbol)
                    positions.append({
                        "symbol": symbol,
                        "asset": asset,
                        "quantity": float(amount),
                        "current_price": float(price),
                        "value": float(amount * price),
                    })
                except Exception:
                    pass
        
        return positions
    
    async def get_tickers(self) -> Dict[str, Dict]:
        """Get all tickers."""
        try:
            tickers = await self.exchange.fetch_tickers()
            return tickers
        except Exception as e:
            logger.error(f"Failed to get tickers: {e}")
            raise


class BinanceExchange(CCXTExchange):
    """Binance-specific exchange implementation."""
    
    def __init__(self, api_key: str = None, api_secret: str = None, sandbox: bool = True, **kwargs):
        super().__init__(
            exchange_id="binance",
            api_key=api_key,
            api_secret=api_secret,
            sandbox=sandbox,
            **kwargs,
        )


class OKXExchange(CCXTExchange):
    """OKX-specific exchange implementation."""
    
    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        password: str = None,
        sandbox: bool = True,
        **kwargs,
    ):
        super().__init__(
            exchange_id="okx",
            api_key=api_key,
            api_secret=api_secret,
            password=password,
            sandbox=sandbox,
            **kwargs,
        )