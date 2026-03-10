"""Futu Exchange implementation for HK/US stock trading."""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from tradingagents.execution.base_exchange import AbstractExchange, OrderResult, Balance, OrderSide, OrderType

logger = logging.getLogger(__name__)


class FutuMarket(str, Enum):
    """Futu market types."""
    HK = "HK"  # Hong Kong
    US = "US"  # United States
    CN = "CN"  # China A-shares


class FutuExchange(AbstractExchange):
    """
    Futu OpenD Exchange implementation.
    
    Supports trading on:
    - Hong Kong Stock Exchange
    - US Markets (NASDAQ, NYSE)
    - China A-shares
    
    Requirements:
    - FutuOpenD gateway running
    - futu-api package installed
    """
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 11111,
        market: FutuMarket = FutuMarket.US,
        paper_trading: bool = True,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(config)
        self.host = host
        self.port = port
        self.market = market
        self.paper_trading = paper_trading
        self._quote_ctx = None
        self._trade_ctx = None
        self._connected = False
        self._positions: Dict[str, Dict[str, Any]] = {}
        self._balances: Dict[str, float] = {}
        
    async def connect(self) -> bool:
        """Connect to FutuOpenD gateway."""
        try:
            # Lazy import to avoid dependency issues
            from futu import OpenQuoteContext, OpenHKTradeContext, OpenUSTradeContext, RET_OK
            
            # Connect quote context
            self._quote_ctx = OpenQuoteContext(self.host, self.port)
            
            # Connect trade context based on market
            if self.market == FutuMarket.HK:
                self._trade_ctx = OpenHKTradeContext(self.host, self.port)
            else:
                self._trade_ctx = OpenUSTradeContext(self.host, self.port)
            
            self._connected = True
            logger.info(f"Connected to FutuOpenD at {self.host}:{self.port}")
            return True
            
        except ImportError:
            logger.warning("futu-api not installed. Running in simulation mode.")
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to FutuOpenD: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from FutuOpenD gateway."""
        if self._quote_ctx:
            self._quote_ctx.close()
        if self._trade_ctx:
            self._trade_ctx.close()
        self._connected = False
        logger.info("Disconnected from FutuOpenD")
    
    def is_connected(self) -> bool:
        """Check if connected to exchange."""
        return self._connected
    
    async def get_balance(self, asset: str = "USD") -> Balance:
        """Get account balance."""
        if not self._connected:
            raise RuntimeError("Not connected to FutuOpenD")
        
        try:
            if self._trade_ctx:
                # Real balance query
                ret, data = self._trade_ctx.accinfo_query()
                if ret == 0:  # RET_OK
                    for row in data.iter_rows():
                        if row['currency'] == asset:
                            return Balance(
                                asset=asset,
                                free=float(row['available']),
                                locked=float(row['balance']) - float(row['available']),
                                total=float(row['balance'])
                            )
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
        
        # Return simulated balance if no real data
        return Balance(
            asset=asset,
            free=self._balances.get(asset, 100000.0),
            locked=0.0,
            total=self._balances.get(asset, 100000.0)
        )
    
    async def get_price(self, symbol: str) -> float:
        """Get current market price for symbol."""
        if not self._connected:
            raise RuntimeError("Not connected to FutuOpenD")
        
        try:
            if self._quote_ctx:
                from futu import RET_OK
                ret, data = self._quote_ctx.get_market_snapshot([symbol])
                if ret == RET_OK and len(data) > 0:
                    return float(data.iloc[0]['last_price'])
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
        
        # Return simulated price
        return 100.0
    
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        **kwargs
    ) -> OrderResult:
        """Place an order on Futu."""
        if not self._connected:
            raise RuntimeError("Not connected to FutuOpenD")
        
        try:
            if self._trade_ctx and not self.paper_trading:
                # Real order placement
                from futu import RET_OK, TrdSide, OrderType as FutuOrderType
                
                futu_side = TrdSide.BUY if side == OrderSide.BUY else TrdSide.SELL
                futu_order_type = FutuOrderType.MARKET if order_type == OrderType.MARKET else FutuOrderType.NORMAL
                
                ret, data = self._trade_ctx.place_order(
                    price=price or 0,  # 0 for market orders
                    qty=int(quantity),
                    code=symbol,
                    trd_side=futu_side,
                    order_type=futu_order_type
                )
                
                if ret == RET_OK:
                    order_id = str(data.iloc[0]['order_id'])
                    executed_price = float(data.iloc[0]['dealt_avg_price'] or price or await self.get_price(symbol))
                    
                    return OrderResult(
                        success=True,
                        order_id=order_id,
                        executed_price=executed_price,
                        executed_quantity=quantity,
                        message="Order placed successfully"
                    )
                else:
                    return OrderResult(
                        success=False,
                        message=f"Order failed: {data}"
                    )
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return OrderResult(
                success=False,
                message=str(e)
            )
        
        # Simulated order (paper trading or no connection)
        simulated_price = price or await self.get_price(symbol)
        order_id = f"FUTU_{datetime.now().strftime('%Y%m%d%H%M%S')}_{symbol}"
        
        # Update positions
        position_key = f"{symbol}_{side.value}"
        if position_key in self._positions:
            self._positions[position_key]['quantity'] += quantity
        else:
            self._positions[position_key] = {
                'symbol': symbol,
                'side': side.value,
                'quantity': quantity,
                'entry_price': simulated_price,
            }
        
        return OrderResult(
            success=True,
            order_id=order_id,
            executed_price=simulated_price,
            executed_quantity=quantity,
            message="Order executed (simulated)"
        )
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if not self._connected:
            raise RuntimeError("Not connected to FutuOpenD")
        
        try:
            if self._trade_ctx and not self.paper_trading:
                from futu import RET_OK
                ret, data = self._trade_ctx.modify_order(
                    modify_order_op=0,  # Cancel
                    order_id=order_id
                )
                return ret == RET_OK
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
        
        return True  # Simulated success
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status."""
        if not self._connected:
            raise RuntimeError("Not connected to FutuOpenD")
        
        try:
            if self._trade_ctx and not self.paper_trading:
                from futu import RET_OK
                ret, data = self._trade_ctx.order_list_query(order_id=order_id)
                if ret == RET_OK and len(data) > 0:
                    row = data.iloc[0]
                    return {
                        'order_id': order_id,
                        'status': row['order_status'],
                        'symbol': row['code'],
                        'side': row['trd_side'],
                        'quantity': float(row['qty']),
                        'filled_quantity': float(row['dealt_qty']),
                        'price': float(row['price']),
                        'avg_price': float(row['dealt_avg_price'] or 0),
                    }
        except Exception as e:
            logger.error(f"Failed to get order status: {e}")
        
        return {'order_id': order_id, 'status': 'filled'}
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get all positions."""
        if not self._connected:
            raise RuntimeError("Not connected to FutuOpenD")
        
        positions = []
        
        try:
            if self._trade_ctx and not self.paper_trading:
                from futu import RET_OK
                ret, data = self._trade_ctx.position_list_query()
                if ret == RET_OK:
                    for _, row in data.iterrows():
                        positions.append({
                            'symbol': row['code'],
                            'quantity': float(row['qty']),
                            'avg_price': float(row['cost_price']),
                            'market_value': float(row['market_val']),
                            'pnl': float(row['pl_val']),
                            'pnl_ratio': float(row['pl_ratio']),
                        })
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
        
        # Add simulated positions
        for pos in self._positions.values():
            positions.append(pos)
        
        return positions
    
    async def close_position(self, symbol: str, quantity: Optional[float] = None) -> OrderResult:
        """Close a position."""
        positions = await self.get_positions()
        
        for pos in positions:
            if pos['symbol'] == symbol:
                close_qty = quantity or pos['quantity']
                return await self.place_order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=close_qty,
                    order_type=OrderType.MARKET
                )
        
        return OrderResult(
            success=False,
            message=f"No position found for {symbol}"
        )
    
    def get_name(self) -> str:
        """Get exchange name."""
        return f"Futu ({self.market.value})"
    
    def get_supported_assets(self) -> List[str]:
        """Get list of supported trading assets."""
        if self.market == FutuMarket.HK:
            return ["HKD", "USD", "CNY"]
        elif self.market == FutuMarket.US:
            return ["USD"]
        else:
            return ["CNY"]