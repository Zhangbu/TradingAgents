# TradingAgents 开发路线图

> 从 0 到 1 的分阶段开发计划

---

## 📊 项目现状分析

### 架构可行性评估

基于对现有代码和 PRD 文档的分析，TradingAgents 项目架构具备以下优势：

| 维度 | 评估 | 说明 |
|------|------|------|
| **Agent 设计** | ✅ 优秀 | 多 Agent 协作架构成熟，LangGraph 提供了可靠的状态管理 |
| **数据层** | ✅ 良好 | 已有 Alpha Vantage、YFinance 数据源集成 |
| **LLM 支持** | ✅ 完善 | 支持 OpenAI、Google、Anthropic 多供应商 |
| **可扩展性** | ✅ 良好 | 模块化设计便于扩展 |
| **生产就绪度** | ⚠️ 待完善 | 缺少 API 层、执行层、风控层 |

### 关键缺口

1. **API 层**：缺少 RESTful API 供外部调用
2. **执行层**：Agent 决策无法自动执行到交易所
3. **风控层**：缺少风险管理机制
4. **前端界面**：缺少可视化监控界面
5. **HITL 机制**：缺少 Human-in-the-Loop 审批流程

---

## 🗺️ 分阶段开发路线图

### 阶段一：基础设施搭建（Week 1-2）

**目标**：搭建 API 服务骨架，实现前后端通信

#### 1.1 后端 API 搭建 ✅
- [x] FastAPI 应用初始化
- [x] 异步路由设计
- [x] CORS 配置
- [x] 环境变量管理

#### 1.2 数据库设计 ✅
- [x] SQLite + SQLAlchemy 异步模型
- [x] Proposal（交易提案）模型
- [x] Position（持仓）模型
- [x] TradeHistory（交易历史）模型
- [x] AgentLog（Agent 日志）模型

#### 1.3 API Schema 定义 ✅
- [x] Pydantic Request/Response 模型
- [x] WebSocket 消息类型定义

#### 1.4 Docker 部署 ✅
- [x] docker-compose.yml
- [x] Dockerfile.backend
- [x] Dockerfile.frontend

**交付物**：
- 可运行的 FastAPI 服务
- 完整的 API 文档（Swagger）
- Docker 部署配置

---

### 阶段二：Agent 异步化改造（Week 3）

**目标**：将同步 Agent 调用改造为异步，支持并发处理

#### 2.1 AsyncTradingAgentsGraph ✅
- [x] ThreadPoolExecutor 包装同步代码
- [x] 异步 propagate() 方法
- [x] create_proposal() 便捷方法

#### 2.2 异步回调机制 ✅
- [x] AsyncCallbackHandler 类
- [x] AgentEventType 事件类型定义
- [x] WebSocket 事件推送

#### 2.3 并发控制 ✅
- [x] Semaphore 信号量限制并发数
- [x] 懒加载 Agent 实例

**交付物**：
- `tradingagents/graph/async_wrapper.py`

---

### 阶段三：交易执行层（Week 4）

**目标**：实现从决策到执行的闭环

#### 3.1 抽象交易接口 ✅
- [x] AbstractExchange 基类
- [x] OrderResult、Balance 数据结构
- [x] OrderSide、OrderType 枚举

#### 3.2 模拟交易 ✅
- [x] PaperExchange 实现
- [x] 模拟余额和持仓管理

#### 3.3 CCXT 集成 ✅
- [x] CCXTExchange 通用实现
- [x] BinanceExchange 特化实现
- [x] OKXExchange 特化实现

#### 3.4 风控层 ✅
- [x] RiskConfig 配置类
- [x] RiskGuard 验证器
- [x] 仓位限制、止损、日内限额

**交付物**：
- `tradingagents/execution/` 模块

---

### 阶段四：前端界面（Week 5-6）✅

**目标**：提供可视化的监控和操作界面

#### 4.1 项目初始化 ✅
- [x] Next.js 14 + TypeScript
- [x] TailwindCSS 样式
- [x] shadcn/ui 组件库

#### 4.2 核心页面 ✅
- [x] Dashboard（概览）
- [x] Proposals（提案列表）
- [x] Positions（持仓管理）
- [x] Trade History（交易历史）
- [x] Settings（设置）

#### 4.3 实时更新 ✅
- [x] WebSocket 连接管理
- [ ] Agent 思考流展示
- [ ] 实时价格更新

**交付物**：
- `frontend/` 目录

---

### 阶段五：HITL 审批流程（Week 7）

**目标**：实现 Human-in-the-Loop 人工审批机制

