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

## 🧰 Prerequisites

- Python 3.11+（建议使用虚拟环境）
- 可选：Docker / Docker Compose
- 可选：Redis（缓存）
- 需要准备：Telegram Bot Token、HashKey RPC（默认使用测试网）

## 🚀 Quick Start

### 1. Clone & Install（本地开发）

```bash
git clone https://github.com/your-org/hashbot.git
cd hashbot
# 创建并激活虚拟环境（Windows）
python -m venv .venv
.venv\Scripts\activate

# 安装
pip install -e .
# 开发依赖（可选）
pip install -e .[dev]
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Run

```bash
# Development（本地）
python -m server.main
# 或使用项目脚本（安装后会生成命令）
hashbot

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

## ⚙️ Configuration

- 常用必填
  - TELEGRAM_BOT_TOKEN：Telegram 机器人令牌
  - WALLET_PRIVATE_KEY：商户钱包私钥（用于链上结算）
  - MERCHANT_ADDRESS：商户地址
- 常用可选
  - HASHKEY_RPC_URL（默认测试网）：https://hashkeychain-testnet.alt.technology
  - HASHKEY_CHAIN_ID（默认测试网）：177
  - API_HOST（默认 0.0.0.0），API_PORT（默认 8000），API_DEBUG（默认 false）
  - DATABASE_URL（默认 sqlite+aiosqlite:///./hashbot.db）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR，默认 INFO），LOG_FORMAT（json/console，默认 json）
  - JWT_* 与 API_SECRET_KEY（如需开启鉴权）

示例 .env（节选）：

```dotenv
TELEGRAM_BOT_TOKEN=xxxxxx
HASHKEY_RPC_URL=https://hashkeychain-testnet.alt.technology
HASHKEY_CHAIN_ID=177
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=true
DATABASE_URL=sqlite+aiosqlite:///./hashbot.db
LOG_LEVEL=INFO
LOG_FORMAT=json
```

安全提示：不要将私钥、Token 等敏感信息提交到仓库或日志。

## 📲 Telegram 集成

- 通过 BotFather 创建机器人并获取 TELEGRAM_BOT_TOKEN
- Webhook 接口：POST /webhook/telegram（开发环境默认回显）
- 在生产环境中建议使用 python-telegram-bot 的 Application 来处理更新
- Bot 内置命令：/start、/help、/agents、/wallet、/balance、/pay

## 📘 API 文档

- 健康检查：GET /health
- 列出代理：GET /agents
- A2A 发现：GET /a2a/.well-known/agent.json
- 任务发送：POST /a2a
- 如果 API_DEBUG=true，会开放 Swagger：/docs 与 ReDoc：/redoc

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

## 🧪 Development

- 运行测试

```bash
pytest -q
```

- 代码静态检查

```bash
ruff check .
mypy .
```

## 🎥 Demo

- 启动后访问：/health 查看服务状态
- 示例 Agents：Crypto Analyst、Translator、Code Reviewer
- Telegram 中使用 /agents 浏览并调用 Agent，付费由 x402 自动处理

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
