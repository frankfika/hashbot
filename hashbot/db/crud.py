"""CRUD operations for HashBot database."""

from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hashbot.db.models import User, Agent, AgentSkill, Payment, Wallet


class UserCRUD:
    """CRUD operations for User model."""

    async def get_by_id(self, db: AsyncSession, user_id: int) -> User | None:
        """Get user by ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, db: AsyncSession, telegram_id: int) -> User | None:
        """Get user by Telegram ID."""
        result = await db.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        telegram_id: int,
        username: str | None = None,
        display_name: str = "",
        wallet_address: str | None = None,
        encrypted_private_key: str | None = None,
    ) -> User:
        """Create a new user."""
        user = User(
            telegram_id=telegram_id,
            telegram_username=username,
            display_name=display_name or username or f"User {telegram_id}",
            wallet_address=wallet_address,
            encrypted_private_key=encrypted_private_key,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def update(
        self,
        db: AsyncSession,
        user_id: int,
        **kwargs: Any,
    ) -> User | None:
        """Update user fields."""
        user = await self.get_by_id(db, user_id)
        if not user:
            return None

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        await db.commit()
        await db.refresh(user)
        return user

    async def get_or_create(
        self,
        db: AsyncSession,
        telegram_id: int,
        username: str | None = None,
        display_name: str = "",
    ) -> User:
        """Get existing user or create new one."""
        user = await self.get_by_telegram_id(db, telegram_id)
        if not user:
            user = await self.create(db, telegram_id, username, display_name)
        return user


class AgentCRUD:
    """CRUD operations for Agent model."""

    async def get_by_id(self, db: AsyncSession, agent_id: str) -> Agent | None:
        """Get agent by ID."""
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        return result.scalar_one_or_none()

    async def get_by_owner(self, db: AsyncSession, owner_id: int) -> list[Agent]:
        """Get all agents owned by a user."""
        result = await db.execute(select(Agent).where(Agent.owner_id == owner_id))
        return list(result.scalars().all())

    async def get_public_agents(self, db: AsyncSession) -> list[Agent]:
        """Get all public agents."""
        result = await db.execute(select(Agent).where(Agent.is_public == True))
        return list(result.scalars().all())

    async def create(
        self,
        db: AsyncSession,
        owner_id: int,
        name: str,
        description: str = "",
        openclaw_agent_id: str = "",
        workspace_path: str = "",
        price_per_call: float = 0.0,
        is_public: bool = False,
    ) -> Agent:
        """Create a new agent."""
        agent = Agent(
            owner_id=owner_id,
            name=name,
            description=description,
            openclaw_agent_id=openclaw_agent_id,
            workspace_path=workspace_path,
            price_per_call=price_per_call,
            is_public=is_public,
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        return agent

    async def update(
        self,
        db: AsyncSession,
        agent_id: str,
        **kwargs: Any,
    ) -> Agent | None:
        """Update agent fields."""
        agent = await self.get_by_id(db, agent_id)
        if not agent:
            return None

        for key, value in kwargs.items():
            if hasattr(agent, key):
                setattr(agent, key, value)

        await db.commit()
        await db.refresh(agent)
        return agent

    async def delete(self, db: AsyncSession, agent_id: str) -> bool:
        """Delete an agent."""
        agent = await self.get_by_id(db, agent_id)
        if not agent:
            return False

        await db.delete(agent)
        await db.commit()
        return True


class TaskCRUD:
    """CRUD operations for task/payment tracking."""

    async def create_payment(
        self,
        db: AsyncSession,
        payer_user_id: int,
        agent_id: str,
        amount: float,
        currency: str = "HKDC",
    ) -> Payment:
        """Create a new payment record."""
        payment = Payment(
            payer_user_id=payer_user_id,
            agent_id=agent_id,
            amount=amount,
            currency=currency,
            status="pending",
        )
        db.add(payment)
        await db.commit()
        await db.refresh(payment)
        return payment

    async def update_payment(
        self,
        db: AsyncSession,
        payment_id: int,
        tx_hash: str | None = None,
        status: str | None = None,
    ) -> Payment | None:
        """Update payment status."""
        result = await db.execute(select(Payment).where(Payment.id == payment_id))
        payment = result.scalar_one_or_none()
        if not payment:
            return None

        if tx_hash:
            payment.tx_hash = tx_hash
        if status:
            payment.status = status

        await db.commit()
        await db.refresh(payment)
        return payment

    async def get_user_payments(
        self,
        db: AsyncSession,
        user_id: int,
        limit: int = 50,
    ) -> list[Payment]:
        """Get user's payment history."""
        result = await db.execute(
            select(Payment)
            .where(Payment.payer_user_id == user_id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class WalletCRUD:
    """CRUD operations for Wallet model."""

    async def get_by_user_id(self, db: AsyncSession, user_id: int) -> Wallet | None:
        """Get wallet by user ID."""
        result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        user_id: int,
        address: str,
        encrypted_private_key: str,
    ) -> Wallet:
        """Create a new wallet."""
        wallet = Wallet(
            user_id=user_id,
            address=address,
            encrypted_private_key=encrypted_private_key,
        )
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)
        return wallet


