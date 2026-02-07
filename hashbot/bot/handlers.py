"""Telegram Bot message handlers."""

from decimal import Decimal
from typing import Any

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from hashbot.bot.keyboards import InlineKeyboards
from hashbot.config import get_settings


class HashBotHandler:
    """Main Telegram bot handler."""

    def __init__(
        self,
        agent_registry: Any | None = None,
        wallet_service: Any | None = None,
    ):
        self.agent_registry = agent_registry
        self.wallet_service = wallet_service
        self.settings = get_settings()

    def setup(self, application: Application) -> None:
        """Register all handlers with the application."""
        # Command handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("agents", self.agents_command))
        application.add_handler(CommandHandler("wallet", self.wallet_command))
        application.add_handler(CommandHandler("balance", self.balance_command))
        application.add_handler(CommandHandler("pay", self.pay_command))

        # Callback query handler for inline buttons
        application.add_handler(
            CallbackQueryHandler(self.button_callback)
        )

        # Message handler for agent interactions
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler)
        )

    async def start_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /start command."""
        welcome_text = """
🤖 **Welcome to HashBot!**

Bot 用 Bot，自动付费 — Agent Economy on HashKey Chain

**What I can do:**
• `/agents` - Browse available AI agents
• `/wallet` - Manage your wallet
• `/balance` - Check your HKDC balance
• `/pay` - Make a payment

**How it works:**
1. Choose an Agent to help you
2. Agent requests payment (x402)
3. Pay with HKDC stablecoin
4. Get your result!

Start by exploring `/agents` 👇
        """
        await update.message.reply_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboards.main_menu(),
        )

    async def help_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /help command."""
        help_text = """
📖 **HashBot Help**

**Commands:**
• `/start` - Start the bot
• `/agents` - List available agents
• `/wallet` - Wallet management
• `/balance` - Check HKDC balance
• `/pay <address> <amount>` - Send HKDC

**About x402 Payments:**
When you use a paid agent, it will request payment automatically.
You'll see the price before confirming.

**About A2A Protocol:**
HashBot uses Google's A2A protocol for agent communication.
Your agents can be called by other agents too!

**HashKey Chain:**
All payments are settled on HashKey Chain with HKDC stablecoin.
Low fees, fast confirmation, fully compliant.

Need more help? Contact @hashbot_support
        """
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def agents_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /agents command."""
        agents_text = """
🤖 **Available Agents**

Choose an agent to interact with:
        """

        # Get agents from registry if available
        agents = []
        if self.agent_registry:
            agents = self.agent_registry.list_agents()

        if not agents:
            # Default demo agents
            agents = [
                {
                    "id": "crypto_analyst",
                    "name": "Crypto Analyst",
                    "description": "Token analysis and market insights",
                    "price": "0.1 HKDC",
                },
                {
                    "id": "translator",
                    "name": "AI Translator",
                    "description": "Multi-language translation",
                    "price": "0.05 HKDC",
                },
                {
                    "id": "code_reviewer",
                    "name": "Code Reviewer",
                    "description": "Smart contract audit",
                    "price": "0.5 HKDC",
                },
            ]

        for agent in agents:
            agents_text += f"""
**{agent['name']}** (`{agent['id']}`)
{agent['description']}
💰 {agent['price']} per call
"""

        await update.message.reply_text(
            agents_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboards.agent_list(agents),
        )

    async def wallet_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /wallet command."""
        user_id = update.effective_user.id

        # Get or create wallet for user
        wallet_info = await self._get_user_wallet(user_id)

        if wallet_info:
            wallet_text = f"""
💼 **Your Wallet**

**Address:** `{wallet_info['address']}`
**Network:** HashKey Chain {'Mainnet' if self.settings.hashkey_chain_id == 133 else 'Testnet'}

Use `/balance` to check your HKDC balance.
            """
        else:
            wallet_text = """
💼 **Wallet Setup**

You don't have a wallet yet.
Click below to create one or import existing.
            """

        await update.message.reply_text(
            wallet_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboards.wallet_menu(has_wallet=bool(wallet_info)),
        )

    async def balance_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /balance command."""
        user_id = update.effective_user.id
        wallet_info = await self._get_user_wallet(user_id)

        if not wallet_info:
            await update.message.reply_text(
                "❌ No wallet found. Use /wallet to create one."
            )
            return

        # Get balance (placeholder)
        hkdc_balance = Decimal("0.00")
        native_balance = Decimal("0.00")

        if self.wallet_service:
            hkdc_balance = await self.wallet_service.get_hkdc_balance(
                wallet_info["address"]
            )
            native_balance = await self.wallet_service.get_native_balance(
                wallet_info["address"]
            )

        balance_text = f"""
