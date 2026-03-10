# Product Requirements Document: AI-Agent Trading Hub

## 1. Project Goal
Build a professional-grade trading platform that leverages multi-agent intelligence (based on TauricResearch/TradingAgents) to provide investment insights and execute trades across Crypto, US, and HK markets with a Human-in-the-loop (HITL) safety mechanism.

## 2. Target Markets
- **Crypto**: Binance, OKX (via CCXT)
- **Stocks**: US/HK/A-share (via Futu Open API / IBKR)

## 3. Core Features (MVP)
### A. Agent Intelligence
- Integrate 3 specialized agents: Technical Analyst, Fundamental Researcher, and Sentiment Auditor.
- A "Portfolio Manager" agent to synthesize reports and propose trades.

### B. Human-in-the-Loop (HITL)
- **Approval Workflow**: All trade proposals must stay in a "PENDING" state until a user clicks "Approve" on the Web UI.
- **Manual Overwrite**: User can manually close any position or pause the AI agents via a "Kill Switch".

### C. Dashboard & Monitoring
- **Thinking Stream**: Real-time display of agent reasoning (logs/thoughts).
- **Portfolio Tracker**: Real-time PnL, balance, and position visualization.
- **Trade History**: Audit log of all AI proposals and human decisions.

## 4. User Experience
- Minimalist web interface (Dark mode preferred).
- Mobile-responsive (for approving trades on the go).
- Low-latency updates for price and order status.