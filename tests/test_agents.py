"""Tests for Agent framework."""

import pytest
from decimal import Decimal

from hashbot.agents.base import BaseAgent, agent_card
from hashbot.agents.registry import AgentRegistry
from hashbot.a2a.messages import Task


@agent_card(
    name="TestAgent",
    description="A test agent",
    price_per_call=0.1,
    currency="HKDC",
)
class MockAgent(BaseAgent):
    """Mock agent for testing."""

    async def process(self, task: Task):
        return self._create_success_response(task, text="Test response")


class TestBaseAgent:
    """Test BaseAgent class."""

    def test_agent_metadata(self):
        """Test agent metadata from decorator."""
        agent = MockAgent()

        assert agent.name == "TestAgent"
        assert agent.description == "A test agent"
        assert agent.price == Decimal("0.1")
        assert agent.currency == "HKDC"
        assert agent.requires_payment is True

    def test_get_agent_card(self):
        """Test getting agent card."""
        agent = MockAgent(base_url="http://localhost:8000")
        card = agent.get_agent_card()

        assert card.name == "TestAgent"
        assert card.x402_enabled is True

    def test_get_payment_config(self):
        """Test getting payment config."""
        agent = MockAgent()
        config = agent.get_payment_config()

        assert config is not None
        assert config.price == Decimal("0.1")
        assert config.currency == "HKDC"


class TestAgentRegistry:
    """Test AgentRegistry class."""

    def test_register_agent(self):
        """Test registering an agent."""
        registry = AgentRegistry()
        registry.register("mock", MockAgent)

        agents = registry.list_agents()
        assert len(agents) == 1
        assert agents[0]["id"] == "mock"
        assert agents[0]["name"] == "TestAgent"

    def test_get_agent_class(self):
        """Test getting agent class."""
        registry = AgentRegistry()
        registry.register("mock", MockAgent)

        agent_class = registry.get_agent_class("mock")
        assert agent_class is MockAgent

    @pytest.mark.asyncio
    async def test_get_agent_instance(self):
        """Test getting agent instance."""
        registry = AgentRegistry()
        registry.register("mock", MockAgent)

        agent = await registry.get_agent("mock")
        assert isinstance(agent, MockAgent)

    @pytest.mark.asyncio
    async def test_process_task(self):
        """Test processing task through registry."""
        registry = AgentRegistry()
        registry.register("mock", MockAgent)

        task = Task()
        task.add_message("user", "Hello")
        task.metadata["x402.payment.status"] = "payment-completed"

        result = await registry.process_task("mock", task)

        assert result["status"]["state"] == "completed"
