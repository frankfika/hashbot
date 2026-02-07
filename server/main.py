"""HashBot API Server entry point."""

import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hashbot.config import get_settings
from hashbot.agents.registry import get_registry

# Import example agents to register them
from hashbot.agents.examples import (  # noqa: F401
    CryptoAnalystAgent,
    TranslatorAgent,
    CodeReviewerAgent,
)

from server.routes.a2a import router as a2a_router
from server.routes.webhook import router as webhook_router
from server.routes.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    settings = get_settings()
    print(f"Starting HashBot on {settings.api_host}:{settings.api_port}")
    print(f"HashKey Chain: {settings.hashkey_rpc_url}")

    # Initialize agent registry
    registry = get_registry()
    print(f"Registered agents: {[a['id'] for a in registry.list_agents()]}")

    yield

    # Shutdown
    print("Shutting down HashBot...")
    await registry.shutdown()


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
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(a2a_router, prefix="/a2a", tags=["A2A Protocol"])
    app.include_router(webhook_router, prefix="/webhook", tags=["Webhooks"])

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
