"""FastAPI application factory and middleware configuration."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from grc_tool.adapters.agents.graph import LangGraphAuditAgent
from grc_tool.adapters.sandbox.mock_sandbox import MockSandboxAdapter
from grc_tool.api.router import create_api_router
from grc_tool.application.ports.agent import AuditAgentPort
from grc_tool.application.ports.sandbox import SandboxPort

STATIC_DIR = Path(__file__).parent / "static"


def create_app(
    agent: AuditAgentPort | None = None,
    sandbox: SandboxPort | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="GRC Learning Platform - ISO 27001 Simulation Engine",
        description=(
            "Interactive GRC training platform featuring LangGraph cognitive agents "
            "and open-source GRC simulation."
        ),
        version="0.1.0",
    )

    # Enable CORS for local development and integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Fallback default adapters for out-of-the-box local execution
    effective_sandbox = sandbox or MockSandboxAdapter()
    effective_agent: AuditAgentPort
    if agent is None:
        default_responses = [
            "Welcome to the ISO 27001 audit. Let's examine your risk assessment process.",
            "Consider reviewing your asset classification and criteria before answering.",
            "Please provide objective evidence showing the designated risk owner.",
        ]
        effective_agent = LangGraphAuditAgent(llm=FakeListChatModel(responses=default_responses))
    else:
        effective_agent = agent

    # Mount API routes
    api_router = create_api_router(agent=effective_agent, sandbox=effective_sandbox)
    app.include_router(api_router)

    # Static file serving & SPA root
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def serve_spa() -> FileResponse:
        """Serve the interactive Single Page Application."""
        index_file = STATIC_DIR / "index.html"
        if not index_file.exists():
            return FileResponse(__file__)  # fallback
        return FileResponse(index_file)

    return app
