"""Database package for HashBot."""

from hashbot.db.engine import close_db, get_db, init_db
from hashbot.db.crud import (  # noqa: F401 – re-exported convenience helpers
    # User helpers
    get_user_by_telegram_id,
    get_or_create_user,
    # Agent helpers
    get_agent_by_id,
    get_public_agents,
    get_user_agents,
    create_agent,
    update_agent,
    delete_agent,
    # Wallet helpers
    get_user_wallet,
    get_wallet_by_telegram_id,
    get_or_create_wallet,
    # Payment helpers
    record_payment,
    complete_payment,
    # Skill helpers
    get_agent_skills,
    install_skill,
    remove_skill,
)

__all__ = [
    # Engine
    "init_db",
    "get_db",
    "close_db",
    # User helpers
    "get_user_by_telegram_id",
    "get_or_create_user",
    # Agent helpers
    "get_agent_by_id",
    "get_public_agents",
    "get_user_agents",
    "create_agent",
    "update_agent",
    "delete_agent",
    # Wallet helpers
    "get_user_wallet",
    "get_wallet_by_telegram_id",
    "get_or_create_wallet",
    # Payment helpers
    "record_payment",
    "complete_payment",
    # Skill helpers
    "get_agent_skills",
    "install_skill",
    "remove_skill",
]
