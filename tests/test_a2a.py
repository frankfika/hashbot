"""Tests for A2A Protocol implementation."""

from hashbot.a2a.messages import AgentCard, Task, TaskState


class TestTask:
    """Test Task class."""

    def test_create_task(self):
        """Test task creation."""
        task = Task()
        assert task.id is not None
        assert task.session_id is not None
        assert task.status == TaskState.SUBMITTED
        assert len(task.history) == 0

    def test_add_message(self):
        """Test adding message to task."""
        task = Task()
        task.add_message("user", "Hello")

        assert len(task.history) == 1
        assert task.history[0].role == "user"
        assert task.history[0].parts[0].text == "Hello"

    def test_add_data(self):
        """Test adding data to task."""
        task = Task()
        task.add_data("agent", {"result": "success"})

        assert len(task.history) == 1
        assert task.history[0].role == "agent"
        assert task.history[0].parts[0].data == {"result": "success"}


class TestAgentCard:
    """Test AgentCard class."""

    def test_create_agent_card(self):
        """Test agent card creation."""
        card = AgentCard(
            name="TestAgent",
            description="A test agent",
            url="http://localhost:8000",
        )

        assert card.name == "TestAgent"
        assert card.description == "A test agent"
        assert card.protocol_version == "0.1"
        assert card.x402_enabled is False

    def test_agent_card_with_x402(self):
        """Test agent card with x402 enabled."""
        card = AgentCard(
            name="PaidAgent",
            description="A paid agent",
            url="http://localhost:8000",
            x402_enabled=True,
        )

        assert card.x402_enabled is True
