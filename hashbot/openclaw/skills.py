"""Built-in HashBot skills (SKILL.md content for OpenClaw agents)."""

BUILTIN_SKILLS: dict[str, dict[str, str]] = {
    "hsk-crypto-price": {
        "name": "Crypto Price Checker",
        "description": "Check real-time crypto prices and market data",
        "content": (
            "# Crypto Price Checker\n\n"
            "You can check cryptocurrency prices and market data.\n\n"
            "## Capabilities\n"
            "- Get current price of any token (BTC, ETH, HSK, etc.)\n"
            "- Show 24h price change and volume\n"
            "- Compare token prices across exchanges\n"
            "- Provide market cap and ranking info\n\n"
            "## Usage\n"
            "When the user asks about crypto prices, fetch the latest data "
            "and present it in a clear, formatted way.\n"
        ),
    },
    "hsk-wallet-ops": {
        "name": "Wallet Operations",
        "description": "Check wallet balances and transaction history on HashKey Chain",
        "content": (
            "# Wallet Operations\n\n"
            "You can interact with wallets on HashKey Chain.\n\n"
            "## Capabilities\n"
            "- Check HSK and HKDC balances\n"
            "- View recent transaction history\n"
            "- Look up transaction details by hash\n"
            "- Check token allowances and approvals\n\n"
            "## Usage\n"
            "When the user asks about their wallet, use the HashKey Chain RPC "
            "to fetch on-chain data and present it clearly.\n"
        ),
    },
    "hsk-defi-swap": {
        "name": "DeFi Token Swap",
        "description": "Swap tokens on HashKey Chain DEXes",
        "content": (
            "# DeFi Token Swap\n\n"
            "You can help users swap tokens on HashKey Chain decentralized exchanges.\n\n"
            "## Capabilities\n"
            "- Get swap quotes for token pairs\n"
            "- Execute token swaps via DEX aggregator\n"
            "- Check liquidity pool info\n"
            "- Estimate gas costs for swaps\n\n"
            "## Usage\n"
            "When the user wants to swap tokens, get a quote first, "
            "show the details, and ask for confirmation before executing.\n"
            "Always warn about slippage and price impact.\n"
        ),
    },
}


def get_skill(slug: str) -> dict[str, str] | None:
    """Get a built-in skill by slug."""
    return BUILTIN_SKILLS.get(slug)


def list_skills() -> list[dict[str, str]]:
    """List all built-in skills."""
    return [
        {"slug": slug, "name": s["name"], "description": s["description"]}
        for slug, s in BUILTIN_SKILLS.items()
    ]
