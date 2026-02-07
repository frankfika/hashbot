"""Telegram inline keyboard builders."""

from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class InlineKeyboards:
    """Factory for inline keyboards."""

    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Main menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("🤖 Agents", callback_data="menu:agents"),
                InlineKeyboardButton("💼 Wallet", callback_data="menu:wallet"),
            ],
            [
                InlineKeyboardButton("💰 Balance", callback_data="menu:balance"),
                InlineKeyboardButton("❓ Help", callback_data="menu:help"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def agent_list(agents: list[dict[str, Any]]) -> InlineKeyboardMarkup:
        """Agent selection keyboard."""
        keyboard = []

        for agent in agents:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🤖 {agent['name']} ({agent['price']})",
                        callback_data=f"agent:{agent['id']}",
                    )
                ]
            )

        keyboard.append(
            [InlineKeyboardButton("◀️ Back", callback_data="menu")]
        )

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def wallet_menu(has_wallet: bool = False) -> InlineKeyboardMarkup:
        """Wallet management keyboard."""
        if has_wallet:
            keyboard = [
                [
                    InlineKeyboardButton("💰 Balance", callback_data="wallet:balance"),
                    InlineKeyboardButton("📤 Send", callback_data="wallet:send"),
                ],
                [
                    InlineKeyboardButton("📋 Address", callback_data="wallet:address"),
                    InlineKeyboardButton("🔑 Export", callback_data="wallet:export"),
                ],
                [InlineKeyboardButton("◀️ Back", callback_data="menu")],
            ]
        else:
            keyboard = [
                [
                    InlineKeyboardButton(
                        "➕ Create Wallet", callback_data="wallet_create"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "📥 Import Wallet", callback_data="wallet_import"
                    ),
                ],
                [InlineKeyboardButton("◀️ Back", callback_data="menu")],
            ]

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def confirm_payment(to_address: str, amount: str) -> InlineKeyboardMarkup:
        """Payment confirmation keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Confirm",
                    callback_data=f"pay_confirm:{to_address}:{amount}",
                ),
                InlineKeyboardButton("❌ Cancel", callback_data="pay_cancel"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def payment_required(
        agent_name: str,
        price: str,
        task_id: str,
    ) -> InlineKeyboardMarkup:
        """x402 payment required keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(
                    f"💰 Pay {price}",
                    callback_data=f"x402_pay:{task_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "❌ Cancel",
                    callback_data=f"x402_cancel:{task_id}",
                ),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def agent_session(agent_id: str) -> InlineKeyboardMarkup:
        """Agent session keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(
                    "🔄 New Session",
                    callback_data=f"agent_new:{agent_id}",
                ),
                InlineKeyboardButton(
                    "❌ Exit",
                    callback_data="agent_exit",
                ),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def back_button(callback_data: str = "menu") -> InlineKeyboardMarkup:
        """Simple back button."""
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton("◀️ Back", callback_data=callback_data)]]
        )
