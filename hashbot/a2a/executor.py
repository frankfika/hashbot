"""A2A Protocol executor for handling incoming requests."""

from collections.abc import Awaitable, Callable
from typing import Any

from hashbot.a2a.messages import (
    A2AMessage,
    AgentCard,
    Message,
    Task,
    TaskState,
    TextPart,
)
from hashbot.a2a.protocol import A2AProtocol

# Type alias for task handlers
TaskHandler = Callable[[Task], Awaitable[dict[str, Any]]]


class A2AExecutor:
    """Executor for processing incoming A2A requests."""

    def __init__(self, agent_card: AgentCard):
        self.agent_card = agent_card
        self.protocol = A2AProtocol(agent_card)
        self._handlers: dict[str, TaskHandler] = {}
        self._tasks: dict[str, Task] = {}

    def register_handler(self, skill_id: str, handler: TaskHandler) -> None:
        """Register a handler for a skill."""
        self._handlers[skill_id] = handler

    def handler(self, skill_id: str) -> Callable[[TaskHandler], TaskHandler]:
        """Decorator to register a skill handler."""

        def decorator(func: TaskHandler) -> TaskHandler:
            self.register_handler(skill_id, func)
            return func

        return decorator

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle an incoming A2A request."""
        try:
            message = A2AMessage.model_validate(request)
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id", "unknown"),
                "error": {"code": -32600, "message": f"Invalid request: {e}"},
            }

        method = message.method
        params = message.params

        if method == "tasks/send":
            return await self._handle_send_task(message.id, params)
        elif method == "tasks/get":
            return await self._handle_get_task(message.id, params)
        elif method == "tasks/cancel":
            return await self._handle_cancel_task(message.id, params)
        else:
            return {
                "jsonrpc": "2.0",
                "id": message.id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

    async def _handle_send_task(
        self, request_id: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle tasks/send request."""
        task_id = params.get("id")
        session_id = params.get("sessionId")
        message_data = params.get("message", {})
        metadata = params.get("metadata", {})

        # Get or create task
        if task_id and task_id in self._tasks:
            task = self._tasks[task_id]
        else:
            task = Task(
                id=task_id or None,
                session_id=session_id or None,
                metadata=metadata,
            )
            self._tasks[task.id] = task

        # Add incoming message to history
        parts = []
        for part_data in message_data.get("parts", []):
            if part_data.get("type") == "text":
                parts.append(TextPart(text=part_data.get("text", "")))
        if parts:
            task.history.append(Message(role="user", parts=parts))

        # Determine which handler to use
        skill_id = metadata.get("skill_id", "default")
        handler = self._handlers.get(skill_id) or self._handlers.get("default")

        if not handler:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": "No handler for this request"},
            }

        # Execute handler
        try:
            result = await handler(task)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result,
            }
        except Exception as e:
            task.status = TaskState.FAILED
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": str(e)},
            }

    async def _handle_get_task(
        self, request_id: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle tasks/get request."""
        task_id = params.get("id")

        if not task_id or task_id not in self._tasks:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": "Task not found"},
            }

        task = self._tasks[task_id]
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "id": task.id,
                "sessionId": task.session_id,
                "status": {"state": task.status.value},
                "history": [
                    {"role": m.role, "parts": [p.model_dump() for p in m.parts]}
                    for m in task.history
                ],
                "metadata": task.metadata,
            },
        }

    async def _handle_cancel_task(
        self, request_id: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle tasks/cancel request."""
        task_id = params.get("id")

        if not task_id or task_id not in self._tasks:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": "Task not found"},
            }

        task = self._tasks[task_id]
        task.status = TaskState.CANCELED

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"id": task.id, "status": {"state": TaskState.CANCELED.value}},
        }

    def get_agent_card_dict(self) -> dict[str, Any]:
        """Get agent card as dictionary for JSON response."""
        return self.agent_card.model_dump()