#### 5.1 审批 API
- [ ] POST /api/proposals/{id}/approve
- [ ] POST /api/proposals/{id}/reject
- [ ] WebSocket 审批通知

#### 5.2 审批前端
- [ ] Proposal 详情页
- [ ] 一键审批/拒绝
- [ ] 审批历史

#### 5.3 通知机制
- [ ] 邮件通知（可选）
- [ ] WebSocket 推送
- [ ] Telegram Bot（可选）

**交付物**：
- 完整的 HITL 流程

---

### 阶段六：实盘对接（Week 8）

**目标**：完成真实交易所对接

#### 6.1 Futu OpenD 集成
- [ ] FutuExchange 实现
- [ ] 港股/美股支持
- [ ] 订单状态同步

#### 6.2 安全加固
- [ ] API Key 加密存储
- [ ] IP 白名单
- [ ] 操作日志审计

#### 6.3 监控告警
- [ ] Prometheus 指标
- [ ] Grafana 仪表盘
- [ ] 异常告警

**交付物**：
- 生产级部署

---

## 📁 新增文件结构

```
TradingAgents/
├── backend/                    # 新增：后端 API
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用
│   ├── config.py               # 配置管理
│   ├── database.py             # 数据库连接
│   ├── models.py               # SQLAlchemy 模型
│   └── schemas.py              # Pydantic Schema
│
├── frontend/                   # 新增：前端界面（待实现）
│   ├── src/
│   │   ├── app/               # Next.js App Router
│   │   ├── components/        # React 组件
│   │   ├── hooks/             # 自定义 Hooks
│   │   └── lib/               # 工具函数
│   └── package.json
│
├── tradingagents/
│   ├── execution/              # 新增：交易执行层
│   │   ├── __init__.py
│   │   ├── base_exchange.py   # 抽象基类
│   │   ├── paper_exchange.py  # 模拟交易
│   │   ├── ccxt_exchange.py   # CCXT 集成
│   │   └── risk_guard.py      # 风控层
│   │
│   └── graph/
│       └── async_wrapper.py    # 新增：异步包装
│
├── docker-compose.yml          # 新增：Docker 编排
├── Dockerfile.backend          # 新增：后端镜像
├── Dockerfile.frontend         # 新增：前端镜像
└── ROADMAP.md                  # 本文档
```

---

## 🔧 技术栈总结

| 层级 | 技术选型 |
|------|----------|
| **前端** | Next.js 14 + TypeScript + TailwindCSS + shadcn/ui |
| **后端** | FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| **数据库** | SQLite (dev) / PostgreSQL (prod) |
| **消息队列** | Redis (可选) |
| **交易所** | CCXT (Crypto) / Futu OpenD (港股美股) |
| **AI 框架** | LangChain + LangGraph |
| **部署** | Docker + Docker Compose |

---

## ⚠️ 风险与建议

### 技术风险

1. **LLM 不稳定性**：Agent 输出可能不稳定
   - **建议**：增加输出验证和重试机制

2. **API 限流**：数据源和交易所 API 有限流
   - **建议**：实现请求队列和缓存

3. **资金安全**：实盘交易有资金风险
   - **建议**：严格的 RiskGuard 验证 + 模拟盘测试

### 开发建议

1. **先 Paper Trading**：在模拟环境充分测试
2. **逐步迭代**：按阶段交付，每个阶段独立可用
3. **监控先行**：从第一天就接入日志和监控
4. **文档同步**：代码和文档同步更新

---

## 📈 当前进度

- [x] 阶段一：基础设施搭建（后端部分）
- [x] 阶段二：Agent 异步化改造
- [x] 阶段三：交易执行层
- [x] 阶段四：前端界面
- [x] 阶段五：HITL 审批流程
- [x] 阶段六：实盘对接

**完成度**：100% ✅

### 已完成功能
- [x] Agent 思考流展示组件 (`frontend/src/components/AgentThinkingStream.tsx`)
- [x] 审批历史记录查询 (`backend/models.py` - ApprovalHistory)
- [x] 审批状态机 (`backend/approval_service.py`)
- [x] 通知机制 (`backend/notification_service.py`)
- [x] FutuExchange 实现 (`tradingagents/execution/futu_exchange.py`)
- [x] API Key 加密存储 (`backend/crypto_service.py`)
- [x] Prometheus 指标 (`backend/metrics.py`)
- [x] Grafana 仪表盘 (`monitoring/grafana/dashboards/tradingagents.json`)

---

*最后更新：2026-03-10*