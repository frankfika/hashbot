"""Comprehensive tests for database CRUD operations and convenience functions."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from hashbot.db.models import Base, User, Agent, Wallet, Payment, AgentSkill
from hashbot.db.crud import (
    UserCRUD,
    AgentCRUD,
    WalletCRUD,
    TaskCRUD,
    AgentSkillCRUD,
    # Module-level convenience functions
    get_user_by_telegram_id,
    get_or_create_user,
    get_agent_by_id,
    get_public_agents,
    get_user_agents,
    create_agent,
    update_agent,
    delete_agent,
    get_user_wallet,
    get_wallet_by_telegram_id,
    get_or_create_wallet,
    record_payment,
    complete_payment,
    get_agent_skills,
    install_skill,
    remove_skill,
)


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def engine():
    """Create an in-memory SQLite engine for testing."""
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    """Create a fresh session for each test."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest_asyncio.fixture(autouse=True)
async def patch_get_session(engine, monkeypatch):
    """Patch _get_session in crud module so convenience functions use test DB."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(
        "hashbot.db.crud._get_session",
        lambda: factory(),
    )


# ── UserCRUD class tests ────────────────────────────────────────────


class TestUserCRUD:
    """Tests for UserCRUD class methods."""

    @pytest.mark.asyncio
    async def test_create_user(self, session: AsyncSession):
        crud = UserCRUD()
        user = await crud.create(session, telegram_id=111, username="alice", display_name="Alice")
        assert user.id is not None
        assert user.telegram_id == 111
        assert user.telegram_username == "alice"
        assert user.display_name == "Alice"

    @pytest.mark.asyncio
    async def test_create_user_default_display_name(self, session: AsyncSession):
        crud = UserCRUD()
        user = await crud.create(session, telegram_id=222, username="bob")
        assert user.display_name == "bob"  # falls back to username

    @pytest.mark.asyncio
    async def test_create_user_no_username(self, session: AsyncSession):
        crud = UserCRUD()
        user = await crud.create(session, telegram_id=333)
        assert user.display_name == "User 333"

    @pytest.mark.asyncio
    async def test_get_by_id(self, session: AsyncSession):
        crud = UserCRUD()
        user = await crud.create(session, telegram_id=444, username="charlie")
        fetched = await crud.get_by_id(session, user.id)
        assert fetched is not None
        assert fetched.telegram_id == 444

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, session: AsyncSession):
        crud = UserCRUD()
        assert await crud.get_by_id(session, 99999) is None

    @pytest.mark.asyncio
    async def test_get_by_telegram_id(self, session: AsyncSession):
        crud = UserCRUD()
        await crud.create(session, telegram_id=555, username="dave")
        fetched = await crud.get_by_telegram_id(session, 555)
        assert fetched is not None
        assert fetched.telegram_username == "dave"

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_not_found(self, session: AsyncSession):
        crud = UserCRUD()
        assert await crud.get_by_telegram_id(session, 99999) is None

    @pytest.mark.asyncio
    async def test_update_user(self, session: AsyncSession):
        crud = UserCRUD()
        user = await crud.create(session, telegram_id=666, username="eve")
        updated = await crud.update(session, user.id, display_name="Eve Updated")
        assert updated is not None
        assert updated.display_name == "Eve Updated"

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, session: AsyncSession):
        crud = UserCRUD()
        assert await crud.update(session, 99999, display_name="Ghost") is None

    @pytest.mark.asyncio
    async def test_update_user_ignores_unknown_fields(self, session: AsyncSession):
        crud = UserCRUD()
        user = await crud.create(session, telegram_id=777, username="frank")
        updated = await crud.update(session, user.id, nonexistent_field="value")
        assert updated is not None  # should not crash

    @pytest.mark.asyncio
    async def test_get_or_create_creates(self, session: AsyncSession):
        crud = UserCRUD()
        user = await crud.get_or_create(session, telegram_id=888, username="grace")
        assert user.telegram_id == 888
        assert user.telegram_username == "grace"

    @pytest.mark.asyncio
    async def test_get_or_create_gets_existing(self, session: AsyncSession):
        crud = UserCRUD()
        user1 = await crud.get_or_create(session, telegram_id=999, username="heidi")
        user2 = await crud.get_or_create(session, telegram_id=999, username="heidi_v2")
        assert user1.id == user2.id
        assert user2.telegram_username == "heidi"  # original, not updated


# ── AgentCRUD class tests ───────────────────────────────────────────


class TestAgentCRUD:
    """Tests for AgentCRUD class methods."""

    async def _make_user(self, session: AsyncSession) -> User:
        crud = UserCRUD()
        return await crud.create(session, telegram_id=10001, username="owner")

    @pytest.mark.asyncio
    async def test_create_agent(self, session: AsyncSession):
        user = await self._make_user(session)
        crud = AgentCRUD()
        agent = await crud.create(
            session, owner_id=user.id, name="Bot1",
            description="desc", price_per_call=0.5, is_public=True,
        )
        assert agent.id is not None
        assert agent.name == "Bot1"
        assert agent.owner_id == user.id
        assert agent.is_public is True

    @pytest.mark.asyncio
    async def test_get_by_id(self, session: AsyncSession):
        user = await self._make_user(session)
        crud = AgentCRUD()
        agent = await crud.create(session, owner_id=user.id, name="Bot2")
        fetched = await crud.get_by_id(session, agent.id)
        assert fetched is not None
        assert fetched.name == "Bot2"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, session: AsyncSession):
        crud = AgentCRUD()
        assert await crud.get_by_id(session, "nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_by_owner(self, session: AsyncSession):
        user = await self._make_user(session)
        crud = AgentCRUD()
        await crud.create(session, owner_id=user.id, name="Bot3")
        await crud.create(session, owner_id=user.id, name="Bot4")
        agents = await crud.get_by_owner(session, user.id)
        assert len(agents) == 2

    @pytest.mark.asyncio
    async def test_get_public_agents(self, session: AsyncSession):
        user = await self._make_user(session)
        crud = AgentCRUD()
        await crud.create(session, owner_id=user.id, name="Public", is_public=True)
        await crud.create(session, owner_id=user.id, name="Private", is_public=False)
        public = await crud.get_public_agents(session)
        assert len(public) == 1
        assert public[0].name == "Public"

    @pytest.mark.asyncio
    async def test_update_agent(self, session: AsyncSession):
        user = await self._make_user(session)
        crud = AgentCRUD()
        agent = await crud.create(session, owner_id=user.id, name="OldName")
        updated = await crud.update(session, agent.id, name="NewName")
        assert updated is not None
        assert updated.name == "NewName"

    @pytest.mark.asyncio
    async def test_update_agent_not_found(self, session: AsyncSession):
        crud = AgentCRUD()
        assert await crud.update(session, "nonexistent", name="X") is None

    @pytest.mark.asyncio
    async def test_delete_agent(self, session: AsyncSession):
        user = await self._make_user(session)
        crud = AgentCRUD()
        agent = await crud.create(session, owner_id=user.id, name="ToDelete")
        assert await crud.delete(session, agent.id) is True
        assert await crud.get_by_id(session, agent.id) is None

    @pytest.mark.asyncio
    async def test_delete_agent_not_found(self, session: AsyncSession):
        crud = AgentCRUD()
        assert await crud.delete(session, "nonexistent") is False


# ── WalletCRUD class tests ──────────────────────────────────────────


class TestWalletCRUD:
    """Tests for WalletCRUD class methods."""

    @pytest.mark.asyncio
    async def test_create_and_get_wallet(self, session: AsyncSession):
        user_crud = UserCRUD()
        user = await user_crud.create(session, telegram_id=20001, username="wallet_user")

        crud = WalletCRUD()
        wallet = await crud.create(session, user.id, "0x" + "a" * 40, "encrypted_key_data")
        assert wallet.address == "0x" + "a" * 40

        fetched = await crud.get_by_user_id(session, user.id)
        assert fetched is not None
        assert fetched.address == wallet.address

    @pytest.mark.asyncio
    async def test_get_wallet_not_found(self, session: AsyncSession):
        crud = WalletCRUD()
        assert await crud.get_by_user_id(session, 99999) is None


# ── TaskCRUD (Payment) class tests ──────────────────────────────────


class TestTaskCRUD:
    """Tests for TaskCRUD (payment tracking) class methods."""

    async def _setup(self, session: AsyncSession):
        user_crud = UserCRUD()
        agent_crud = AgentCRUD()
        user = await user_crud.create(session, telegram_id=30001, username="payer")
        agent = await agent_crud.create(session, owner_id=user.id, name="PaidAgent")
        return user, agent

    @pytest.mark.asyncio
    async def test_create_payment(self, session: AsyncSession):
        user, agent = await self._setup(session)
        crud = TaskCRUD()
        payment = await crud.create_payment(session, user.id, agent.id, 1.5, "HKDC")
        assert payment.id is not None
        assert payment.status == "pending"
        assert float(payment.amount) == 1.5

    @pytest.mark.asyncio
    async def test_update_payment(self, session: AsyncSession):
        user, agent = await self._setup(session)
        crud = TaskCRUD()
        payment = await crud.create_payment(session, user.id, agent.id, 2.0)
        updated = await crud.update_payment(session, payment.id, tx_hash="0xabc", status="completed")
        assert updated is not None
        assert updated.tx_hash == "0xabc"
        assert updated.status == "completed"

    @pytest.mark.asyncio
    async def test_update_payment_not_found(self, session: AsyncSession):
        crud = TaskCRUD()
        assert await crud.update_payment(session, 99999, tx_hash="0x") is None

    @pytest.mark.asyncio
    async def test_get_user_payments(self, session: AsyncSession):
        user, agent = await self._setup(session)
        crud = TaskCRUD()
        await crud.create_payment(session, user.id, agent.id, 1.0)
        await crud.create_payment(session, user.id, agent.id, 2.0)
        payments = await crud.get_user_payments(session, user.id)
        assert len(payments) == 2


# ── AgentSkillCRUD class tests ──────────────────────────────────────


class TestAgentSkillCRUD:
    """Tests for AgentSkillCRUD class methods."""

    async def _setup(self, session: AsyncSession):
        user_crud = UserCRUD()
        agent_crud = AgentCRUD()
        user = await user_crud.create(session, telegram_id=40001, username="skill_owner")
        agent = await agent_crud.create(session, owner_id=user.id, name="SkillAgent")
        return agent

    @pytest.mark.asyncio
    async def test_add_and_get_skills(self, session: AsyncSession):
        agent = await self._setup(session)
        crud = AgentSkillCRUD()
        skill = await crud.add_skill(session, agent.id, "translator", "builtin")
        assert skill.skill_slug == "translator"
        assert skill.is_enabled is True

        skills = await crud.get_agent_skills(session, agent.id)
        assert len(skills) == 1

    @pytest.mark.asyncio
    async def test_remove_skill(self, session: AsyncSession):
        agent = await self._setup(session)
        crud = AgentSkillCRUD()
        await crud.add_skill(session, agent.id, "code_review")
        assert await crud.remove_skill(session, agent.id, "code_review") is True
        assert await crud.remove_skill(session, agent.id, "code_review") is False  # already gone

    @pytest.mark.asyncio
    async def test_get_skills_empty(self, session: AsyncSession):
        agent = await self._setup(session)
        crud = AgentSkillCRUD()
        skills = await crud.get_agent_skills(session, agent.id)
        assert skills == []


# ══════════════════════════════════════════════════════════════════════
# Module-level convenience function tests
# ══════════════════════════════════════════════════════════════════════


class TestConvenienceUserFunctions:
    """Tests for module-level user convenience functions."""

    @pytest.mark.asyncio
    async def test_get_or_create_user(self):
        user = await get_or_create_user(telegram_id=50001, username="conv_user")
        assert user.telegram_id == 50001
        assert user.telegram_username == "conv_user"

    @pytest.mark.asyncio
    async def test_get_or_create_user_idempotent(self):
        u1 = await get_or_create_user(telegram_id=50002, username="idem")
        u2 = await get_or_create_user(telegram_id=50002, username="idem_v2")
        assert u1.id == u2.id

    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id(self):
        await get_or_create_user(telegram_id=50003, username="lookup")
        user = await get_user_by_telegram_id(50003)
        assert user is not None
        assert user.telegram_username == "lookup"

    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id_not_found(self):
        assert await get_user_by_telegram_id(99999) is None


class TestConvenienceAgentFunctions:
    """Tests for module-level agent convenience functions."""

    @pytest.mark.asyncio
    async def test_create_and_get_agent(self):
        user = await get_or_create_user(telegram_id=60001, username="agent_owner")
        agent = await create_agent(
            owner_id=user.id, name="ConvAgent",
            description="test", price_per_call=0.1, is_public=True,
        )
        assert agent.name == "ConvAgent"

        fetched = await get_agent_by_id(agent.id)
        assert fetched is not None
        assert fetched.name == "ConvAgent"

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self):
        assert await get_agent_by_id("nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_public_agents(self):
        user = await get_or_create_user(telegram_id=60002, username="pub_owner")
        await create_agent(owner_id=user.id, name="Pub", is_public=True)
        await create_agent(owner_id=user.id, name="Priv", is_public=False)
        public = await get_public_agents()
        names = [a.name for a in public]
        assert "Pub" in names

    @pytest.mark.asyncio
    async def test_get_user_agents(self):
        user = await get_or_create_user(telegram_id=60003, username="my_agents")
        await create_agent(owner_id=user.id, name="A1")
        await create_agent(owner_id=user.id, name="A2")
        agents = await get_user_agents(user.id)
        assert len(agents) == 2

    @pytest.mark.asyncio
    async def test_update_agent(self):
        user = await get_or_create_user(telegram_id=60004, username="updater")
        agent = await create_agent(owner_id=user.id, name="Before")
        updated = await update_agent(agent.id, name="After")
        assert updated is not None
        assert updated.name == "After"

    @pytest.mark.asyncio
    async def test_update_agent_not_found(self):
        assert await update_agent("nonexistent", name="X") is None

    @pytest.mark.asyncio
    async def test_delete_agent(self):
        user = await get_or_create_user(telegram_id=60005, username="deleter")
        agent = await create_agent(owner_id=user.id, name="Doomed")
        assert await delete_agent(agent.id) is True
        assert await get_agent_by_id(agent.id) is None

    @pytest.mark.asyncio
    async def test_delete_agent_not_found(self):
        assert await delete_agent("nonexistent") is False


class TestConvenienceWalletFunctions:
    """Tests for module-level wallet convenience functions."""

    @pytest.mark.asyncio
    async def test_get_or_create_wallet(self):
        user = await get_or_create_user(telegram_id=70001, username="wallet_guy")
        wallet = await get_or_create_wallet(user.id, "0x" + "b" * 40, "enc_key")
        assert wallet.address == "0x" + "b" * 40

    @pytest.mark.asyncio
    async def test_get_or_create_wallet_idempotent(self):
        user = await get_or_create_user(telegram_id=70002, username="wallet_idem")
        w1 = await get_or_create_wallet(user.id, "0x" + "c" * 40, "key1")
        w2 = await get_or_create_wallet(user.id, "0x" + "d" * 40, "key2")
        assert w1.id == w2.id  # returns existing, doesn't create new

    @pytest.mark.asyncio
    async def test_get_user_wallet(self):
        user = await get_or_create_user(telegram_id=70003, username="wallet_get")
        await get_or_create_wallet(user.id, "0x" + "e" * 40, "key3")
        wallet = await get_user_wallet(user.id)
        assert wallet is not None
        assert wallet.address == "0x" + "e" * 40

    @pytest.mark.asyncio
    async def test_get_user_wallet_not_found(self):
        assert await get_user_wallet(99999) is None

    @pytest.mark.asyncio
    async def test_get_wallet_by_telegram_id(self):
        user = await get_or_create_user(telegram_id=70004, username="tg_wallet")
        await get_or_create_wallet(user.id, "0x" + "f" * 40, "key4")
        wallet = await get_wallet_by_telegram_id(70004)
        assert wallet is not None
        assert wallet.address == "0x" + "f" * 40

    @pytest.mark.asyncio
    async def test_get_wallet_by_telegram_id_no_user(self):
        assert await get_wallet_by_telegram_id(99998) is None

    @pytest.mark.asyncio
    async def test_get_wallet_by_telegram_id_no_wallet(self):
        await get_or_create_user(telegram_id=70005, username="no_wallet")
        assert await get_wallet_by_telegram_id(70005) is None


class TestConveniencePaymentFunctions:
    """Tests for module-level payment convenience functions."""

    @pytest.mark.asyncio
    async def test_record_and_complete_payment(self):
        user = await get_or_create_user(telegram_id=80001, username="payer")
        agent = await create_agent(owner_id=user.id, name="PayAgent")
        payment = await record_payment(user.id, agent.id, 3.14, "HKDC")
        assert payment.status == "pending"
        assert float(payment.amount) == pytest.approx(3.14)

        completed = await complete_payment(payment.id, "0xdeadbeef")
        assert completed is not None
        assert completed.status == "completed"
        assert completed.tx_hash == "0xdeadbeef"

    @pytest.mark.asyncio
    async def test_complete_payment_not_found(self):
        assert await complete_payment(99999, "0x") is None


class TestConvenienceSkillFunctions:
    """Tests for module-level skill convenience functions."""

    @pytest.mark.asyncio
    async def test_install_and_get_skills(self):
        user = await get_or_create_user(telegram_id=90001, username="skill_user")
        agent = await create_agent(owner_id=user.id, name="SkillBot")
        skill = await install_skill(agent.id, "translator", "builtin")
        assert skill.skill_slug == "translator"

        skills = await get_agent_skills(agent.id)
        assert len(skills) == 1
        assert skills[0].skill_slug == "translator"

    @pytest.mark.asyncio
    async def test_remove_skill(self):
        user = await get_or_create_user(telegram_id=90002, username="skill_rm")
        agent = await create_agent(owner_id=user.id, name="SkillBot2")
        await install_skill(agent.id, "code_review")
        assert await remove_skill(agent.id, "code_review") is True
        assert await remove_skill(agent.id, "code_review") is False

    @pytest.mark.asyncio
    async def test_get_skills_empty(self):
        user = await get_or_create_user(telegram_id=90003, username="no_skills")
        agent = await create_agent(owner_id=user.id, name="EmptyBot")
        skills = await get_agent_skills(agent.id)
        assert skills == []
