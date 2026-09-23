"""Pydantic DTO schemas for the FastAPI presentation layer."""

from pydantic import BaseModel, Field

from grc_tool.adapters.sandbox.mock_sandbox import ScenarioMode


class CreateSessionRequest(BaseModel):
    """Payload to initiate an ISO 27001 audit simulation session."""

    control_code: str = Field(
        default="6.1.2",
        description="ISO standard clause or Annex A control code, e.g. '6.1.2' or 'A.5.15'",
    )


class ProcessTurnRequest(BaseModel):
    """Payload representing a learner's conversational turn or evidence submission."""

    user_message: str = Field(
        ...,
        description="Learner's response, inquiry, hint request, or audit conclusion trigger",
    )


class ScenarioSwitchRequest(BaseModel):
    """Payload to toggle simulation scenario in the sandbox."""

    scenario: ScenarioMode = Field(
        default=ScenarioMode.COMPLIANT,
        description="Target simulation state scenario",
    )


class MessageDTO(BaseModel):
    """Representation of a conversational message in the audit session."""

    role: str = Field(description="'auditee', 'auditor', or 'coach'")
    content: str = Field(description="Textual dialogue content")


class FindingDTO(BaseModel):
    """Structured audit finding representation."""

    finding_id: str
    control_code: str
    severity: str
    title: str
    statement: str
    remediation_guidance: str | None = None


class SessionResponse(BaseModel):
    """Full snapshot of an ongoing or completed audit simulation session."""

    session_id: str
    control_code: str
    phase: str
    status: str
    messages: list[MessageDTO]
    finding: FindingDTO | None = None


class ControlSummaryDTO(BaseModel):
    """Summary of an ISO 27001 standard requirement available for simulation."""

    code: str
    title: str
    statement: str
    is_annex_a: bool
    category: str
