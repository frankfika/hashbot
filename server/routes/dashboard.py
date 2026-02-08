"""Dashboard web UI routes."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from hashbot.agents.registry import get_registry
from hashbot.db import crud

router = APIRouter()

_templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Dashboard home page."""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "active_page": "home"},
    )


@router.get("/dashboard/agents", response_class=HTMLResponse)
async def dashboard_agents(request: Request):
    """Redirect old built-in agents page to explore."""
    return RedirectResponse(url="/dashboard/explore", status_code=302)


@router.get("/dashboard/agents/{agent_id}", response_class=HTMLResponse)
async def dashboard_agent_chat(request: Request, agent_id: str):
    """Agent chat page — works for both built-in and user-created agents."""
    registry = get_registry()
    agents = registry.list_agents()

    # Check built-in registry first
    agent = None
    for a in agents:
        if a["id"] == agent_id:
            agent = a
            break

    # Fall back to DB agent
    if agent is None:
        db_agent = await crud.get_agent_by_id(agent_id)
        if db_agent:
            agent = {
                "id": db_agent.id,
                "name": db_agent.name,
                "description": db_agent.description,
                "price": f"{db_agent.price_per_call} {db_agent.currency}"
                if db_agent.price_per_call
                else "Free",
                "version": "1.0.0",
                "is_openclaw": True,
            }

    if agent is None:
        agent = {
            "id": agent_id,
            "name": agent_id.replace("_", " ").title(),
            "description": "Agent not found in registry",
            "price": "Unknown",
            "version": "0.0.0",
        }

    return templates.TemplateResponse(
        "agent_chat.html",
        {"request": request, "active_page": "explore", "agent": agent},
    )


@router.get("/dashboard/my-agents", response_class=HTMLResponse)
async def dashboard_my_agents(request: Request):
    """User's own agents management page."""
    return templates.TemplateResponse(
        "my_agents.html",
        {"request": request, "active_page": "my-agents", "telegram_id": 0},
    )


@router.get("/dashboard/my-agents/{agent_id}", response_class=HTMLResponse)
async def dashboard_agent_detail(request: Request, agent_id: str):
    """Agent detail / edit page."""
    db_agent = await crud.get_agent_by_id(agent_id)
    if db_agent is None:
        agent = {
            "id": agent_id,
            "name": "Not Found",
            "description": "",
            "openclaw_agent_id": "",
            "is_public": False,
            "price_per_call": 0,
            "created_at": "",
        }
    else:
        agent = {
            "id": db_agent.id,
            "name": db_agent.name,
            "description": db_agent.description,
            "openclaw_agent_id": db_agent.openclaw_agent_id,
            "is_public": db_agent.is_public,
            "price_per_call": float(db_agent.price_per_call),
            "created_at": str(db_agent.created_at),
        }

    return templates.TemplateResponse(
        "agent_detail.html",
        {"request": request, "active_page": "my-agents", "agent": agent},
    )


@router.get("/dashboard/my-agents/{agent_id}/skills", response_class=HTMLResponse)
async def dashboard_agent_skills(request: Request, agent_id: str):
    """Agent skill management page."""
    db_agent = await crud.get_agent_by_id(agent_id)
    if db_agent is None:
        agent = {"id": agent_id, "name": "Not Found"}
    else:
        agent = {"id": db_agent.id, "name": db_agent.name}

    return templates.TemplateResponse(
        "agent_skills.html",
        {"request": request, "active_page": "my-agents", "agent": agent},
    )


@router.get("/dashboard/explore", response_class=HTMLResponse)
async def dashboard_explore(request: Request):
    """Public agent marketplace page."""
    return templates.TemplateResponse(
        "explore.html",
        {"request": request, "active_page": "explore"},
    )


@router.get("/dashboard/settings", response_class=HTMLResponse)
async def dashboard_settings(request: Request):
    """Settings and info page."""
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "active_page": "settings"},
    )
