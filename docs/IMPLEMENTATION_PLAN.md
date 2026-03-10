# TradingAgents 实战交易系统实施方案

> 文档创建时间: 2026-03-09
> 项目版本: v0.2.0

---

## 目录

1. [项目分析报告](#一项目分析报告)
2. [当前限制与问题](#二当前限制与问题)
3. [实战交易系统架构设计](#三实战交易系统架构设计)
4. [模块详细设计](#四模块详细设计)
5. [实施计划与任务清单](#五实施计划与任务清单)
6. [技术选型建议](#六技术选型建议)

---

## 一、项目分析报告

### 1.1 项目概述

TradingAgents 是一个**多Agent协作的LLM金融交易框架**，基于 LangGraph 构建工作流，模拟真实投资公司的运作方式。

**项目地址**: https://github.com/TauricResearch/TradingAgents

### 1.2 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      TradingAgents 架构                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐           │
│  │   Analysts  │ → │ Researchers │ → │   Trader    │           │
│  │  (分析师团队) │   │  (研究员团队) │   │  (交易员)   │           │
│  └─────────────┘   └─────────────┘   └─────────────┘           │
│                                              ↓                   │
│  ┌─────────────────────────────────────────────────┐           │
│  │           Risk Management (风险管理团队)          │           │
│  │   Aggressive ↔ Conservative ↔ Neutral           │           │
│  │                    ↓                              │           │
│  │            Risk Manager (最终决策)                │           │
│  └─────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Agent 模块分析

#### 分析师团队 (Analysts)

| Agent | 文件位置 | 功能 | 使用工具 |
|-------|---------|------|---------|
| **Market Analyst** | `analysts/market_analyst.py` | 技术指标分析 | `get_stock_data`, `get_indicators` |
| **News Analyst** | `analysts/news_analyst.py` | 新闻和宏观分析 | `get_news`, `get_global_news` |
| **Social Media Analyst** | `analysts/social_media_analyst.py` | 社交情绪分析 | `get_news` |
| **Fundamentals Analyst** | `analysts/fundamentals_analyst.py` | 财务基本面分析 | `get_fundamentals`, `get_balance_sheet`, `get_cashflow`, `get_income_statement` |

**支持的技术指标**:
- 移动平均: SMA(50/200), EMA(10)
- MACD系列: macd, macds, macdh
- 动量指标: RSI
- 波动指标: Bollinger Bands, ATR
- 成交量指标: VWMA, MFI

#### 研究员团队 (Researchers)

| Agent | 文件位置 | 功能 |
|-------|---------|------|
| **Bull Researcher** | `researchers/bull_researcher.py` | 提出看多论点，支持买入 |
| **Bear Researcher** | `researchers/bear_researcher.py` | 提出看空论点，支持卖出 |
| **Research Manager** | `managers/research_manager.py` | 评估辩论，制定投资计划 |

**辩论机制**: Bull ↔ Bear 多轮辩论（可配置轮数），Research Manager 裁决

#### 交易员与风险管理

| Agent | 文件位置 | 立场 |
|-------|---------|------|
| **Trader** | `trader/trader.py` | 综合分析，制定交易计划 |
| **Aggressive Debator** | `risk_mgmt/aggressive_debator.py` | 高风险高回报 |
| **Conservative Debator** | `risk_mgmt/conservative_debator.py` | 保守稳健 |
| **Neutral Debator** | `risk_mgmt/neutral_debator.py` | 中性平衡 |
| **Risk Manager** | `managers/risk_manager.py` | 最终裁决 |

### 1.4 工作流引擎

```
工作流执行顺序:
START → Market Analyst → Social Analyst → News Analyst → Fundamentals Analyst
    → Bull Researcher ↔ Bear Researcher (辩论)
    → Research Manager (裁决)
    → Trader (交易计划)
    → Aggressive ↔ Conservative ↔ Neutral (风险辩论)
    → Risk Manager (最终决策)
    → END
```

**核心文件**:
| 文件 | 功能 |
|------|------|
| `trading_graph.py` | 主入口类 `TradingAgentsGraph`，编排所有组件 |
| `setup.py` | 构建 LangGraph 状态图 |
| `propagation.py` | 状态初始化和传播参数 |
| `conditional_logic.py` | 控制辩论轮数和路由 |
| `signal_processing.py` | 从完整报告中提取 BUY/SELL/HOLD |
| `reflection.py` | 反思学习机制 |

### 1.5 数据流模块

**数据源支持**:
| 数据源 | API Key | 功能 |
|--------|---------|------|
| **yfinance** | 免费（推荐） | 股票价格、技术指标、基本面、新闻 |
| **Alpha Vantage** | 需要API Key | 同上，有速率限制 |

### 1.6 LLM 客户端

**支持的LLM提供商**:
| 提供商 | 配置项 |
|--------|--------|
| OpenAI | `llm_provider: "openai"` |
| Google | `llm_provider: "google"` |
| Anthropic | `llm_provider: "anthropic"` |
| xAI (Grok) | `llm_provider: "xai"` |
| OpenRouter | `llm_provider: "openrouter"` |
| Ollama (本地) | `llm_provider: "ollama"` |

---

## 二、当前限制与问题

### 2.1 核心问题

| 问题 | 说明 |
|------|------|
| **无交易执行** | 只输出决策，不执行交易 |
| **无回测系统** | 无法验证策略有效性 |
| **单标的限制** | 每次只分析一只股票 |
| **无仓位管理** | 不建议买卖数量和资金分配 |
| **无实时监控** | 需手动运行 |
| **无止损止盈** | 缺少风险控制自动化 |

### 2.2 README 描述与实际代码不符

**README 声称**:
> The Portfolio Manager approves/rejects the transaction proposal. If approved, the order will be sent to the simulated exchange and executed.

**实际代码**:
- 搜索 `exchange`, `broker`, `order`, `execute`, `simulate` 等关键词，结果为 0
- 最终输出只是 `final_trade_decision` 字符串 (BUY/SELL/HOLD)
- **模拟交易所不存在，交易执行功能完全未实现**

### 2.3 当前系统输出

```
输入: AAPL, 2024-05-10
输出: "BUY" (或一段包含 BUY/SELL/HOLD 的文字描述)
然后就结束了。
```

---

## 三、实战交易系统架构设计

### 3.1 系统架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TradingAgents 实战交易系统                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │  Strategy Layer │    │  Portfolio Layer │   │  Execution Layer│         │
│  │    (决策层)      │    │    (组合层)       │   │    (执行层)      │         │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘         │
│           │                      │                      │                   │
│           ▼                      ▼                      ▼                   │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                      Risk Management Layer                       │       │
│  │                         (风险控制层)                              │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                      Market Data Layer                           │       │
│  │             (多市场数据层 - 美股/A股/加密货币)                      │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 模块目录结构

```
tradingagents/
├── execution/              # 执行层 (新增)
│   ├── __init__.py
│   ├── base_broker.py      # 抽象基类
│   ├── paper_broker.py     # 模拟交易
│   ├── alpaca_broker.py    # 美股 - Alpaca
│   ├── ibkr_broker.py      # 美股 - Interactive Brokers
│   ├── xtquant_broker.py   # A股 - 迅投QMT
│   ├── binance_broker.py   # 加密货币 - Binance
│   └── broker_factory.py   # 券商工厂
│
├── portfolio/              # 组合管理层 (新增)
│   ├── __init__.py
│   ├── position_manager.py # 仓位管理
│   ├── allocation_engine.py# 资金分配引擎
│   ├── portfolio_tracker.py# 组合追踪
│   └── rebalance.py        # 再平衡
│
├── risk/                   # 风险控制层 (新增)
│   ├── __init__.py
│   ├── risk_manager.py     # 风险管理主控
│   ├── stop_loss.py        # 止损策略
│   ├── take_profit.py      # 止盈策略
│   ├── exposure_monitor.py # 敞口监控
│   ├── drawdown_monitor.py # 回撤监控
│   └── alerts.py           # 风险预警
│
├── backtest/               # 回测系统 (新增)
│   ├── __init__.py
│   ├── backtester.py       # 回测引擎
│   ├── metrics.py          # 绩效指标
│   ├── report_generator.py # 报告生成
│   └── visualizer.py       # 可视化
│
├── scheduler/              # 调度系统 (新增)
│   ├── __init__.py
│   ├── task_scheduler.py   # 任务调度
│   ├── market_calendar.py  # 交易日历
│   └── signal_cron.py      # 定时信号生成
│
├── storage/                # 存储层 (新增)
│   ├── __init__.py
│   ├── trade_log.py        # 交易日志
│   ├── performance_db.py   # 绩效数据库
│   ├── signal_history.py   # 信号历史
│   └── config_store.py     # 配置存储
│
└── dataflows/              # 数据层扩展
    ├── markets/            # 多市场数据
    │   ├── us_market.py
    │   ├── cn_market.py
    │   └── crypto_market.py
    ├── realtime/           # 实时数据
    │   ├── websocket_feed.py
    │   └── quote_monitor.py
    └── alternative/        # 另类数据
        ├── sentiment_feed.py
        └── news_feed.py
```

---

## 四、模块详细设计

### 4.1 执行层 (Execution Layer)

#### 抽象基类设计

```python
# tradingagents/execution/base_broker.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

@dataclass
class Order:
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType
    limit_price: Optional[float] = None
    stop_price: Optional[float] None

@dataclass
class OrderResult:
    success: bool
    order_id: str
    filled_price: float
    message: str

@dataclass
class Position:
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float

@dataclass
class AccountInfo:
    cash: float
    total_value: float
    buying_power: float
    positions: List[Position]

class BaseBroker(ABC):
    """券商接口抽象基类"""
    
    @abstractmethod
    def connect(self) -> bool:
        """连接券商"""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """断开连接"""
        pass
    
    @abstractmethod
    def get_account(self) -> AccountInfo:
        """获取账户信息"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        """获取持仓"""
        pass
    
    @abstractmethod
    def place_order(self, order: Order) -> OrderResult:
        """下单"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        pass
    
    @abstractmethod
    def get_market_data(self, symbol: str) -> dict:
        """获取行情"""
        pass
    
    @abstractmethod
    def is_market_open(self) -> bool:
        """市场是否开盘"""
        pass
```

#### 模拟交易实现

```python
# tradingagents/execution/paper_broker.py
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from .base_broker import BaseBroker, Order, OrderResult, Position, AccountInfo, OrderSide, OrderType

class PaperBroker(BaseBroker):
    """模拟交易引擎"""
    
    def __init__(self, initial_capital: float = 100000, data_dir: str = "data/paper_trading"):
        self.initial_capital = initial_capital
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.pending_orders: Dict[str, Order] = {}
        self.trade_history: List[dict] = []
        
        self._load_state()
    
    def _load_state(self):
        """加载持久化状态"""
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
                self.cash = state.get('cash', self.initial_capital)
                # 恢复持仓和交易历史...
    
    def _save_state(self):
        """保存状态"""
        state = {
            'cash': self.cash,
            'positions': {k: v.__dict__ for k, v in self.positions.items()},
            'trade_history': self.trade_history
        }
        with open(self.data_dir / "state.json", 'w') as f:
            json.dump(state, f, indent=2, default=str)
    
    def connect(self) -> bool:
        return True
    
    def disconnect(self) -> bool:
        self._save_state()
        return True
    
    def get_account(self) -> AccountInfo:
        total_value = self.cash + sum(p.market_value for p in self.positions.values())
        return AccountInfo(
            cash=self.cash,
            total_value=total_value,
            buying_power=self.cash * 4,  # 4倍杠杆
            positions=list(self.positions.values())
        )
    
    def place_order(self, order: Order) -> OrderResult:
        current_price = self._get_current_price(order.symbol)
        
        if order.side == OrderSide.BUY:
            cost = current_price * order.quantity
            if cost > self.cash:
                return OrderResult(False, "", 0, "Insufficient funds")
            
            self.cash -= cost
            
            if order.symbol in self.positions:
                pos = self.positions[order.symbol]
                total_cost = pos.avg_cost * pos.quantity + cost
                total_qty = pos.quantity + order.quantity
                pos.avg_cost = total_cost / total_qty
                pos.quantity = total_qty
            else:
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    avg_cost=current_price,
                    current_price=current_price,
                    market_value=current_price * order.quantity,
                    unrealized_pnl=0
                )
            
            self.trade_history.append({
                'timestamp': datetime.now().isoformat(),
                'symbol': order.symbol,
                'side': 'BUY',
                'quantity': order.quantity,
                'price': current_price
            })
            
            self._save_state()
            return OrderResult(True, f"paper_{len(self.trade_history)}", current_price, "Filled")
        
        elif order.side == OrderSide.SELL:
            if order.symbol not in self.positions:
                return OrderResult(False, "", 0, "No position to sell")
            
            pos = self.positions[order.symbol]
            if pos.quantity < order.quantity:
                return OrderResult(False, "", 0, "Insufficient shares")
            
            revenue = current_price * order.quantity
            self.cash += revenue
            pos.quantity -= order.quantity
            
            if pos.quantity == 0:
                del self.positions[order.symbol]
            
            self.trade_history.append({
                'timestamp': datetime.now().isoformat(),
                'symbol': order.symbol,
                'side': 'SELL',
                'quantity': order.quantity,
                'price': current_price
            })
            
            self._save_state()
            return OrderResult(True, f"paper_{len(self.trade_history)}", current_price, "Filled")
        
        return OrderResult(False, "", 0, "Invalid order side")
    
    def _get_current_price(self, symbol: str) -> float:
        """获取当前价格 - 使用 yfinance"""
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        return ticker.history(period="1d")['Close'].iloc[-1]
```

### 4.2 组合管理层 (Portfolio Layer)

#### 仓位管理器

```python
# tradingagents/portfolio/position_manager.py
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class AllocationMethod(Enum):
    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    KELLY = "kelly"
    CUSTOM = "custom"

@dataclass
class Signal:
    symbol: str
    decision: str  # BUY, SELL, HOLD
    confidence: float  # 0-1
    price: float
    volatility: float

class PositionManager:
    """仓位管理器"""
    
    def __init__(
        self,
        total_capital: float,
        max_single_position: float = 0.10,  # 单标的最大仓位 10%
        max_sector_exposure: float = 0.30,   # 单板块最大仓位 30%
        max_total_exposure: float = 0.95,    # 最大总仓位 95%
    ):
        self.total_capital = total_capital
        self.max_single_position = max_single_position
        self.max_sector_exposure = max_sector_exposure
        self.max_total_exposure = max_total_exposure
        
        self.current_positions: Dict[str, float] = {}  # symbol -> value
    
    def calculate_position_size(
        self,
        signal: Signal,
        method: AllocationMethod = AllocationMethod.KELLY
    ) -> int:
        """计算建议仓位大小"""
        
        if method == AllocationMethod.EQUAL_WEIGHT:
            fraction = 1.0  # 将在外部除以标的数量
            
        elif method == AllocationMethod.RISK_PARITY:
            # 按波动率倒数分配
            if signal.volatility > 0:
                fraction = 1.0 / signal.volatility
            else:
                fraction = 1.0
                
        elif method == AllocationMethod.KELLY:
            # 凯利公式: f = (p*b - q) / b
            # 简化版: f = 2 * confidence - 1
            kelly_fraction = 2 * signal.confidence - 1
            fraction = max(0, min(kelly_fraction, 0.25))  # 限制最大25%
        
        # 应用风控限制
        max_value = self.total_capital * self.max_single_position
        position_value = min(self.total_capital * fraction, max_value)
        
        return int(position_value / signal.price)
    
    def allocate_portfolio(
        self,
        signals: List[Signal],
        method: AllocationMethod = AllocationMethod.RISK_PARITY
    ) -> Dict[str, int]:
        """组合资金分配"""
        
        if method == AllocationMethod.EQUAL_WEIGHT:
            n = len(signals)
            return {
                s.symbol: self.calculate_position_size(s, method) // n
                for s in signals if s.decision == "BUY"
            }
        
        elif method == AllocationMethod.RISK_PARITY:
            # 计算波动率倒数
            inv_vols = {}
            for s in signals:
                if s.decision == "BUY" and s.volatility > 0:
                    inv_vols[s.symbol] = 1.0 / s.volatility
            
            total_inv_vol = sum(inv_vols.values())
            
            allocations = {}
            for symbol, inv_vol in inv_vols.items():
                weight = inv_vol / total_inv_vol
                position_value = self.total_capital * weight
                # 获取价格
                price = next(s.price for s in signals if s.symbol == symbol)
                allocations[symbol] = int(position_value / price)
            
            return allocations
        
        return {}
    
    def check_exposure(self, new_position: Dict[str, int]) -> bool:
        """检查敞口是否超限"""
        current_exposure = sum(self.current_positions.values())
        new_exposure = sum(v * 1.0 for v in new_position.values())  # 简化
        
        total_exposure = (current_exposure + new_exposure) / self.total_capital
        
        return total_exposure <= self.max_total_exposure
```

### 4.3 风险控制层 (Risk Layer)

#### 风险管理器

```python
# tradingagents/risk/risk_manager.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

@dataclass
class RiskRules:
    """风控规则配置"""
    max_single_position: float = 0.10      # 单标的最大仓位
    max_sector_exposure: float = 0.30       # 单板块最大仓位
    max_total_exposure: float = 0.95        # 最大总仓位
    max_daily_loss: float = 0.03            # 单日最大亏损
    max_drawdown: float = 0.15              # 最大回撤
    default_stop_loss: float = 0.08         # 默认止损比例
    default_take_profit: float = 0.20       # 默认止盈比例
    trailing_stop_pct: float = 0.05         # 移动止损比例

@dataclass
class PositionRisk:
    symbol: str
    entry_price: float
    current_price: float
    highest_price: float
    stop_loss_price: float
    take_profit_price: float
    quantity: int
    entry_time: datetime

class RiskManager:
    """风险管理主控"""
    
    def __init__(self, rules: RiskRules, initial_capital: float):
        self.rules = rules
        self.initial_capital = initial_capital
        self.peak_capital = initial_capital
        
        self.position_risks: Dict[str, PositionRisk] = {}
        self.daily_pnl: float = 0
        self.daily_pnl_reset: datetime = datetime.now().replace(hour=0, minute=0)
    
    def check_order(self, order, current_positions: Dict) -> Tuple[bool, str]:
        """订单风控检查"""
        
        # 1. 单标的仓位检查
        symbol = order['symbol']
        position_value = current_positions.get(symbol, 0) * order.get('price', 0)
        new_value = position_value + order['quantity'] * order.get('price', 0)
        
        if new_value / self.initial_capital > self.rules.max_single_position:
            return False, f"Exceeds max single position ({self.rules.max_single_position*100}%)"
        
        # 2. 总仓位检查
        total_exposure = sum(v for v in current_positions.values())
        if total_exposure / self.initial_capital > self.rules.max_total_exposure:
            return False, "Exceeds max total exposure"
        
        # 3. 日内亏损检查
        self._check_daily_reset()
        if self.daily_pnl / self.initial_capital < -self.rules.max_daily_loss:
            return False, "Daily loss limit reached - trading halted"
        
        # 4. 回撤检查
        current_capital = self.initial_capital + self.daily_pnl
        if current_capital < self.peak_capital:
            drawdown = (self.peak_capital - current_capital) / self.peak_capital
            if drawdown > self.rules.max_drawdown:
                return False, "Max drawdown exceeded - trading halted"
        
        return True, "Approved"
    
    def update_position_risk(
        self,
        symbol: str,
        entry_price: float,
        quantity: int
    ):
        """初始化仓位风控"""
        self.position_risks[symbol] = PositionRisk(
            symbol=symbol,
            entry_price=entry_price,
            current_price=entry_price,
            highest_price=entry_price,
            stop_loss_price=entry_price * (1 - self.rules.default_stop_loss),
            take_profit_price=entry_price * (1 + self.rules.default_take_profit),
            quantity=quantity,
            entry_time=datetime.now()
        )
    
    def check_stop_loss_take_profit(self, symbol: str, current_price: float) -> Optional[str]:
        """检查止损止盈触发"""
        if symbol not in self.position_risks:
            return None
        
        risk = self.position_risks[symbol]
        risk.current_price = current_price
        
        # 更新最高价
        if current_price > risk.highest_price:
            risk.highest_price = current_price
            # 更新移动止损
            new_stop = current_price * (1 - self.rules.trailing_stop_pct)
            if new_stop > risk.stop_loss_price:
                risk.stop_loss_price = new_stop
        
        # 检查止损
        if current_price <= risk.stop_loss_price:
            return f"STOP_LOSS:{symbol}"
        
        # 检查止盈
        if current_price >= risk.take_profit_price:
            return f"TAKE_PROFIT:{symbol}"
        
        return None
    
    def _check_daily_reset(self):
        """重置日内统计"""
        now = datetime.now()
        if now.date() > self.daily_pnl_reset.date():
            self.daily_pnl = 0
            self.daily_pnl_reset = now.replace(hour=0, minute=0)
    
    def get_risk_report(self) -> dict:
        """生成风险报告"""
        return {
            'peak_capital': self.peak_capital,
            'daily_pnl': self.daily_pnl,
            'daily_pnl_pct': self.daily_pnl / self.initial_capital,
            'positions_at_risk': len(self.position_risks),
            'stop_losses': [
                {'symbol': r.symbol, 'stop_loss': r.stop_loss_price, 'current': r.current_price}
                for r in self.position_risks.values()
            ]
        }
```

### 4.4 回测系统 (Backtest)

#### 回测引擎

```python
# tradingagents/backtest/backtester.py
from dataclasses import dataclass
from typing import Dict, List, Callable, Optional
from datetime import datetime
import pandas as pd
import numpy as np

@dataclass
class BacktestConfig:
    initial_capital: float = 100000
    commission: float = 0.001  # 0.1%
    slippage: float = 0.0005   # 0.05%
    risk_free_rate: float = 0.02

@dataclass
class Trade:
    timestamp: datetime
    symbol: str
    side: str
    quantity: int
    price: float
    commission: float

class Backtester:
    """回测引擎"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.cash = config.initial_capital
        self.positions: Dict[str, int] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict] = []
    
    def run(
        self,
        data: pd.DataFrame,
        strategy: Callable,
        symbols: List[str]
    ) -> dict:
        """
        运行回测
        
        Args:
            data: OHLCV数据，MultiIndex (symbol, date)
            strategy: 策略函数，输入(data, date)，输出{symbol: decision}
            symbols: 股票列表
        """
        dates = data.index.get_level_values(1).unique()
        
        for date in dates:
            # 获取当日数据
            daily_data = data.xs(date, level=1)
            
            # 运行策略
            signals = strategy(data, date)
            
            # 执行交易
            for symbol, signal in signals.items():
                if signal == 'BUY' and symbol not in self.positions:
                    self._execute_buy(symbol, daily_data.loc[symbol], date)
                elif signal == 'SELL' and symbol in self.positions:
                    self._execute_sell(symbol, daily_data.loc[symbol], date)
            
            # 记录权益
            equity = self._calculate_equity(daily_data)
            self.equity_curve.append({
                'date': date,
                'equity': equity,
                'cash': self.cash,
                'positions': self.positions.copy()
            })
        
        return self._generate_report()
    
    def _execute_buy(self, symbol: str, price_data: pd.Series, date: datetime):
        price = price_data['Close'] * (1 + self.config.slippage)
        max_shares = int(self.cash * 0.95 / price)  # 留5%现金
        
        if max_shares > 0:
            cost = price * max_shares
            commission = cost * self.config.commission
            
            self.cash -= (cost + commission)
            self.positions[symbol] = max_shares
            
            self.trades.append(Trade(
                timestamp=date,
                symbol=symbol,
                side='BUY',
                quantity=max_shares,
                price=price,
                commission=commission
            ))
    
    def _execute_sell(self, symbol: str, price_data: pd.Series, date: datetime):
        if symbol not in self.positions:
            return
        
        quantity = self.positions[symbol]
        price = price_data['Close'] * (1 - self.config.slippage)
        revenue = price * quantity
        commission = revenue * self.config.commission
        
        self.cash += (revenue - commission)
        del self.positions[symbol]
        
        self.trades.append(Trade(
            timestamp=date,
            symbol=symbol,
            side='SELL',
            quantity=quantity,
            price=price,
            commission=commission
        ))
    
    def _calculate_equity(self, daily_data: pd.DataFrame) -> float:
        equity = self.cash
        for symbol, quantity in self.positions.items():
            if symbol in daily_data.index:
                equity += quantity * daily_data.loc[symbol, 'Close']
        return equity
    
    def _generate_report(self) -> dict:
        """生成回测报告"""
        equity_series = pd.Series(
            [e['equity'] for e in self.equity_curve],
            index=[e['date'] for e in self.equity_curve]
        )
        
        returns = equity_series.pct_change().dropna()
        
        # 绩效指标
        total_return = (equity_series.iloc[-1] / self.config.initial_capital - 1)
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1
        volatility = returns.std() * np.sqrt(252)
        sharpe = (annual_return - self.config.risk_free_rate) / volatility if volatility > 0 else 0
        
        # 回撤
        cummax = equity_series.cummax()
        drawdown = (equity_series - cummax) / cummax
        max_drawdown = drawdown.min()
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'total_trades': len(self.trades),
            'equity_curve': equity_series.to_dict()
        }
```

---

## 五、实施计划与任务清单

### 5.1 阶段一：基础框架（1-2周）

- [ ] 创建模块目录结构
  - [ ] `tradingagents/execution/`
  - [ ] `tradingagents/portfolio/`
  - [ ] `tradingagents/risk/`
  - [ ] `tradingagents/backtest/`
  - [ ] `tradingagents/scheduler/`
  - [ ] `tradingagents/storage/`

- [ ] 实现抽象基类和接口
  - [ ] `base_broker.py` - 券商接口基类
  - [ ] `base_strategy.py` - 策略接口基类
  - [ ] `base_data_feed.py` - 数据源接口基类

- [ ] 完成模拟交易引擎
  - [ ] `paper_broker.py` - 模拟交易实现
  - [ ] 状态持久化
  - [ ] 交易历史记录

- [ ] 基础仓位管理
  - [ ] `position_manager.py` - 仓位计算
  - [ ] 等权重分配
  - [ ] 风险平价分配
  - [ ] 凯利公式

### 5.2 阶段二：券商接入（2-3周）

- [ ] 美股 - Alpaca
  - [ ] 连接和认证
  - [ ] 账户和持仓查询
  - [ ] 下单和撤单
  - [ ] 实时行情订阅

- [ ] 加密货币 - Binance
  - [ ] REST API 封装
  - [ ] WebSocket 实时数据
  - [ ] 现货交易
  - [ ] 资金管理

- [ ] A股接口（可选）
  - [ ] 迅投QMT / 同花顺API
  - [ ] 交易日历适配

- [ ] 券商工厂模式
  - [ ] `broker_factory.py`
  - [ ] 统一配置管理

### 5.3 阶段三：风控系统（1-2周）

- [ ] 止损止盈机制
  - [ ] 固定止损
  - [ ] 移动止损
  - [ ] 时间止损
  - [ ] 盈亏比止盈

- [ ] 敞口监控
  - [ ] 单标的敞口
  - [ ] 板块敞口
  - [ ] 总敞口

- [ ] 回撤控制
  - [ ] 日内亏损限制
  - [ ] 最大回撤熔断

- [ ] 风险预警
  - [ ] 邮件通知
  - [ ] Webhook 通知

### 5.4 阶段四：回测与优化（1-2周）

- [ ] 回测引擎
  - [ ] 事件驱动回测
  - [ ] 向量化回测
  - [ ] 支持多标的

- [ ] 绩效分析
  - [ ] 收益率指标
  - [ ] 风险指标
  - [ ] 风险调整收益

- [ ] 可视化
  - [ ] 权益曲线
  - [ ] 回撤图
  - [ ] 持仓分析

### 5.5 阶段五：生产部署（1周）

- [ ] 调度系统
  - [ ] 开盘前任务
  - [ ] 盘中监控
  - [ ] 收盘后总结

- [ ] 监控告警
  - [ ] 系统健康检查
  - [ ] 异常告警

- [ ] 日志和持久化
  - [ ] 结构化日志
  - [ ] 数据库存储
  - [ ] 备份策略

---

## 六、技术选型建议

### 6.1 券商API

| 市场 | 推荐 | 特点 |
|------|------|------|
| 美股 | **Alpaca** | 免费API、支持加密货币、纸面交易 |
| 美股 | Interactive Brokers | 专业级、全球市场、佣金低 |
| A股 | 迅投QMT | 国内主流、支持量化 |
| A股 | 同花顺iFinD | 数据丰富 |
| 加密货币 | **Binance** | 最大交易所、API完善 |

### 6.2 数据库

| 用途 | 推荐 |
|------|------|
| 交易日志 | SQLite (轻量) / PostgreSQL (生产) |
| 时序数据 | TimescaleDB / InfluxDB |
| 缓存 | Redis |

### 6.3 调度

| 方案 | 适用场景 |
|------|---------|
| APScheduler | 单机部署 |
| Celery + Redis | 分布式部署 |
| Airflow | 复杂工作流 |

### 6.4 监控

| 方案 | 特点 |
|------|------|
| Prometheus + Grafana | 开源监控标配 |
| Sentry | 错误追踪 |
| 自定义Dashboard | Streamlit / Dash |

---

## 附录：快速启动命令

```bash
# 1. 克隆项目
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents

# 2. 创建环境
conda create -n tradingagents python=3.13
conda activate tradingagents
pip install -r requirements.txt

# 3. 配置API (创建.env文件)
echo "OPENAI_API_KEY=your_key_here" > .env

# 4. 运行CLI
python -m cli.main

# 5. Python代码调用
python -c "
from tradingagents.graph.trading_graph import TradingAgentsGraph
ta = TradingAgentsGraph(debug=True)
_, decision = ta.propagate('AAPL', '2024-05-10')
print(f'Decision: {decision}')
"
```

---

> 本文档将持续更新，记录实施进度和变更。