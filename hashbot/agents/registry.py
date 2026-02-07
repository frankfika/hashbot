"""Agent registry for managing available agents."""

from typing import Any, Type

from hashbot.agents.base import BaseAgent
from hashbot.a2a.messages import AgentCard, Task


class AgentRegistry:
    """Registry for managing and discovering agents."""

    def __init__(self):
        self._agents: dict[str, Type[BaseAgent]] = {}
        self._instances: dict[str, BaseAgent] = {}

    def register(self, agent_id: str, agent_class: Type[BaseAgent]) -> None:
        """Register an agent class."""
        self._agents[agent_id] = agent_class

    def unregister(self, agent_id: str) -> None:
        """Unregister an agent."""
        if agent_id in self._agents:
            del self._agents[agent_id]
        if agent_id in self._instances:
            del self._instances[agent_id]

    def get_agent_class(self, agent_id: str) -> Type[BaseAgent] | None:
        """Get agent class by ID."""
        return self._agents.get(agent_id)

    async def get_agent(self, agent_id: str, base_url: str = "") -> BaseAgent | None:
        """Get or create agent instance."""
        if agent_id not in self._agents:
            return None

        if agent_id not in self._instances:
            agent_class = self._agents[agent_id]
            agent = agent_class(base_url=base_url)
            await agent.initialize()
            self._instances[agent_id] = agent

        return self._instances[agent_id]

    def list_agents(self) -> list[dict[str, Any]]:
        """List all registered agents with their metadata."""
        agents = []

        for agent_id, agent_class in self._agents.items():
            agents.append(
                {
                    "id": agent_id,
                    "name": agent_class._agent_name,
                    "description": agent_class._agent_description,
                    "price": f"{agent_class._price_per_call} {agent_class._currency}"
                    if agent_class._price_per_call
                    else "Free",
                    "version": agent_class._version,
                }
            )

        return agents

    def get_agent_cards(self, base_url: str = "") -> list[AgentCard]:
        """Get agent cards for all registered agents."""
        cards = []

        for agent_id, agent_class in self._agents.items():
            # Create temporary instance to get card
            agent = agent_class(base_url=f"{base_url}/agents/{agent_id}")
            cards.append(agent.get_agent_card())

        return cards

    async def process_task(
        self,
        agent_id: str,
        task: Task,
        base_url: str = "",
    ) -> dict[str, Any]:
        """Process a task with the specified agent."""
        agent = await self.get_agent(agent_id, base_url)

        if not agent:
            return {
                "id": task.id,
                "sessionId": task.session_id,
                "status": {
                    "state": "failed",
                    "message": {
                        "role": "agent",
                        "parts": [{"type": "text", "text": f"Agent not found: {agent_id}"}],
                    },
                },
            }

        return await agent.handle_task(task)

    async def shutdown(self) -> None:
        """Shutdown all agent instances."""
        for agent in self._instances.values():
            await agent.shutdown()
        self._instances.clear()


# Global registry instance
_registry: AgentRegistry | None = None


def get_registry() -> AgentRegistry:
    """Get global agent registry."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def register_agent(agent_id: str):
    """Decorator to register an agent class."""

    def decorator(cls: Type[BaseAgent]) -> Type[BaseAgent]:
        get_registry().register(agent_id, cls)
        return cls

    return decorator
