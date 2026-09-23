"""FastAPI router implementing REST endpoints and SSE streaming."""

import json
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage

from grc_tool.adapters.sandbox.mock_sandbox import MockSandboxAdapter
from grc_tool.api.schemas import (
    ControlSummaryDTO,
    CreateSessionRequest,
    FindingDTO,
    MessageDTO,
    ProcessTurnRequest,
    ScenarioSwitchRequest,
    SessionResponse,
)
from grc_tool.application.ports.agent import AuditAgentPort
from grc_tool.application.ports.sandbox import SandboxPort
from grc_tool.core.models.finding import AuditFinding
from grc_tool.core.models.iso_standard import list_controls


def _format_session_response(session_id: str, state: dict[str, Any]) -> SessionResponse:
    """Transform raw graph state into API SessionResponse DTO."""
    messages_dto: list[MessageDTO] = []
    for msg in state.get("messages", []):
        if isinstance(msg, HumanMessage):
            role = "auditee"
        elif isinstance(msg, AIMessage):
            role = "auditor" if state.get("phase") != "COACHING" else "coach"
        else:
            role = "system"
        messages_dto.append(
            MessageDTO(
                role=role,
                content=msg.content if isinstance(msg.content, str) else str(msg.content),
            )
        )

    finding_dto: FindingDTO | None = None
    raw_finding = state.get("finding")
    if isinstance(raw_finding, AuditFinding):
        finding_dto = FindingDTO(
            finding_id=raw_finding.finding_id,
            control_code=raw_finding.control_code,
            severity=raw_finding.severity.value,
            title=raw_finding.title,
            statement=raw_finding.statement,
            remediation_guidance=raw_finding.remediation_guidance,
        )

    return SessionResponse(
        session_id=session_id,
        control_code=str(state.get("control_code", "6.1.2")),
        phase=str(state.get("phase", "INQUIRY")),
        status=str(state.get("status", "ACTIVE")),
        messages=messages_dto,
        finding=finding_dto,
    )


def create_api_router(agent: AuditAgentPort, sandbox: SandboxPort) -> APIRouter:
    """Construct APIRouter wired with application port dependencies."""
    router = APIRouter(prefix="/api/v1")

    @router.get("/controls", response_model=list[ControlSummaryDTO])
    def get_controls() -> list[ControlSummaryDTO]:
        """List all available ISO 27001:2022 clauses and Annex A controls."""
        controls = list_controls()
        return [
            ControlSummaryDTO(
                code=c.code,
                title=c.title,
                statement=c.statement,
                is_annex_a=c.is_annex_a,
                category=(
                    c.theme.value
                    if c.is_annex_a and c.theme
                    else (c.clause.value if c.clause else "Clause")
                ),
            )
            for c in controls
        ]

    @router.post(
        "/sessions",
        response_model=SessionResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_session(request: CreateSessionRequest) -> SessionResponse:
        """Initialize a new simulation session for an ISO 27001 control."""
        session_id = f"sim-{uuid4().hex[:8]}"
        state = agent.start_session(session_id=session_id, control_code=request.control_code)
        return _format_session_response(session_id, state)

    @router.post("/sessions/{session_id}/turns", response_model=SessionResponse)
    def process_turn(session_id: str, request: ProcessTurnRequest) -> SessionResponse:
        """Submit a user response or hint request to the cognitive agent."""
        existing = agent.get_state(session_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' not found.",
            )

        updated_state = agent.process_turn(session_id=session_id, user_message=request.user_message)
        return _format_session_response(session_id, updated_state)

    @router.get("/sessions/{session_id}", response_model=SessionResponse)
    def get_session(session_id: str) -> SessionResponse:
        """Retrieve the current snapshot state of an audit simulation session."""
        state = agent.get_state(session_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' not found.",
            )
        return _format_session_response(session_id, state)

    @router.get("/sessions/{session_id}/stream")
    async def stream_session(session_id: str) -> StreamingResponse:
        """Stream real-time session events using Server-Sent Events (SSE)."""
        state = agent.get_state(session_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' not found.",
            )

        async def event_generator() -> AsyncGenerator[str, None]:
            data = _format_session_response(session_id, state).model_dump()
            yield f"event: update\ndata: {json.dumps(data)}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @router.post("/sandbox/scenario")
    def switch_sandbox_scenario(
        request: ScenarioSwitchRequest,
    ) -> dict[str, str]:
        """Switch simulation scenario state in the target sandbox."""
        if isinstance(sandbox, MockSandboxAdapter):
            sandbox.set_scenario(request.scenario)
            return {
                "status": "updated",
                "scenario": request.scenario.value,
            }
        return {
            "status": "skipped",
            "message": "Connected to live external sandbox",
        }

    @router.get("/sandbox/health")
    def sandbox_health() -> dict[str, bool]:
        """Check operational connectivity to target sandbox."""
        return {"healthy": sandbox.health_check()}

    return router
