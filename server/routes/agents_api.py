"""REST API for agent management (dashboard + external)."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hashbot.db import crud
from hashbot.openclaw.client import OpenClawClient
from hashbot.openclaw.manager import OpenClawManager
from hashbot.openclaw.skills import get_skill, list_skills

router = APIRouter()

# Shared instances — set by server.main at startup
_openclaw_client: OpenClawClient | None = None
_openclaw_manager: OpenClawManager | None = None


def set_openclaw(client: OpenClawClient, manager: OpenClawManager) -> None:
    global _openclaw_client, _openclaw_manager
    _openclaw_client = client
    _openclaw_manager = manager


# ── Request schemas ────────────────────────────────────────────────────

class CreateAgentRequest(BaseModel):
    owner_telegram_id: int
    name: str
    description: str = ""
    soul_text: str = ""


class UpdateAgentRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    is_public: bool | None = None
    price_per_call: float | None = None


class ChatRequest(BaseModel):
    text: str
    session_key: str = ""


class InstallSkillRequest(BaseModel):
    slug: str


# ── Endpoints ──────────────────────────────────────────────────────────

@router.get("/")
async def list_public_agents():
    """List all public agents."""
    agents = await crud.get_public_agents()
    return {"agents": [_agent_dict(a) for a in agents]}


@router.get("/user/{telegram_id}")
async def list_user_agents(telegram_id: int):
    """List agents owned by a specific user (by telegram_id)."""
    user = await crud.get_user_by_telegram_id(telegram_id)
    if user is None:
        return {"agents": []}
    agents = await crud.get_user_agents(user.id)
    return {"agents": [_agent_dict(a) for a in agents]}


@router.post("/")
async def create_agent(req: CreateAgentRequest):
    """Create a new agent with OpenClaw workspace."""
    user = await crud.get_or_create_user(
        telegram_id=req.owner_telegram_id,
        display_name="Dashboard User",
    )

    # Check limit
    existing = await crud.get_user_agents(user.id)
    from hashbot.config import get_settings
    settings = get_settings()
    if len(existing) >= settings.max_agents_per_user:
        raise HTTPException(400, f"Max {settings.max_agents_per_user} agents per user")

    # Create workspace
    manager = _get_manager()
    agent_id_hint = f"user_{user.telegram_id}_{len(existing)}"
    workspace = await manager.create_agent_workspace(
        agent_id_hint, req.name, req.description, req.soul_text,
    )

    # Persist in DB
    agent = await crud.create_agent(
        owner_id=user.id,
        name=req.name,
        description=req.description,
        openclaw_agent_id=agent_id_hint,
        workspace_path=workspace,
    )

    # Register in gateway (best-effort)
    await manager.register_agent_in_gateway(agent_id_hint, workspace)

    return _agent_dict(agent)


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent details."""
    agent = await crud.get_agent_by_id(agent_id)
    if agent is None:
        raise HTTPException(404, "Agent not found")
    return _agent_dict(agent)


@router.patch("/{agent_id}")
async def update_agent(agent_id: str, req: UpdateAgentRequest):
    """Update agent fields."""
    updates: dict[str, Any] = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.description is not None:
        updates["description"] = req.description
    if req.is_public is not None:
        updates["is_public"] = req.is_public
    if req.price_per_call is not None:
        updates["price_per_call"] = req.price_per_call

    agent = await crud.update_agent(agent_id, **updates)
    if agent is None:
        raise HTTPException(404, "Agent not found")
    return _agent_dict(agent)


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete agent and its workspace."""
    agent = await crud.get_agent_by_id(agent_id)
    if agent is None:
        raise HTTPException(404, "Agent not found")

    manager = _get_manager()
    await manager.delete_agent_workspace(agent.openclaw_agent_id)
    await crud.delete_agent(agent_id)
    return {"ok": True}


@router.get("/{agent_id}/skills")
async def get_agent_skills(agent_id: str):
    """List installed skills + available built-in skills."""
    installed = await crud.get_agent_skills(agent_id)
    installed_slugs = {s.skill_slug for s in installed}
    available = [s for s in list_skills() if s["slug"] not in installed_slugs]
    return {
        "installed": [
            {"slug": s.skill_slug, "source": s.source, "enabled": s.is_enabled}
            for s in installed
        ],
        "available": available,
    }


@router.post("/{agent_id}/skills")
async def install_agent_skill(agent_id: str, req: InstallSkillRequest):
    """Install a built-in skill to an agent."""
    agent = await crud.get_agent_by_id(agent_id)
    if agent is None:
        raise HTTPException(404, "Agent not found")

    skill_data = get_skill(req.slug)
    if skill_data is None:
        raise HTTPException(404, f"Skill not found: {req.slug}")

    manager = _get_manager()
    await manager.install_skill_to_workspace(
        agent.workspace_path, req.slug, skill_data["content"],
    )
    skill = await crud.install_skill(agent_id, req.slug, source="builtin")
    return {"slug": skill.skill_slug, "source": skill.source, "enabled": skill.is_enabled}


@router.delete("/{agent_id}/skills/{slug}")
async def remove_agent_skill(agent_id: str, slug: str):
    """Remove a skill from an agent."""
    agent = await crud.get_agent_by_id(agent_id)
    if agent is None:
        raise HTTPException(404, "Agent not found")

    manager = _get_manager()
    await manager.remove_skill_from_workspace(agent.workspace_path, slug)
    await crud.remove_skill(agent_id, slug)
    return {"ok": True}


@router.post("/{agent_id}/chat")
async def chat_with_agent(agent_id: str, req: ChatRequest):
    """Send a message to an agent via OpenClaw."""
    agent = await crud.get_agent_by_id(agent_id)
    if agent is None:
        raise HTTPException(404, "Agent not found")

    client = _get_client()
    session_key = req.session_key or f"dashboard_{agent_id}"
    try:
        response = await client.send_message(
            agent.openclaw_agent_id, session_key, req.text,
        )
        return {"response": response}
    except Exception as exc:
        raise HTTPException(502, f"OpenClaw error: {exc}")


# ── Helpers ────────────────────────────────────────────────────────────

def _agent_dict(agent) -> dict[str, Any]:
    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "openclaw_agent_id": agent.openclaw_agent_id,
        "is_public": agent.is_public,
        "price_per_call": float(agent.price_per_call),
        "currency": agent.currency,
        "created_at": str(agent.created_at),
    }


def _get_client() -> OpenClawClient:
    if _openclaw_client is None:
        raise HTTPException(503, "OpenClaw client not initialised")
    return _openclaw_client


def _get_manager() -> OpenClawManager:
    if _openclaw_manager is None:
        raise HTTPException(503, "OpenClaw manager not initialised")
    return _openclaw_manager
