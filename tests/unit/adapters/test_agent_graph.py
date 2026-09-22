"""Deterministic unit tests for LangGraph state machine and cognitive agent adapter."""

from datetime import UTC, datetime

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage

from grc_tool.adapters.agents.graph import (
    LangGraphAuditAgent,
    route_user_turn,
)
from grc_tool.adapters.agents.state import AuditGraphState, append_unique_evidence
from grc_tool.core.models.evidence import Evidence, EvidenceType
from grc_tool.core.models.finding import FindingSeverity


def test_evidence_reducer_deduplication() -> None:
    """Verify evidence reducer preserves unique items based on evidence_id."""
    ev1 = Evidence(
        evidence_id="EV-1",
        evidence_type=EvidenceType.POLICY_DOCUMENT,
        source_system="eramba",
        title="Policy A",
        payload={"approved": True},
        collected_at=datetime.now(UTC),
    )
    ev2 = Evidence(
        evidence_id="EV-2",
        evidence_type=EvidenceType.TECHNICAL_CONFIG,
        source_system="wazuh",
        title="Config B",
        payload={"mfa": True},
        collected_at=datetime.now(UTC),
    )
    ev1_duplicate = Evidence(
        evidence_id="EV-1",
        evidence_type=EvidenceType.POLICY_DOCUMENT,
        source_system="eramba",
        title="Policy A (Duplicate)",
        payload={"approved": True},
        collected_at=datetime.now(UTC),
    )

    # Empty new items returns current
    assert append_unique_evidence([ev1], []) == [ev1]

    # Appending distinct items
    merged = append_unique_evidence([ev1], [ev2])
    assert len(merged) == 2
    assert [e.evidence_id for e in merged] == ["EV-1", "EV-2"]

    # Appending duplicate ID is ignored
    deduped = append_unique_evidence(merged, [ev1_duplicate])
    assert len(deduped) == 2


def test_route_user_turn_intent_detection() -> None:
    """Verify conditional edge routing based on user input semantics."""
    # Empty messages routes to auditor
    state_empty: AuditGraphState = {
        "session_id": "s1",
        "control_code": "6.1.2",
        "messages": [],
        "collected_evidence": [],
        "evaluation_result": None,
        "finding": None,
        "phase": "INITIALIZING",
        "status": "ACTIVE",
    }
    assert route_user_turn(state_empty) == "auditor"

    # Hint / coaching intent
    state_coach: AuditGraphState = dict(state_empty)  # type: ignore[assignment]
    state_coach["messages"] = [HumanMessage(content="I am stuck, can you give me a hint?")]
    assert route_user_turn(state_coach) == "coach"

    # Evaluation / conclusion intent
    state_eval: AuditGraphState = dict(state_empty)  # type: ignore[assignment]
    state_eval["messages"] = [
        HumanMessage(content="I am ready for audit, please evaluate my evidence")
    ]
    assert route_user_turn(state_eval) == "evaluator"

    # Standard audit dialogue
    state_auditor: AuditGraphState = dict(state_empty)  # type: ignore[assignment]
    state_auditor["messages"] = [
        HumanMessage(content="Here is our risk assessment procedure summary.")
    ]
    assert route_user_turn(state_auditor) == "auditor"


def test_agent_multi_turn_lifecycle() -> None:
    """Verify multi-turn session lifecycle with deterministic mock responses."""
    responses = [
        # 1. Opening Auditor Inquiry
        "Welcome to the ISO 27001 audit. Please explain your risk assessment methodology.",
        # 2. Socratic Coach Hint
        "Consider what criteria are required by Clause 6.1.2: likelihood, impact, and risk owner.",
        # 3. Follow-up Auditor Inquiry
        "Thank you. Can you demonstrate who the assigned risk owners are?",
    ]
    fake_llm = FakeListChatModel(responses=responses)
    agent = LangGraphAuditAgent(llm=fake_llm)

    session_id = "test-session-001"

    # Turn 1: Start Session -> Auditor Node
    state1 = agent.start_session(session_id=session_id, control_code="6.1.2")
    assert state1["phase"] == "INQUIRY"
    assert state1["status"] == "ACTIVE"
    last_msg = state1["messages"][-1]
    assert isinstance(last_msg, AIMessage)
    assert "explain your risk assessment methodology" in last_msg.content

    # Turn 2: Learner asks for help -> Coach Node
    state2 = agent.process_turn(
        session_id=session_id,
        user_message="I need help understanding what is expected here.",
    )
    assert state2["phase"] == "COACHING"
    last_msg2 = state2["messages"][-1]
    assert isinstance(last_msg2, AIMessage)
    assert "Consider what criteria are required" in last_msg2.content

    # Turn 3: Learner responds to Auditor -> Auditor Node
    state3 = agent.process_turn(
        session_id=session_id,
        user_message="We define qualitative risk matrices with 5x5 impact and likelihood.",
    )
    assert state3["phase"] == "INQUIRY"
    last_msg3 = state3["messages"][-1]
    assert isinstance(last_msg3, AIMessage)
    assert "assigned risk owners" in last_msg3.content

    # Turn 4: Learner submits complete evidence and requests evaluation -> Evaluator Node
    evidence_bundle = [
        Evidence(
            evidence_id="EV-RISK-01",
            evidence_type=EvidenceType.RISK_REGISTER_ENTRY,
            source_system="eramba",
            title="Formal Risk Assessment Register",
            payload={
                "methodology_documented": True,
                "risk_owner_assigned": True,
                "risk_criteria_defined": True,
                "annual_review_completed": True,
            },
            collected_at=datetime.now(UTC),
        )
    ]
    state4 = agent.process_turn(
        session_id=session_id,
        user_message="All evidence uploaded. Ready for audit evaluation.",
        evidence=evidence_bundle,
    )
    assert state4["phase"] == "CONCLUDED"
    assert state4["status"] == "CONCLUDED"
    assert state4["evaluation_result"] is not None
    assert state4["evaluation_result"].is_compliant
    assert state4["finding"] is not None
    assert state4["finding"].severity == FindingSeverity.CONFORMANT
    last_msg4 = state4["messages"][-1]
    assert "AUDIT CONCLUSION - CONFORMANT" in last_msg4.content

    # Turn 5: Verify get_state retrieves persistent snapshot from checkpointer
    recovered = agent.get_state(session_id=session_id)
    assert recovered is not None
    assert recovered["session_id"] == session_id
    assert recovered["status"] == "CONCLUDED"
    assert len(recovered["collected_evidence"]) == 1

    # Non-existent session
    assert agent.get_state("non-existent-id") is None


def test_agent_evaluation_non_conformity() -> None:
    """Verify evaluator node correctly concludes with a Non-Conformity when evidence is missing."""
    fake_llm = FakeListChatModel(responses=["Opening question."])
    agent = LangGraphAuditAgent(llm=fake_llm)
    session_id = "test-session-nc"

    agent.start_session(session_id=session_id, control_code="6.1.2")

    # Learner submits empty evidence and requests audit conclusion
    state_nc = agent.process_turn(
        session_id=session_id,
        user_message="I have no evidence ready, please conclude audit now.",
        evidence=[],
    )
    assert state_nc["phase"] == "CONCLUDED"
    assert state_nc["status"] == "CONCLUDED"
    assert state_nc["finding"] is not None
    assert state_nc["finding"].severity == FindingSeverity.MAJOR_NC
    last_msg = state_nc["messages"][-1]
    assert "AUDIT CONCLUSION - MAJOR_NON_CONFORMITY" in last_msg.content
    assert "Corrective Action Required" in last_msg.content