💰 **Your Balance**

**HKDC:** {hkdc_balance:.2f}
**HSK:** {native_balance:.6f}

Address: `{wallet_info['address']}`
        """

        await update.message.reply_text(balance_text, parse_mode="Markdown")

    async def pay_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /pay command."""
        args = context.args

        if not args or len(args) < 2:
            await update.message.reply_text(
                "Usage: `/pay <address> <amount>`\n"
                "Example: `/pay 0x123...abc 10`",
                parse_mode="Markdown",
            )
            return

        to_address = args[0]
        try:
            amount = Decimal(args[1])
        except ValueError:
            await update.message.reply_text("❌ Invalid amount")
            return

        # Confirm payment
        await update.message.reply_text(
            f"**Confirm Payment**\n\n"
            f"To: `{to_address}`\n"
            f"Amount: {amount} HKDC\n\n"
            f"Click confirm to proceed.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboards.confirm_payment(to_address, str(amount)),
        )

    async def message_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle regular text messages."""
        text = update.message.text
        user_id = update.effective_user.id

        # Check if user is in an agent session
        session = context.user_data.get("agent_session")

        if session:
            # Forward to agent
            await self._handle_agent_message(update, context, session, text)
        else:
            # Default response
            await update.message.reply_text(
                "Use /agents to start chatting with an AI agent, "
                "or /help for more options."
            )

    async def button_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle inline button callbacks."""
        query = update.callback_query
        await query.answer()

        data = query.data

        if data.startswith("agent:"):
            agent_id = data.split(":")[1]
            await self._start_agent_session(query, context, agent_id)

        elif data.startswith("pay_confirm:"):
            parts = data.split(":")
            to_address = parts[1]
            amount = parts[2]
            await self._execute_payment(query, context, to_address, amount)

        elif data == "pay_cancel":
            await query.edit_message_text("❌ Payment cancelled.")

        elif data == "wallet_create":
            await self._create_wallet(query, context)

        elif data == "wallet_import":
            await query.edit_message_text(
                "Send your private key to import wallet.\n"
                "⚠️ Make sure you're in a private chat!"
            )
            context.user_data["awaiting_private_key"] = True

        elif data == "menu":
            await query.edit_message_text(
                "Choose an option:",
                reply_markup=InlineKeyboards.main_menu(),
            )

    async def _get_user_wallet(self, user_id: int) -> dict[str, Any] | None:
        """Get wallet for user."""
        # Placeholder - implement with database
        return None

    async def _handle_agent_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        session: dict[str, Any],
        text: str,
    ) -> None:
        """Handle message in agent session."""
        await update.message.reply_text(
            f"[{session['agent_name']}] Processing your request..."
        )
        # TODO: Implement A2A protocol call

    async def _start_agent_session(
        self,
        query: Any,
        context: ContextTypes.DEFAULT_TYPE,
        agent_id: str,
    ) -> None:
        """Start a new agent session."""
        context.user_data["agent_session"] = {
            "agent_id": agent_id,
            "agent_name": agent_id.replace("_", " ").title(),
        }

        await query.edit_message_text(
            f"✅ Connected to **{agent_id.replace('_', ' ').title()}**\n\n"
            "Send your message to start.",
            parse_mode="Markdown",
        )

    async def _execute_payment(
        self,
        query: Any,
        context: ContextTypes.DEFAULT_TYPE,
        to_address: str,
        amount: str,
    ) -> None:
        """Execute a payment."""
        await query.edit_message_text(
            f"⏳ Processing payment of {amount} HKDC..."
        )

        # TODO: Implement actual payment via HashKey Chain
        await query.edit_message_text(
            f"✅ Payment successful!\n\n"
            f"Amount: {amount} HKDC\n"
            f"To: `{to_address}`\n"
            f"TX: `0x...`",
            parse_mode="Markdown",
        )

    async def _create_wallet(
        self,
        query: Any,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Create a new wallet for user."""
        # TODO: Implement secure wallet creation
        await query.edit_message_text(
            "✅ Wallet created!\n\n"
            "Address: `0x...`\n\n"
            "⚠️ Save your recovery phrase securely!",
            parse_mode="Markdown",
        )
