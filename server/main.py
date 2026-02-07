"""HashBot API Server entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import example agents to register them
from hashbot.agents.examples import (  # noqa: F401
    CodeReviewerAgent,
    CryptoAnalystAgent,
    TranslatorAgent,
)
from hashbot.agents.registry import get_registry
from hashbot.config import get_settings
from hashbot.db import close_db, init_db
from hashbot.openclaw.client import OpenClawClient
from hashbot.openclaw.manager import OpenClawManager
from server.routes.a2a import router as a2a_router
from server.routes.agents_api import router as agents_api_router
from server.routes.agents_api import set_openclaw
from server.routes.dashboard import router as dashboard_router
from server.routes.health import router as health_router
from server.routes.health import set_openclaw_client
from server.routes.webhook import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    settings = get_settings()
    print(f"Starting HashBot on {settings.api_host}:{settings.api_port}")
    print(f"HashKey Chain: {settings.hashkey_rpc_url}")

    # Initialize database
    await init_db()
    print("Database initialised")

    # Initialize agent registry
    registry = get_registry()
    print(f"Registered agents: {[a['id'] for a in registry.list_agents()]}")

    # Initialize OpenClaw client + manager
    openclaw_client = OpenClawClient()
    openclaw_manager = OpenClawManager(client=openclaw_client)
    app.state.openclaw_client = openclaw_client
    app.state.openclaw_manager = openclaw_manager
    set_openclaw_client(openclaw_client)
    set_openclaw(openclaw_client, openclaw_manager)
    print(f"OpenClaw gateway: {settings.openclaw_gateway_url}")

    yield

    # Shutdown
    print("Shutting down HashBot...")
    await openclaw_client.close()
    await registry.shutdown()
    await close_db()


def create_app() -> FastAPI:
    """Create FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="HashBot",
        description="Agent Economy on HashKey Chain - A2A Protocol with x402 Payments",
        version="0.1.0",
        docs_url="/docs" if settings.api_debug else None,
        redoc_url="/redoc" if settings.api_debug else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(a2a_router, prefix="/a2a", tags=["A2A Protocol"])
    app.include_router(webhook_router, prefix="/webhook", tags=["Webhooks"])
    app.include_router(agents_api_router, prefix="/api/agents", tags=["Agents API"])
    app.include_router(dashboard_router, tags=["Dashboard"])

    # Mount static files
    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app


app = create_app()


def main():
    """Run the server."""
    settings = get_settings()
    uvicorn.run(
        "server.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
    )


if __name__ == "__main__":
    main()
