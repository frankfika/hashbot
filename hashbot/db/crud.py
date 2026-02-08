"""Async CRUD operations for HashBot database."""

from sqlalchemy import select

from hashbot.db.engine import get_db
from hashbot.db.models import Agent, AgentSkill, Payment, User, Wallet

# ── Users ──────────────────────────────────────────────────────────────

async def get_or_create_user(
    telegram_id: int,
    username: str | None = None,
    display_name: str = "",
) -> User:
    """Get existing user or create a new one."""
    async with get_db() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=telegram_id,
                telegram_username=username,
                display_name=display_name,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


async def get_user_by_telegram_id(telegram_id: int) -> User | None:
    async with get_db() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


# ── Agents ─────────────────────────────────────────────────────────────

async def create_agent(
    owner_id: int,
    name: str,
    description: str,
    openclaw_agent_id: str = "",
    workspace_path: str = "",
) -> Agent:
    async with get_db() as session:
        agent = Agent(
            owner_id=owner_id,
            name=name,
            description=description,
            openclaw_agent_id=openclaw_agent_id,
            workspace_path=workspace_path,
        )
        session.add(agent)
        await session.commit()
        await session.refresh(agent)
        return agent


async def get_user_agents(user_id: int) -> list[Agent]:
    async with get_db() as session:
        result = await session.execute(
            select(Agent).where(Agent.owner_id == user_id)
        )
        return list(result.scalars().all())


async def get_public_agents() -> list[Agent]:
    async with get_db() as session:
        result = await session.execute(
            select(Agent).where(Agent.is_public.is_(True))
        )
        return list(result.scalars().all())


async def get_agent_by_id(agent_id: str) -> Agent | None:
    async with get_db() as session:
        result = await session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        return result.scalar_one_or_none()


async def update_agent(agent_id: str, **kwargs) -> Agent | None:
    async with get_db() as session:
        result = await session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        if agent is None:
            return None
        for key, value in kwargs.items():
            setattr(agent, key, value)
        await session.commit()
        await session.refresh(agent)
        return agent


async def delete_agent(agent_id: str) -> bool:
    async with get_db() as session:
        result = await session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        if agent is None:
            return False
        await session.delete(agent)
        await session.commit()
        return True


# ── Wallets ────────────────────────────────────────────────────────────

async def get_or_create_wallet(
    user_id: int,
    address: str,
    encrypted_key: str = "",
) -> Wallet:
    async with get_db() as session:
        result = await session.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        wallet = result.scalar_one_or_none()
        if wallet is None:
            wallet = Wallet(
                user_id=user_id,
                address=address,
                encrypted_private_key=encrypted_key,
            )
            session.add(wallet)
            await session.commit()
            await session.refresh(wallet)
        return wallet


async def get_user_wallet(user_id: int) -> Wallet | None:
    async with get_db() as session:
        result = await session.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        return result.scalar_one_or_none()


async def get_wallet_by_telegram_id(telegram_id: int) -> Wallet | None:
    async with get_db() as session:
        result = await session.execute(
            select(Wallet)
            .join(User, User.id == Wallet.user_id)
            .where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


# ── Payments ───────────────────────────────────────────────────────────

async def record_payment(
    payer_user_id: int,
    agent_id: str,
    amount: float,
    currency: str = "HKDC",
) -> Payment:
    async with get_db() as session:
        payment = Payment(
            payer_user_id=payer_user_id,
            agent_id=agent_id,
            amount=amount,
            currency=currency,
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment


async def complete_payment(payment_id: int, tx_hash: str) -> Payment | None:
    async with get_db() as session:
        result = await session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            return None
        payment.tx_hash = tx_hash
        payment.status = "completed"
        await session.commit()
        await session.refresh(payment)
        return payment


# ── Skills ─────────────────────────────────────────────────────────────

async def install_skill(
    agent_id: str,
    slug: str,
    source: str = "builtin",
) -> AgentSkill:
    async with get_db() as session:
        skill = AgentSkill(
            agent_id=agent_id,
            skill_slug=slug,
            source=source,
        )
        session.add(skill)
        await session.commit()
        await session.refresh(skill)
        return skill


async def get_agent_skills(agent_id: str) -> list[AgentSkill]:
    async with get_db() as session:
        result = await session.execute(
            select(AgentSkill).where(AgentSkill.agent_id == agent_id)
        )
        return list(result.scalars().all())


async def remove_skill(agent_id: str, slug: str) -> bool:
    async with get_db() as session:
        result = await session.execute(
            select(AgentSkill).where(
                AgentSkill.agent_id == agent_id,
                AgentSkill.skill_slug == slug,
            )
        )
        skill = result.scalar_one_or_none()
        if skill is None:
            return False
        await session.delete(skill)
        await session.commit()
        return True