class AgentSkillCRUD:
    """CRUD operations for AgentSkill model."""

    async def add_skill(
        self,
        db: AsyncSession,
        agent_id: str,
        skill_slug: str,
        source: str = "builtin",
    ) -> AgentSkill:
        """Add a skill to an agent."""
        skill = AgentSkill(
            agent_id=agent_id,
            skill_slug=skill_slug,
            source=source,
            is_enabled=True,
        )
        db.add(skill)
        await db.commit()
        await db.refresh(skill)
        return skill

    async def get_agent_skills(
        self,
        db: AsyncSession,
        agent_id: str,
    ) -> list[AgentSkill]:
        """Get all skills for an agent."""
        result = await db.execute(
            select(AgentSkill).where(AgentSkill.agent_id == agent_id)
        )
        return list(result.scalars().all())

    async def remove_skill(
        self,
        db: AsyncSession,
        agent_id: str,
        skill_slug: str,
    ) -> bool:
        """Remove a skill from an agent."""
        result = await db.execute(
            select(AgentSkill)
            .where(AgentSkill.agent_id == agent_id)
            .where(AgentSkill.skill_slug == skill_slug)
        )
        skill = result.scalar_one_or_none()
        if not skill:
            return False

        await db.delete(skill)
        await db.commit()
        return True


# ── Module-level convenience functions ────────────────────────────────
# These auto-manage DB sessions so callers don't need to.

_user_crud = UserCRUD()
_agent_crud = AgentCRUD()
_wallet_crud = WalletCRUD()
_task_crud = TaskCRUD()
_skill_crud = AgentSkillCRUD()


def _get_session() -> AsyncSession:
    """Get a new async session from the engine."""
    from hashbot.db.engine import get_db
    return get_db()


# ── User helpers ──────────────────────────────────────────────────────

async def get_user_by_telegram_id(telegram_id: int) -> User | None:
    async with _get_session() as db:
        return await _user_crud.get_by_telegram_id(db, telegram_id)


async def get_or_create_user(
    telegram_id: int,
    username: str | None = None,
    display_name: str = "",
) -> User:
    async with _get_session() as db:
        return await _user_crud.get_or_create(db, telegram_id, username, display_name)


# ── Agent helpers ─────────────────────────────────────────────────────

async def get_agent_by_id(agent_id: str) -> Agent | None:
    async with _get_session() as db:
        return await _agent_crud.get_by_id(db, agent_id)


async def get_public_agents() -> list[Agent]:
    async with _get_session() as db:
        return await _agent_crud.get_public_agents(db)


async def get_user_agents(owner_id: int) -> list[Agent]:
    async with _get_session() as db:
        return await _agent_crud.get_by_owner(db, owner_id)


async def create_agent(
    owner_id: int,
    name: str,
    description: str = "",
    openclaw_agent_id: str = "",
    workspace_path: str = "",
    price_per_call: float = 0.0,
    is_public: bool = False,
) -> Agent:
    async with _get_session() as db:
        return await _agent_crud.create(
            db, owner_id, name, description,
            openclaw_agent_id, workspace_path, price_per_call, is_public,
        )


async def update_agent(agent_id: str, **kwargs: Any) -> Agent | None:
    async with _get_session() as db:
        return await _agent_crud.update(db, agent_id, **kwargs)


async def delete_agent(agent_id: str) -> bool:
    async with _get_session() as db:
        return await _agent_crud.delete(db, agent_id)


# ── Wallet helpers ────────────────────────────────────────────────────

async def get_user_wallet(user_id: int) -> Wallet | None:
    async with _get_session() as db:
        return await _wallet_crud.get_by_user_id(db, user_id)


async def get_wallet_by_telegram_id(telegram_id: int) -> Wallet | None:
    async with _get_session() as db:
        user = await _user_crud.get_by_telegram_id(db, telegram_id)
        if not user:
            return None
        return await _wallet_crud.get_by_user_id(db, user.id)


async def get_or_create_wallet(
    user_id: int,
    address: str,
    encrypted_key: str,
) -> Wallet:
    async with _get_session() as db:
        existing = await _wallet_crud.get_by_user_id(db, user_id)
        if existing:
            return existing
        return await _wallet_crud.create(db, user_id, address, encrypted_key)


# ── Payment helpers ───────────────────────────────────────────────────

async def record_payment(
    payer_user_id: int,
    agent_id: str,
    amount: float,
    currency: str = "HKDC",
) -> Payment:
    async with _get_session() as db:
        return await _task_crud.create_payment(db, payer_user_id, agent_id, amount, currency)


async def complete_payment(payment_id: int, tx_hash: str) -> Payment | None:
    async with _get_session() as db:
        return await _task_crud.update_payment(db, payment_id, tx_hash=tx_hash, status="completed")


# ── Skill helpers ─────────────────────────────────────────────────────

async def get_agent_skills(agent_id: str) -> list[AgentSkill]:
    async with _get_session() as db:
        return await _skill_crud.get_agent_skills(db, agent_id)


async def install_skill(
    agent_id: str,
    skill_slug: str,
    source: str = "builtin",
) -> AgentSkill:
    async with _get_session() as db:
        return await _skill_crud.add_skill(db, agent_id, skill_slug, source)


async def remove_skill(agent_id: str, skill_slug: str) -> bool:
    async with _get_session() as db:
        return await _skill_crud.remove_skill(db, agent_id, skill_slug)
