"""Health check endpoints."""

import logging

import httpx
from fastapi import APIRouter

from hashbot.agents.registry import get_registry
from hashbot.config import get_settings
from hashbot.openclaw.client import OpenClawClient

router = APIRouter()

# Shared OpenClaw client — set by server.main at startup
_openclaw_client: OpenClawClient | None = None


def set_openclaw_client(client: OpenClawClient) -> None:
    global _openclaw_client
    _openclaw_client = client


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

    chain_status = "unreachable"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                settings.hashkey_rpc_url,
                json={"jsonrpc": "2.0", "method": "net_version", "params": [], "id": 1},
            )
            if resp.status_code == 200:
                chain_status = "connected"
    except Exception:
        logging.warning("Health check: chain RPC unreachable")

    # OpenClaw gateway status
    openclaw_status = "unknown"
    if _openclaw_client:
        openclaw_status = "connected" if await _openclaw_client.health_check() else "unreachable"

    return {
        "status": "healthy" if chain_status == "connected" else "degraded",
        "chain": settings.hashkey_rpc_url,
        "chain_id": settings.hashkey_chain_id,
        "chain_status": chain_status,
        "agents": len(registry.list_agents()),
        "openclaw_status": openclaw_status,
        "openclaw_url": settings.openclaw_gateway_url,
    }


@router.get("/agents")
async def list_agents():
    """List available agents."""
    registry = get_registry()
    return {"agents": registry.list_agents()}
