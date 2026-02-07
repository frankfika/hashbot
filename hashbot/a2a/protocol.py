"""A2A Protocol core implementation."""

from typing import Any

import httpx

from hashbot.a2a.messages import (
    A2AMessage,
    A2AResponse,
    AgentCard,
    Task,
    TaskState,
)


class A2AProtocol:
    """A2A Protocol client for inter-agent communication."""

    def __init__(self, agent_card: AgentCard):
        self.agent_card = agent_card
        self._http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def discover_agent(self, agent_url: str) -> AgentCard | None:
        """Discover agent capabilities via Agent Card."""
        client = await self._get_client()
        try:
            # Try well-known location first
            card_url = f"{agent_url.rstrip('/')}/.well-known/agent.json"
            response = await client.get(card_url)
            if response.status_code == 200:
                return AgentCard.model_validate(response.json())
        except Exception:
            pass
        return None

    async def send_task(
        self,
        target_url: str,
        task: Task,
    ) -> A2AResponse:
        """Send a task to another agent."""
        client = await self._get_client()

        message = A2AMessage(
            method="tasks/send",
            params={
                "id": task.id,
                "sessionId": task.session_id,
                "message": {
                    "role": "user",
                    "parts": [p.model_dump() for p in task.history[-1].parts]
                    if task.history
                    else [],
                },
                "metadata": task.metadata,
            },
        )

        response = await client.post(
            target_url,
            json=message.model_dump(),
            headers={"Content-Type": "application/json"},
        )

        return A2AResponse.model_validate(response.json())

    async def get_task(self, target_url: str, task_id: str) -> A2AResponse:
        """Get task status from another agent."""
        client = await self._get_client()

        message = A2AMessage(
            method="tasks/get",
            params={"id": task_id},
        )

        response = await client.post(
            target_url,
            json=message.model_dump(),
            headers={"Content-Type": "application/json"},
        )

        return A2AResponse.model_validate(response.json())

    async def cancel_task(self, target_url: str, task_id: str) -> A2AResponse:
        """Cancel a task on another agent."""
        client = await self._get_client()

        message = A2AMessage(
            method="tasks/cancel",
            params={"id": task_id},
        )

        response = await client.post(
            target_url,
            json=message.model_dump(),
            headers={"Content-Type": "application/json"},
        )

        return A2AResponse.model_validate(response.json())

    def create_task(self, text: str, metadata: dict[str, Any] | None = None) -> Task:
        """Create a new task with initial message."""
        task = Task(metadata=metadata or {})
        task.add_message("user", text)
        return task

    def create_response(
        self,
        task: Task,
        text: str,
        status: TaskState = TaskState.COMPLETED,
    ) -> dict[str, Any]:
        """Create a task response."""
        task.add_message("agent", text)
        task.status = status

        return {
            "id": task.id,
            "sessionId": task.session_id,
            "status": {"state": status.value},
            "history": [
                {
                    "role": m.role,
                    "parts": [p.model_dump() for p in m.parts],
                }
                for m in task.history
            ],
            "metadata": task.metadata,
        }

    def create_input_required_response(
        self,
        task: Task,
        prompt: str,
        input_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create an input-required response (used for x402 payment)."""
        task.status = TaskState.INPUT_REQUIRED

        return {
            "id": task.id,
            "sessionId": task.session_id,
            "status": {
                "state": TaskState.INPUT_REQUIRED.value,
                "message": {
                    "role": "agent",
                    "parts": [{"type": "text", "text": prompt}],
                },
            },
            "inputSchema": input_schema,
            "metadata": task.metadata,
        }
