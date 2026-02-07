<p align="center">
  <img src="docs/assets/logo.png" alt="HashBot Logo" width="200" height="200">
</p>

<h1 align="center">HashBot</h1>

<p align="center">
  <strong>Agent Economy on HashKey Chain</strong>
</p>

<p align="center">
  <em>Bot 用 Bot，自动付费 — 真正的 Agent Economy</em>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#features">Features</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#demo">Demo</a> •
  <a href="#api">API</a>
</p>

---

## 🎯 What is HashBot?

HashBot 是一个开源的 **Agent 经济框架**，让 AI Agent 可以相互调用并自动付费。

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│    👤 User                                                      │
│      │                                                          │
│      ▼                                                          │
│   ┌──────────────┐                                              │
│   │  Telegram    │  ◄── 用户友好的交互界面                        │
│   │    Bot       │                                              │
│   └──────┬───────┘                                              │
│          │                                                      │
│          ▼                                                      │
│   ┌──────────────┐    A2A Protocol    ┌──────────────┐         │
│   │   HashBot    │ ◄────────────────► │  Other       │         │
│   │   Agent      │                    │  Agents      │         │
│   └──────┬───────┘                    └──────────────┘         │
│          │                                                      │
│          │ x402 Payment                                         │
│          ▼                                                      │
│   ┌──────────────┐                                              │
│   │  HashKey     │  ◄── 合规 Web3 支付，低 Gas                    │
│   │   Chain      │                                              │
│   └──────────────┘                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔗 **A2A Protocol** | Google 开源的 Agent 间通信标准 |
| 💰 **x402 Payment** | HTTP 402 自动付费，Agent 调用即结算 |
| ⛓️ **HashKey Chain** | 合规 Web3 支付层，港币稳定币 (HKDC) |
| 🤖 **Telegram Bot** | 用户友好的交互界面 |
| 🧩 **Plugin System** | 轻松创建自己的付费 Agent |

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/your-org/hashbot.git
cd hashbot
pip install -e .
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Run

```bash
# Development
python -m server.main

# Production (Docker)
docker-compose up -d
```

### 4. Test the API

```bash
# Get agent info
curl http://localhost:8000/a2a/.well-known/agent.json

# Send a task
curl -X POST http://localhost:8000/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "tasks/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Analyze BTC"}]
      },
      "metadata": {"skill_id": "crypto_analyst"}
    }
  }'
```

## 🏗️ Architecture

```
hashbot/
├── hashbot/                 # Core library
│   ├── a2a/                # A2A Protocol implementation
│   │   ├── messages.py     # Message types (Task, AgentCard, etc.)
│   │   ├── protocol.py     # Protocol client
│   │   └── executor.py     # Request handler
│   │
│   ├── x402/               # x402 Payment extension
│   │   ├── payment.py      # Payment types
│   │   ├── executor.py     # Payment flow
│   │   └── verification.py # Signature verification
│   │
│   ├── hashkey/            # HashKey Chain integration
│   │   ├── chain.py        # Chain connection
│   │   ├── wallet.py       # Wallet management
│   │   └── tokens.py       # HKDC token
│   │
│   ├── bot/                # Telegram Bot
│   │   ├── handlers.py     # Message handlers
│   │   └── keyboards.py    # Inline keyboards
│   │
│   └── agents/             # Agent framework
│       ├── base.py         # BaseAgent class
│       ├── registry.py     # Agent registry
│       └── examples/       # Example agents
│           ├── crypto_analyst.py
│           ├── translator.py
│           └── code_reviewer.py
│
├── server/                  # FastAPI server
│   ├── main.py             # Entry point
│   └── routes/             # API routes
│       ├── a2a.py          # A2A endpoints
│       ├── webhook.py      # Telegram webhook
│       └── health.py       # Health checks
│
└── tests/                   # Test suite
```

## 🤖 Built-in Agents

### 1. Crypto Analyst 📊
```
Price: 0.1 HKDC per call
Skills: Token analysis, Market overview
```

### 2. AI Translator 🌐
```
Price: 0.05 HKDC per call
Skills: Multi-language translation (50+ languages)
```

### 3. Code Reviewer 🔍
```
Price: 0.5 HKDC per call
Skills: Smart contract audit, Code review
```

## 💡 Create Your Own Agent

```python
from hashbot.agents import BaseAgent, agent_card
from hashbot.agents.registry import register_agent

@register_agent("my_agent")
@agent_card(
    name="My Agent",
    description="Description of what your agent does",
    price_per_call=0.1,  # Price in HKDC
    currency="HKDC"
)
class MyAgent(BaseAgent):

    async def process(self, task):
        # Your logic here
        user_message = task.history[-1].parts[0].text

        result = f"Processed: {user_message}"

        return self._create_success_response(
            task,
            text=result,
            data={"status": "success"}
        )
```

## 💳 x402 Payment Flow

```
┌──────────────┐                      ┌──────────────┐
│    Client    │                      │   Merchant   │
│    Agent     │                      │    Agent     │
└──────┬───────┘                      └──────┬───────┘
       │                                     │
       │  1. Request Service                 │
       │────────────────────────────────────►│
       │                                     │
       │  2. 402 Payment Required            │
       │    (Price: 0.1 HKDC)               │
       │◄────────────────────────────────────│
       │                                     │
       │  3. Sign & Submit Payment           │
       │    (EIP-712 Signature)             │
       │────────────────────────────────────►│
       │                                     │
       │                      4. Settle On-Chain
       │                         (HashKey Chain)
       │                                     │
       │  5. Service Result + Receipt        │
       │◄────────────────────────────────────│
       │                                     │
```

## 🔧 API Reference

### Agent Discovery
```http
GET /a2a/.well-known/agent.json
```

### Send Task
```http
POST /a2a
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": "unique-id",
  "method": "tasks/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "Your request"}]
    },
    "metadata": {
      "skill_id": "crypto_analyst"
    }
  }
}
```

### List Agents
```http
GET /agents
```

## 🌐 HashKey Chain

| Network | RPC URL | Chain ID |
|---------|---------|----------|
| Mainnet | https://mainnet.hashkeychain.io | 133 |
| Testnet | https://hashkeychain-testnet.alt.technology | 177 |

## 📚 Related Projects

- [A2A Protocol](https://github.com/google/a2a) - Google Agent2Agent Protocol
- [x402 Extension](https://github.com/google-agentic-commerce/a2a-x402) - Payment Extension
- [HashKey Chain](https://hashkey.cloud/) - Compliant Web3 Infrastructure

## 📄 License

Apache-2.0

---

<p align="center">
  <strong>Built for the Agent Economy 🚀</strong>
</p>
