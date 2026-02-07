"""Health check endpoints."""

from fastapi import APIRouter

from hashbot.config import get_settings
from hashbot.agents.registry import get_registry

router = APIRouter()


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "HashBot",
        "version": "0.1.0",
        "description": "Agent Economy on HashKey Chain",
    }


@router.get("/health")
async def health():
    """Health check endpoint."""
    settings = get_settings()
    registry = get_registry()

    return {
        "status": "healthy",
        "chain": settings.hashkey_rpc_url,
        "chain_id": settings.hashkey_chain_id,
        "agents": len(registry.list_agents()),
    }


@router.get("/agents")
async def list_agents():
    """List available agents."""
    registry = get_registry()
    return {"agents": registry.list_agents()}
