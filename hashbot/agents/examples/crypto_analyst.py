"""Crypto Analyst Agent - Token analysis and market insights."""

from typing import Any

from hashbot.a2a.messages import Task
from hashbot.agents.base import BaseAgent, agent_card
from hashbot.agents.registry import register_agent


@register_agent("crypto_analyst")
@agent_card(
    name="Crypto Analyst",
    description="Professional cryptocurrency analysis with market insights, "
    "technical analysis, and investment recommendations.",
    price_per_call=0.1,
    currency="HKDC",
    skills=[
        {
            "id": "analyze_token",
            "name": "Token Analysis",
            "description": "Analyze a cryptocurrency token",
            "tags": ["crypto", "analysis", "defi"],
        },
        {
            "id": "market_overview",
            "name": "Market Overview",
            "description": "Get current market overview",
            "tags": ["crypto", "market"],
        },
    ],
    version="1.0.0",
    author="HashBot Team",
)
class CryptoAnalystAgent(BaseAgent):
    """AI-powered cryptocurrency analysis agent."""

    # Mock data for demo
    MOCK_TOKENS = {
        "BTC": {
            "name": "Bitcoin",
            "price": 67500.00,
            "change_24h": 2.5,
            "market_cap": "1.32T",
            "recommendation": "HOLD",
            "confidence": 0.85,
        },
        "ETH": {
            "name": "Ethereum",
            "price": 3450.00,
            "change_24h": 3.2,
            "market_cap": "415B",
            "recommendation": "BUY",
            "confidence": 0.78,
        },
        "HSK": {
            "name": "HashKey Token",
            "price": 1.25,
            "change_24h": 5.8,
            "market_cap": "500M",
            "recommendation": "STRONG BUY",
            "confidence": 0.82,
        },
    }

    async def process(self, task: Task) -> dict[str, Any]:
        """Process analysis request."""
        # Extract user message
        user_text = ""
        if task.history:
            for part in task.history[-1].parts:
                if hasattr(part, "text"):
                    user_text = part.text
                    break

        # Determine skill based on message
        user_text_lower = user_text.lower()

        if any(
            token.lower() in user_text_lower for token in self.MOCK_TOKENS.keys()
        ):
            # Token analysis
            for token in self.MOCK_TOKENS.keys():
                if token.lower() in user_text_lower:
                    return await self._analyze_token(task, token)

        elif "market" in user_text_lower or "overview" in user_text_lower:
            # Market overview
            return await self._market_overview(task)

        else:
            # Default: ask for specific token
            return self._create_success_response(
                task,
                text="Which token would you like me to analyze? "
                "I can analyze BTC, ETH, HSK and more. "
                "Or ask for a 'market overview'.",
            )

    async def _analyze_token(self, task: Task, symbol: str) -> dict[str, Any]:
        """Analyze a specific token."""
        token_data = self.MOCK_TOKENS.get(symbol.upper(), {})

        if not token_data:
            return self._create_success_response(
                task,
                text=f"Token {symbol} not found in my database. "
                "Try BTC, ETH, or HSK.",
            )

        # Generate analysis
        analysis = f"""
**{token_data['name']} ({symbol.upper()}) Analysis**

📊 **Current Price:** ${token_data['price']:,.2f}
📈 **24h Change:** {'+' if token_data['change_24h'] > 0 else ''}{token_data['change_24h']}%
💰 **Market Cap:** ${token_data['market_cap']}

**Technical Indicators:**
• RSI (14): 55
• MACD: {'Bullish' if token_data['change_24h'] > 0 else 'Bearish'}
• Moving Average: {'Above' if token_data['change_24h'] > 0 else 'Below'} 50-day MA

**Recommendation:** {token_data['recommendation']}
**Confidence:** {token_data['confidence'] * 100:.0f}%

⚠️ *This is AI-generated analysis for educational purposes only. Not financial advice.*
"""

        return self._create_success_response(
            task,
            text=analysis.strip(),
            data={
                "symbol": symbol.upper(),
                "price": token_data["price"],
                "change_24h": token_data["change_24h"],
                "recommendation": token_data["recommendation"],
                "confidence": token_data["confidence"],
            },
        )

    async def _market_overview(self, task: Task) -> dict[str, Any]:
        """Generate market overview."""
        overview = """
**Crypto Market Overview**

📊 **Market Sentiment:** Bullish (Fear & Greed Index: 72)

**Top Movers (24h):**
• HSK: +5.8% 🚀
• ETH: +3.2% 📈
• BTC: +2.5% 📈

**Market Stats:**
• Total Market Cap: $2.45T
• 24h Volume: $89B
• BTC Dominance: 52.3%

**Key Events:**
• HashKey Chain mainnet upgrade scheduled
• ETH ETF trading volume increasing
• BTC halving effects continuing

**AI Outlook:** Generally bullish conditions with institutional interest
remaining strong. Consider DCA strategy for long-term holdings.

⚠️ *AI analysis for educational purposes only.*
"""

        return self._create_success_response(
            task,
            text=overview.strip(),
            data={
                "sentiment": "bullish",
                "fear_greed_index": 72,
                "total_market_cap": "2.45T",
                "btc_dominance": 52.3,
            },
        )
