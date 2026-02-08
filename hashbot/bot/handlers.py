"""Telegram Bot message handlers."""

import re
from decimal import Decimal
from typing import Any

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from hashbot.bot.keyboards import InlineKeyboards
from hashbot.config import get_settings
from hashbot.db.crud import UserCRUD, AgentCRUD, TaskCRUD
from hashbot.db.database import get_db
from hashbot.services.wallet_service import WalletService
from hashbot.services.payment_service import PaymentService
from hashbot.openclaw.client import OpenClawClient
from hashbot.openclaw.manager import OpenClawManager
from hashbot.openclaw.skills import list_skills, get_skill


class HashBotHandler:
    """Main Telegram bot handler."""

    def __init__(
        self,
        agent_registry: Any | None = None,
        wallet_service: WalletService | None = None,
        openclaw_client: OpenClawClient | None = None,
    ):
        self.agent_registry = agent_registry
        self.wallet_service = wallet_service or WalletService()
        self.openclaw_client = openclaw_client or OpenClawClient()
        self.openclaw_manager = OpenClawManager(self.openclaw_client)
        self.payment_service = PaymentService(self.wallet_service)
        self.settings = get_settings()
        self.user_crud = UserCRUD()
        self.agent_crud = AgentCRUD()
        self.task_crud = TaskCRUD()

    def setup(self, application: Application) -> None:
        """Register all handlers with the application."""
        # Command handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("agents", self.agents_command))
        application.add_handler(CommandHandler("myagent", self.myagent_command))
        application.add_handler(CommandHandler("explore", self.explore_command))
        application.add_handler(CommandHandler("skills", self.skills_command))
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
        welcome_text = (
            "\U0001f916 **Welcome to HashBot!**\n"
            "\n"
            "Bot \u7528 Bot\uff0c\u81ea\u52a8\u4ed8\u8d39 \u2014 Agent Economy on HashKey Chain\n"
            "\n"
            "**What I can do:**\n"
            "\u2022 `/agents` - Browse available AI agents\n"
            "\u2022 `/wallet` - Manage your wallet\n"
            "\u2022 `/balance` - Check your HKDC balance\n"
            "\u2022 `/pay` - Make a payment\n"
            "\n"
            "**How it works:**\n"
            "1. Choose an Agent to help you\n"
            "2. Agent requests payment (x402)\n"
            "3. Pay with HKDC stablecoin\n"
            "4. Get your result!\n"
            "\n"
            "Start by exploring `/agents` \U0001f447"
        )
        await update.message.reply_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboards.main_menu(),
        )

    async def help_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /help command."""
        help_text = (
            "\U0001f4d6 **HashBot Help**\n"
            "\n"
            "**Commands:**\n"
            "\u2022 `/start` - Start the bot\n"
            "\u2022 `/agents` - List available agents\n"
            "\u2022 `/wallet` - Wallet management\n"
            "\u2022 `/balance` - Check HKDC balance\n"
            "\u2022 `/pay <address> <amount>` - Send HKDC\n"
            "\n"
            "**About x402 Payments:**\n"
            "When you use a paid agent, it will request payment automatically.\n"
            "You'll see the price before confirming.\n"
            "\n"
            "**About A2A Protocol:**\n"
            "HashBot uses Google's A2A protocol for agent communication.\n"
            "Your agents can be called by other agents too!\n"
            "\n"
            "**HashKey Chain:**\n"
            "All payments are settled on HashKey Chain with HKDC stablecoin.\n"
            "Low fees, fast confirmation, fully compliant.\n"
            "\n"
            "Need more help? Contact @hashbot_support"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def myagent_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /myagent command - create or manage user's own agent."""
        user_id = update.effective_user.id

        async for db in get_db():
            # Check if user has an agent
            agents = await self.agent_crud.get_by_owner(db, user_id)

            if agents:
                agent = agents[0]
                agent_text = (
                    f"\U0001f916 **Your Agent: {agent.name}**\n\n"
                    f"**ID:** `{agent.agent_id}`\n"
                    f"**Description:** {agent.description}\n"
                    f"**Price:** {agent.price_per_call} HKDC per call\n\n"
                    "Use /skills to manage agent skills."
                )
            else:
                agent_text = (
                    "\U0001f916 **Create Your Agent**\n\n"
                    "You don't have an agent yet.\n"
                    "Click below to create one!"
                )

        await update.message.reply_text(agent_text, parse_mode="Markdown")

    async def explore_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /explore command - explore agent marketplace."""
        explore_text = (
            "\U0001f50d **Explore Agent Marketplace**\n\n"
            "Browse agents by category:\n\n"
            "\U0001f4b9 **DeFi & Trading**\n"
            "- Token swap agents\n"
            "- Price analysis\n"
            "- Portfolio management\n\n"
            "\U0001f4dd **Content & Creative**\n"
            "- Translation\n"
            "- Writing assistance\n"
            "- Image generation\n\n"
            "\U0001f4bb **Development**\n"
            "- Code review\n"
            "- Smart contract audit\n"
            "- Bug detection\n\n"
            "Use /agents to see all available agents."
        )
        await update.message.reply_text(explore_text, parse_mode="Markdown")

    async def skills_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /skills command - manage agent skills."""
        user_id = update.effective_user.id

        async for db in get_db():
            agents = await self.agent_crud.get_by_owner(db, user_id)

            if not agents:
                await update.message.reply_text(
                    "\u274c You don't have an agent yet. Use /myagent to create one."
                )
                return

            # List available skills
            available_skills = list_skills()
            skills_text = (
                "\U0001f6e0 **Available Skills**\n\n"
                "Install skills to enhance your agent:\n\n"
            )

            for skill in available_skills:
                skills_text += (
                    f"**{skill['name']}** (`{skill['slug']}`)\n"
                    f"{skill['description']}\n\n"
                )

            skills_text += "Reply with skill slug to install (e.g., `hsk-crypto-price`)"

        await update.message.reply_text(skills_text, parse_mode="Markdown")

    async def agents_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /agents command."""
        agents_text = "\U0001f916 **Available Agents**\n\nChoose an agent to interact with:\n"

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
            agents_text += (
                f"\n**{agent['name']}** (`{agent['id']}`)\n"
                f"{agent['description']}\n"
                f"\U0001f4b0 {agent['price']} per call\n"
            )

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
            network = "Mainnet" if self.settings.hashkey_chain_id == 133 else "Testnet"
            wallet_text = (
                "\U0001f4bc **Your Wallet**\n"
                "\n"
                f"**Address:** `{wallet_info['address']}`\n"
                f"**Network:** HashKey Chain {network}\n"
                "\n"
                "Use `/balance` to check your HKDC balance."
            )
        else:
            wallet_text = (
                "\U0001f4bc **Wallet Setup**\n"
                "\n"
                "You don't have a wallet yet.\n"
                "Click below to create one or import existing."
            )

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
                "\u274c No wallet found. Use /wallet to create one."
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

        balance_text = (
            "\U0001f4b0 **Your Balance**\n"
            "\n"
            f"**HKDC:** {hkdc_balance:.2f}\n"
            f"**HSK:** {native_balance:.6f}\n"
            "\n"
            f"Address: `{wallet_info['address']}`"
        )

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

        # Validate Ethereum address format
        if not re.fullmatch(r"0x[0-9a-fA-F]{40}", to_address):
            await update.message.reply_text(
                "\u274c Invalid address. Must be a valid Ethereum address "
                "(0x followed by 40 hex characters)."
            )
            return

        try:
            amount = Decimal(args[1])
        except Exception:
            await update.message.reply_text("\u274c Invalid amount")
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

        elif data.startswith("agent_new:"):
            agent_id = data.split(":")[1]
            await self._start_agent_session(query, context, agent_id)

        elif data == "agent_exit":
            context.user_data.pop("agent_session", None)
            await query.edit_message_text(
                "Session ended. Use /agents to start a new one.",
                reply_markup=InlineKeyboards.main_menu(),
            )

        elif data.startswith("menu:"):
            section = data.split(":")[1]
            await self._handle_menu_callback(query, context, section)

        elif data.startswith("pay_confirm:"):
            parts = data.split(":")
            to_address = parts[1]
            amount = parts[2]
            await self._execute_payment(query, context, to_address, amount)

        elif data == "pay_cancel":
            await query.edit_message_text("\u274c Payment cancelled.")

        elif data.startswith("x402_pay:"):
            task_id = data.split(":")[1]
            await query.edit_message_text(
                f"\u23f3 Processing x402 payment for task `{task_id}`...",
                parse_mode="Markdown",
            )

        elif data.startswith("x402_cancel:"):
            task_id = data.split(":")[1]
            await query.edit_message_text(
                f"\u274c Payment for task `{task_id}` cancelled.",
                parse_mode="Markdown",
            )

        elif data == "wallet_create":
            await self._create_wallet(query, context)

        elif data == "wallet_import":
            await query.edit_message_text(
                "Send your private key to import wallet.\n"
                "\u26a0\ufe0f Make sure you're in a private chat!"
            )
            context.user_data["awaiting_private_key"] = True

        elif data.startswith("wallet:"):
            action = data.split(":")[1]
            await self._handle_wallet_callback(query, context, action)

        elif data == "menu":
            await query.edit_message_text(
                "Choose an option:",
                reply_markup=InlineKeyboards.main_menu(),
            )

    async def _handle_menu_callback(
        self,
        query: Any,
        context: ContextTypes.DEFAULT_TYPE,
        section: str,
    ) -> None:
        """Route main menu button presses."""
        if section == "agents":
            agents = []
            if self.agent_registry:
                agents = self.agent_registry.list_agents()

            if not agents:
                agents = [
                    {"id": "crypto_analyst", "name": "Crypto Analyst",
                     "description": "Token analysis and market insights", "price": "0.1 HKDC"},
                    {"id": "translator", "name": "AI Translator",
                     "description": "Multi-language translation", "price": "0.05 HKDC"},
                    {"id": "code_reviewer", "name": "Code Reviewer",
                     "description": "Smart contract audit", "price": "0.5 HKDC"},
                ]

            text = "\U0001f916 **Available Agents**\n\nChoose an agent to interact with:\n"
            for agent in agents:
                text += (
                    f"\n**{agent['name']}** (`{agent['id']}`)\n"
                    f"{agent['description']}\n"
                    f"\U0001f4b0 {agent['price']} per call\n"
                )
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboards.agent_list(agents),
            )

        elif section == "wallet":
            user_id = query.from_user.id
            wallet_info = await self._get_user_wallet(user_id)

            if wallet_info:
                network = "Mainnet" if self.settings.hashkey_chain_id == 133 else "Testnet"
                wallet_text = (
                    "\U0001f4bc **Your Wallet**\n"
                    "\n"
                    f"**Address:** `{wallet_info['address']}`\n"
                    f"**Network:** HashKey Chain {network}\n"
                    "\n"
                    "Use `/balance` to check your HKDC balance."
                )
            else:
                wallet_text = (
                    "\U0001f4bc **Wallet Setup**\n"
                    "\n"
                    "You don't have a wallet yet.\n"
                    "Click below to create one or import existing."
                )

            await query.edit_message_text(
                wallet_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboards.wallet_menu(has_wallet=bool(wallet_info)),
            )

        elif section == "balance":
            user_id = query.from_user.id
            wallet_info = await self._get_user_wallet(user_id)

            if not wallet_info:
                await query.edit_message_text(
                    "\u274c No wallet found. Use /wallet to create one.",
                    reply_markup=InlineKeyboards.main_menu(),
                )
                return

            hkdc_balance = Decimal("0.00")
            native_balance = Decimal("0.00")

            if self.wallet_service:
                hkdc_balance = await self.wallet_service.get_hkdc_balance(
                    wallet_info["address"]
                )
                native_balance = await self.wallet_service.get_native_balance(
                    wallet_info["address"]
                )

            balance_text = (
                "\U0001f4b0 **Your Balance**\n"
                "\n"
                f"**HKDC:** {hkdc_balance:.2f}\n"
                f"**HSK:** {native_balance:.6f}\n"
                "\n"
                f"Address: `{wallet_info['address']}`"
            )
            await query.edit_message_text(balance_text, parse_mode="Markdown")

        elif section == "help":
            help_text = (
                "\U0001f4d6 **HashBot Help**\n"
                "\n"
                "**Commands:**\n"
                "\u2022 `/start` - Start the bot\n"
                "\u2022 `/agents` - List available agents\n"
                "\u2022 `/wallet` - Wallet management\n"
                "\u2022 `/balance` - Check HKDC balance\n"
                "\u2022 `/pay <address> <amount>` - Send HKDC\n"
                "\n"
                "**About x402 Payments:**\n"
                "When you use a paid agent, it will request payment automatically.\n"
                "You'll see the price before confirming.\n"
                "\n"
                "**About A2A Protocol:**\n"
                "HashBot uses Google's A2A protocol for agent communication.\n"
                "Your agents can be called by other agents too!\n"
                "\n"
                "**HashKey Chain:**\n"
                "All payments are settled on HashKey Chain with HKDC stablecoin.\n"
                "Low fees, fast confirmation, fully compliant.\n"
                "\n"
                "Need more help? Contact @hashbot_support"
            )
            await query.edit_message_text(help_text, parse_mode="Markdown")

    async def _handle_wallet_callback(
        self,
        query: Any,
        context: ContextTypes.DEFAULT_TYPE,
        action: str,
    ) -> None:
        """Handle wallet:* callbacks."""
        user_id = query.from_user.id
        wallet_info = await self._get_user_wallet(user_id)

        if not wallet_info:
            await query.edit_message_text(
                "\u274c No wallet found. Use /wallet to create one.",
                reply_markup=InlineKeyboards.main_menu(),
            )
            return

        if action == "balance":
            hkdc_balance = Decimal("0.00")
            native_balance = Decimal("0.00")

            if self.wallet_service:
                hkdc_balance = await self.wallet_service.get_hkdc_balance(
                    wallet_info["address"]
                )
                native_balance = await self.wallet_service.get_native_balance(
                    wallet_info["address"]
                )

            await query.edit_message_text(
                f"\U0001f4b0 **HKDC:** {hkdc_balance:.2f}\n"
                f"**HSK:** {native_balance:.6f}",
                parse_mode="Markdown",
            )
        elif action == "address":
            await query.edit_message_text(
                f"\U0001f4cb **Your Address:**\n`{wallet_info['address']}`",
                parse_mode="Markdown",
            )
        elif action == "send":
            await query.edit_message_text(
                "Use `/pay <address> <amount>` to send HKDC.",
                parse_mode="Markdown",
            )
        elif action == "export":
            await query.edit_message_text(
                "\u26a0\ufe0f Private key export is not yet supported."
            )

    async def _get_user_wallet(self, user_id: int) -> dict[str, Any] | None:
        """Get wallet for user."""
        async for db in get_db():
            user = await self.user_crud.get_by_telegram_id(db, user_id)
            if user and user.wallet_address:
                return {
                    "address": user.wallet_address,
                    "encrypted_key": user.encrypted_private_key,
                }
            return None

    async def _handle_agent_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        session: dict[str, Any],
        text: str,
    ) -> None:
        """Handle message in agent session."""
        await update.message.chat.send_action(ChatAction.TYPING)

        try:
            # Get agent details
            agent_id = session["agent_id"]
            user_id = update.effective_user.id

            # Create session key for OpenClaw
            session_key = f"tg_{user_id}_{agent_id}"

            # Send message to agent via OpenClaw
            response = await self.openclaw_client.send_message(
                agent_id=agent_id,
                session_key=session_key,
                text=text,
            )

            if response:
                await update.message.reply_text(
                    response,
                    reply_markup=InlineKeyboards.agent_session(agent_id),
                )
            else:
                await update.message.reply_text(
                    f"\u274c No response from {session['agent_name']}.",
                    reply_markup=InlineKeyboards.agent_session(agent_id),
                )

        except Exception as e:
            await update.message.reply_text(
                f"\u274c Error communicating with {session['agent_name']}: {str(e)}\n"
                "Please try again or /agents to pick a different agent.",
                reply_markup=InlineKeyboards.agent_session(session["agent_id"]),
            )

    async def _start_agent_session(
        self,
        query: Any,
        context: ContextTypes.DEFAULT_TYPE,
        agent_id: str,
    ) -> None:
        """Start a new agent session."""
        agent_name = agent_id.replace("_", " ").title()
        context.user_data["agent_session"] = {
            "agent_id": agent_id,
            "agent_name": agent_name,
        }

        await query.edit_message_text(
            f"\u2705 Connected to **{agent_name}**\n\n"
            "Send your message to start.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboards.agent_session(agent_id),
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
            f"\u23f3 Processing payment of {amount} HKDC..."
        )

        try:
            user_id = query.from_user.id
            wallet_info = await self._get_user_wallet(user_id)

            if not wallet_info:
                await query.edit_message_text(
                    "\u274c No wallet found. Use /wallet to create one."
                )
                return

            # Execute payment via payment service
            tx_hash = await self.payment_service.send_hkdc(
                from_address=wallet_info["address"],
                to_address=to_address,
                amount=Decimal(amount),
                encrypted_key=wallet_info["encrypted_key"],
            )

            await query.edit_message_text(
                f"\u2705 Payment successful!\n\n"
                f"Amount: {amount} HKDC\n"
                f"To: `{to_address}`\n"
                f"TX: `{tx_hash}`",
                parse_mode="Markdown",
            )

        except Exception as e:
            await query.edit_message_text(
                f"\u274c Payment failed: {str(e)}"
            )

    async def _create_wallet(
        self,
        query: Any,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Create a new wallet for user."""
        try:
            user_id = query.from_user.id
            username = query.from_user.username or f"user_{user_id}"

            # Create wallet via wallet service
            wallet_data = await self.wallet_service.create_wallet(user_id)

            # Save to database
            async for db in get_db():
                user = await self.user_crud.get_by_telegram_id(db, user_id)
                if not user:
                    user = await self.user_crud.create(
                        db,
                        telegram_id=user_id,
                        username=username,
                        wallet_address=wallet_data["address"],
                        encrypted_private_key=wallet_data["encrypted_key"],
                    )
                else:
                    await self.user_crud.update(
                        db,
                        user.id,
                        wallet_address=wallet_data["address"],
                        encrypted_private_key=wallet_data["encrypted_key"],
                    )

            await query.edit_message_text(
                "\u2705 Wallet created!\n\n"
                f"Address: `{wallet_data['address']}`\n\n"
                "\u26a0\ufe0f Your wallet is encrypted and stored securely.\n"
                "Use /balance to check your balance.",
                parse_mode="Markdown",
            )

        except Exception as e:
            await query.edit_message_text(
                f"\u274c Failed to create wallet: {str(e)}"
            )
