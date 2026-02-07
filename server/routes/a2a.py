"""A2A Protocol API endpoints."""

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from hashbot.a2a.messages import Message, Task, TextPart
from hashbot.agents.registry import get_registry
from hashbot.config import get_settings
from hashbot.db import crud

router = APIRouter()


class TaskSendRequest(BaseModel):
    """Request body for tasks/send."""

    jsonrpc: str = "2.0"
    id: str
    method: str
    params: dict[str, Any]


@router.get("/.well-known/agent.json")
async def get_agent_card(request: Request):
    """Return agent card for discovery."""
    settings = get_settings()
    registry = get_registry()

    base_url = str(request.base_url).rstrip("/")

    # Get all registered agents and combine into one card
    agents = registry.list_agents()

    return {
        "name": settings.agent_name,
        "description": settings.agent_description,
        "url": f"{base_url}/a2a",
        "version": "0.1.0",
        "protocolVersion": "0.1",
        "skills": [
            {
                "id": agent["id"],
                "name": agent["name"],
                "description": agent["description"],
            }
            for agent in agents
        ],
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text", "data"],
        "x402Enabled": True,
        "x402ExtensionUri": "https://github.com/google-a2a/a2a-x402/v0.1",
        "metadata": {
            "chain": "hashkey",
            "chainId": settings.hashkey_chain_id,
        },
    }


@router.post("")
@router.post("/")
async def handle_a2a_request(request: TaskSendRequest):
    """Handle A2A JSON-RPC requests."""
    method = request.method
    params = request.params

    if method == "tasks/send":
        return await _handle_tasks_send(request.id, params)
    elif method == "tasks/get":
        return await _handle_tasks_get(request.id, params)
    elif method == "tasks/cancel":
        return await _handle_tasks_cancel(request.id, params)
    else:
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }


async def _handle_tasks_send(request_id: str, params: dict[str, Any]) -> dict[str, Any]:
    """Handle tasks/send method."""
    registry = get_registry()

    task_id = params.get("id")
    session_id = params.get("sessionId")
    message_data = params.get("message", {})
    metadata = params.get("metadata", {})

    # Determine which agent to use
    agent_id = metadata.get("skill_id", "crypto_analyst")

    # Check if this is a user-created (OpenClaw) agent in the DB
    db_agent = await crud.get_agent_by_id(agent_id)
    if db_agent and db_agent.openclaw_agent_id:
        return await _handle_openclaw_task(request_id, db_agent, message_data, session_id)

    # Fall back to built-in registry
    if agent_id not in [a["id"] for a in registry.list_agents()]:
        # Try first available agent
        agents = registry.list_agents()
        if agents:
            agent_id = agents[0]["id"]
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": "No agents available"},
            }

    # Create task
    task = Task(
        id=task_id or None,
        session_id=session_id or None,
        metadata=metadata,
    )

    # Add incoming message
    parts = []
    for part_data in message_data.get("parts", []):
        if part_data.get("type") == "text":
            parts.append(TextPart(text=part_data.get("text", "")))
    if parts:
        task.history.append(Message(role="user", parts=parts))

    # Process with agent
    result = await registry.process_task(agent_id, task)

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }


async def _handle_openclaw_task(
    request_id: str,
    db_agent,
    message_data: dict[str, Any],
    session_id: str | None,
) -> dict[str, Any]:
    """Route a task to an OpenClaw agent."""
    from hashbot.openclaw.client import OpenClawClient

    # Extract user text
    text = ""
    for part in message_data.get("parts", []):
        if part.get("type") == "text":
            text += part.get("text", "")

    if not text:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32602, "message": "No text in message"},
        }

    client = OpenClawClient()
    try:
        response = await client.send_message(
            db_agent.openclaw_agent_id,
            session_id or f"a2a_{db_agent.id}",
            text,
        )
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "id": request_id,
                "sessionId": session_id,
                "status": {"state": "completed"},
                "history": [
                    {"role": "user", "parts": [{"type": "text", "text": text}]},
                    {"role": "agent", "parts": [{"type": "text", "text": response}]},
                ],
            },
        }
    except Exception as exc:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32000, "message": f"OpenClaw error: {exc}"},
        }
    finally:
        await client.close()


async def _handle_tasks_get(request_id: str, params: dict[str, Any]) -> dict[str, Any]:
    """Handle tasks/get method."""
    task_id = params.get("id")

    # For now, return not found (implement task storage for persistence)
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32602, "message": f"Task not found: {task_id}"},
    }


async def _handle_tasks_cancel(request_id: str, params: dict[str, Any]) -> dict[str, Any]:
    """Handle tasks/cancel method."""
    task_id = params.get("id")

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {"id": task_id, "status": {"state": "canceled"}},
    }
