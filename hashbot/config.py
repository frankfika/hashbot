"""HashBot configuration management."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Telegram
    telegram_bot_token: str = Field(default="")
    telegram_webhook_url: str = Field(default="")

    # HashKey Chain
    hashkey_rpc_url: str = Field(default="https://hashkeychain-testnet.alt.technology")
    hashkey_chain_id: int = Field(default=177)  # Testnet
    wallet_private_key: str = Field(default="")
    merchant_address: str = Field(default="")

    # Token contracts
    hkdc_contract_address: str = Field(default="")

    # x402 Payment
    payment_timeout: int = Field(default=300)

    # A2A Protocol
    agent_card_url: str = Field(default="")
    agent_name: str = Field(default="HashBot")
    agent_description: str = Field(
        default="AI Agent with x402 payment support on HashKey Chain"
    )

    # API Server
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_debug: bool = Field(default=False)

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./hashbot.db")

    # OpenClaw Gateway
    openclaw_gateway_url: str = Field(default="http://localhost:18789")
    openclaw_gateway_token: str = Field(default="")
    openclaw_workspaces_dir: str = Field(default="~/.hashbot/workspaces")

    # Agent defaults
    default_agent_model: str = Field(default="claude-sonnet-4-20250514")
    max_agents_per_user: int = Field(default=3)

    # Wallet encryption
    wallet_encryption_key: str = Field(default="")  # Fernet key
    wallet_encryption_secret: str = Field(default="hashbot-wallet-secret")

    # Platform wallet (for payment settlement)
    platform_private_key: str = Field(default="")

    # Security
    api_secret_key: str = Field(default="")
    jwt_secret: str = Field(default="")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=60)
    cors_origins: list[str] = Field(default=["*"])

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    log_format: Literal["json", "console"] = Field(default="json")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
