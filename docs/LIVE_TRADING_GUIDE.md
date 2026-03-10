# Live Trading Guide - 实战交易指南

本文档介绍如何将 TradingAgents 用于实战股票交易。

## 📋 目录

1. [系统架构](#系统架构)
2. [快速开始](#快速开始)
3. [模块说明](#模块说明)
4. [实战配置](#实战配置)
5. [风险管理](#风险管理)
6. [券商接入](#券商接入)
7. [最佳实践](#最佳实践)

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     TradingAgents                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Analysts   │  │ Researchers │  │ Risk Mgmt   │        │
│  │  分析师群   │  │  研究员群   │  │  风险管理   │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │
│         └────────────────┼────────────────┘                │
│                          ▼                                 │
│                  ┌───────────────┐                         │
│                  │ Trader Agent  │                         │
│                  │   交易决策    │                         │
│                  └───────┬───────┘                         │
│                          │                                 │
├──────────────────────────┼─────────────────────────────────┤
│                  Trading System                            │
│  ┌───────────────────────┴───────────────────────┐         │
│  │              Signal Processing                │         │
│  └───────────────────────┬───────────────────────┘         │
│                          ▼                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Risk      │  │  Position   │  │  Execution  │        │
│  │  Manager    │  │  Manager    │  │   Layer     │        │
│  │  风控管理   │  │  仓位管理   │  │  执行层     │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │
│         └────────────────┼────────────────┘                │
│                          ▼                                 │
│  ┌───────────────────────────────────────────────┐         │
│  │              Broker Interface                 │         │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐       │         │
│  │  │ Paper   │  │ Alpaca  │  │ Custom  │       │         │
│  │  │ Broker  │  │ Broker  │  │ Broker  │       │         │
│  │  └─────────┘  └─────────┘  └─────────┘       │         │
│  └───────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 1. 安装依赖

```bash
# 基础依赖
pip install -r requirements.txt

# 可选：Alpaca 券商支持
pip install alpaca-py
```

### 2. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 文件
OPENAI_API_KEY=your_openai_key
ALPACA_API_KEY=your_alpaca_key        # 可选
ALPACA_SECRET_KEY=your_alpaca_secret  # 可选
```

### 3. 运行示例

```python
from tradingagents.trading_system import (
    TradingSystem,
    TradingConfig,
    TradingMode,
    TradingSignal,
    SignalType,
)

# 创建交易系统
config = TradingConfig(
    mode=TradingMode.PAPER,
    initial_capital=100000,
)
system = TradingSystem(config)
system.initialize()

# 创建交易信号
signal = TradingSignal(
    symbol="AAPL",
    signal=SignalType.BUY,
    confidence=0.8,
    reason="Strong earnings report",
)

# 执行交易
result = system.execute_signal(signal)
print(f"执行结果: {result.message}")
```

---

## 模块说明

### 1. Execution Layer (执行层)

执行层负责与券商交互，执行实际的交易操作。

```python
from tradingagents.execution import PaperBroker

# 创建模拟交易
broker = PaperBroker(
    initial_capital=100000,
    commission_rate=0.001,  # 0.1% 手续费
    slippage_rate=0.0005,   # 0.05% 滑点
)

# 连接
broker.connect()

# 买入
result = broker.buy_market("AAPL", quantity=100)

# 获取持仓
positions = broker.get_positions()

# 断开连接
broker.disconnect()
```

### 2. Risk Manager (风险管理)

风险管理模块提供多层次的风险控制。

```python
from tradingagents.risk import RiskManager, RiskRules

# 配置风险规则
rules = RiskRules(
    max_single_position=0.10,    # 单个持仓最大10%
    max_daily_loss=0.03,         # 日损失上限3%
    max_drawdown=0.15,           # 最大回撤15%
    default_stop_loss=0.05,      # 默认止损5%
)

rm = RiskManager(rules=rules, initial_capital=100000)

# 注册持仓并设置止损
rm.register_position(
    symbol="AAPL",
    quantity=100,
    entry_price=150.0,
    stop_loss_pct=0.05,
)

# 检查止损
alert = rm.check_stop_loss_take_profit("AAPL", current_price=140.0)
if alert:
    print(f"触发警报: {alert.message}")
```

### 3. Position Manager (仓位管理)

仓位管理模块提供多种仓位计算策略。

```python
from tradingagents.portfolio import PositionManager, AllocationMethod, Signal

pm = PositionManager(
    total_capital=100000,
    max_single_position=0.10,
)

# 创建信号
signals = [
    Signal(symbol="AAPL", decision="BUY", confidence=0.8, price=150.0),
    Signal(symbol="MSFT", decision="BUY", confidence=0.7, price=300.0),
]

# 计算仓位分配
allocations = pm.allocate_portfolio(
    signals,
    method=AllocationMethod.RISK_PARITY,  # 或 EQUAL_WEIGHT, KELLY
)

for alloc in allocations:
    print(f"{alloc.symbol}: {alloc.shares} 股, 价值 ${alloc.value:,.2f}")
```

### 4. Backtester (回测)

回测模块用于验证交易策略。

```python
from tradingagents.backtest import Backtester, BacktestConfig
import pandas as pd

# 准备数据
data = pd.DataFrame({
    'Close': [...],  # 收盘价序列
    'Volume': [...],
}, index=pd.DatetimeIndex(...))

# 定义策略
def my_strategy(data, date, positions):
    """简单的移动平均策略"""
    # ... 策略逻辑
    return {"AAPL": "BUY"}  # 返回交易决策

# 运行回测
config = BacktestConfig(initial_capital=100000)
backtester = Backtester(config)
results = backtester.run(data, my_strategy)

# 查看结果
print(f"总回报: {results['summary']['total_return_pct']:.2f}%")
print(f"夏普比率: {results['risk_metrics']['sharpe_ratio']:.2f}")
```

---

## 实战配置

### 推荐配置模板

```python
from tradingagents.trading_system import TradingSystemBuilder, TradingMode
from tradingagents.portfolio.position_manager import AllocationMethod

system = (TradingSystemBuilder()
    # 基本设置
    .with_mode(TradingMode.PAPER)  # 先用模拟交易测试
    .with_capital(100000)
    
    # 仓位管理
    .with_position_sizing(AllocationMethod.RISK_PARITY)
    .with_max_position_pct(0.08)   # 单仓最大8%
    .with_max_positions(12)         # 最多12个持仓
    
    # 风险控制
    .with_risk_rules(
        stop_loss_pct=0.05,         # 5% 止损
        take_profit_pct=0.15,       # 15% 止盈
        max_daily_loss_pct=0.02,    # 日损失2%暂停
        max_drawdown_pct=0.10,      # 回撤10%停止
    )
    
    # 信号过滤
    .with_min_confidence(0.7)       # 信号置信度>=70%才执行
    
    .build())

system.initialize()
```

---

## 风险管理

### 风险控制层级

1. **信号层面**: 置信度过滤
2. **仓位层面**: 单仓限制、总数限制
3. **组合层面**: 行业分散、相关性控制
4. **账户层面**: 日损失限制、回撤控制

### 止损策略

```python
# 固定止损
rm.register_position("AAPL", 100, 150.0, stop_loss_pct=0.05)

# 移动止损
rm.enable_trailing_stop("AAPL", trailing_pct=0.05)

# 手动设置止损位
rm.set_stop_loss("AAPL", stop_price=140.0)
```

---

## 券商接入

### Alpaca (美股)

```python
from tradingagents.execution import AlpacaBroker

broker = AlpacaBroker(
    api_key="your_key",
    secret_key="your_secret",
    paper=True,  # 使用模拟账户测试
)

# 其余操作与 PaperBroker 相同
```

### 自定义券商

继承 `BaseBroker` 实现自定义券商：

```python
from tradingagents.execution.base_broker import BaseBroker, Order, OrderResult

class MyBroker(BaseBroker):
    def connect(self) -> bool:
        # 实现连接逻辑
        pass
    
    def get_account(self):
        # 实现账户查询
        pass
    
    def place_order(self, order: Order) -> OrderResult:
        # 实现下单逻辑
        pass
    
    # ... 实现其他抽象方法
```

---

## 最佳实践

### 1. 开发流程

```
策略开发 → 回测验证 → 模拟交易 → 小资金实盘 → 正式实盘
```

### 2. 安全建议

- ✅ 始终先用 PAPER 模式测试
- ✅ 设置合理的止损止盈
- ✅ 控制单仓和总仓位
- ✅ 监控系统运行状态
- ❌ 不要使用全部资金
- ❌ 不要忽视风险警报

### 3. 监控指标

```python
# 获取系统状态
status = system.get_status()

# 风险报告
risk_report = system.risk_manager.get_risk_report()

# 交易统计
summary = system.get_trading_summary()
```

---

## 常见问题

**Q: 如何从模拟切换到实盘？**

```python
# 修改配置
config.mode = TradingMode.LIVE

# 使用真实券商
from tradingagents.execution import AlpacaBroker
broker = AlpacaBroker(api_key, secret_key, paper=False)
```

**Q: 如何处理交易信号？**

Agent 产生的决策会被转换为 `TradingSignal`：

```python
# 从 Agent 输出创建信号
signal = TradingSignal(
    symbol=agent_decision['symbol'],
    signal=SignalType[agent_decision['action']],
    confidence=agent_decision['confidence'],
    reason=agent_decision['reasoning'],
)
```

---

## 支持

- GitHub Issues: [项目地址]
- 文档: [文档地址]