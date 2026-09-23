"""Integration tests connecting the LangGraph agent to the simulation sandbox."""

from datetime import UTC, datetime

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from grc_tool.adapters.agents.graph import LangGraphAuditAgent
from grc_tool.adapters.sandbox.mock_sandbox import MockSandboxAdapter, ScenarioMode
from grc_tool.adapters.sandbox.tools import create_sandbox_inspection_tools
from grc_tool.core.models.evidence import Evidence, EvidenceType
from grc_tool.core.models.finding import FindingSeverity


def test_sandbox_inspection_tools_execution() -> None:
    """Verify tool functions correctly format sandbox state into text summaries."""
    sandbox = MockSandboxAdapter(initial_scenario=ScenarioMode.COMPLIANT)
    tools = create_sandbox_inspection_tools(sandbox)
    tool_map = {t.name: t for t in tools}

    # 1. Policy inspection
    pol_tool = tool_map["inspect_policy_repository"]
    pol_res = pol_tool.invoke({"policy_id": "POL-ACCESS-01"})
    assert "Status: APPROVED" in pol_res
    assert "Owner: ciso@company.local" in pol_res

    # 2. Risk register inspection
    risk_tool = tool_map["inspect_risk_register"]
    risk_res = risk_tool.invoke({"control_code": "6.1.2"})
    assert "Methodology: True" in risk_res
    assert "Owner Assigned: True" in risk_res

    # 3. Technical controls inspection
    tech_tool = tool_map["inspect_technical_controls"]
    tech_res = tech_tool.invoke({"control_code": "A.5.15"})
    assert "MFA: ENFORCED" in tech_res


def test_sandbox_missing_records_messaging() -> None:
    """Verify tools return informative responses when records do not exist."""
    sandbox = MockSandboxAdapter(initial_scenario=ScenarioMode.EMPTY)
    tools = create_sandbox_inspection_tools(sandbox)
    tool_map = {t.name: t for t in tools}

    pol_res = tool_map["inspect_policy_repository"].invoke({"policy_id": "MISSING"})
    assert "was not found" in pol_res

    risk_res = tool_map["inspect_risk_register"].invoke({"control_code": "6.1.2"})
    assert "No risk register records found" in risk_res

    tech_res = tool_map["inspect_technical_controls"].invoke({"control_code": "A.5.15"})
    assert "No technical configuration telemetry available" in tech_res


def test_end_to_end_agent_sandbox_audit_compliant() -> None:
    """Verify end-to-end flow: Agent inspects sandbox, retrieves evidence, renders CONFORMANT."""
    sandbox = MockSandboxAdapter(initial_scenario=ScenarioMode.COMPLIANT)
    fake_llm = FakeListChatModel(responses=["Opening inquiry on Clause 6.1.2 risk assessment."])
    agent = LangGraphAuditAgent(llm=fake_llm)
    session_id = "integration-session-001"

    # Step 1: Start session
    state1 = agent.start_session(session_id=session_id, control_code="6.1.2")
    assert state1["phase"] == "INQUIRY"

    # Step 2: Retrieve objective evidence directly from sandbox
    evidence = sandbox.fetch_risk_register("6.1.2")
    assert len(evidence) == 1

    # Step 3: Conclude audit with retrieved evidence
    state2 = agent.process_turn(
        session_id=session_id,
        user_message="I have configured the risk register in Eramba. Ready for audit.",
        evidence=evidence,
    )
    assert state2["phase"] == "CONCLUDED"
    assert state2["finding"] is not None
    assert state2["finding"].severity == FindingSeverity.CONFORMANT
    assert "AUDIT CONCLUSION - CONFORMANT" in state2["messages"][-1].content


def test_end_to_end_agent_sandbox_audit_deficient() -> None:
    """Verify end-to-end flow: Deficient sandbox state produces a MINOR_NC finding."""
    sandbox = MockSandboxAdapter(initial_scenario=ScenarioMode.DEFICIENT_RISK_OWNER)
    fake_llm = FakeListChatModel(responses=["Opening inquiry on Clause 6.1.2 risk assessment."])
    agent = LangGraphAuditAgent(llm=fake_llm)
    session_id = "integration-session-002"

    agent.start_session(session_id=session_id, control_code="6.1.2")

    # Retrieve deficient evidence from sandbox
    deficient_evidence = sandbox.fetch_risk_register("6.1.2")
    assert not deficient_evidence[0].payload["risk_owner_assigned"]

    # Conclude audit
    state = agent.process_turn(
        session_id=session_id,
        user_message="Ready for audit evaluation with current Eramba state.",
        evidence=deficient_evidence,
    )
    assert state["phase"] == "CONCLUDED"
    assert state["finding"] is not None
    assert state["finding"].severity == FindingSeverity.MINOR_NC
    assert "Corrective Action Required" in state["messages"][-1].content


def test_mock_sandbox_custom_evidence_and_scenarios() -> None:
    """Verify custom evidence injection, scenario switching, and health check."""
    sandbox = MockSandboxAdapter(initial_scenario=ScenarioMode.EMPTY)
    assert sandbox.health_check() is True
    assert sandbox.fetch_policy("P-1") is None
    assert sandbox.fetch_risk_register("6.1.2") == []
    assert sandbox.fetch_technical_controls("A.5.15") == []

    # Scenario switching
    sandbox.set_scenario(ScenarioMode.MISSING_MFA)
    tech = sandbox.fetch_technical_controls("A.5.15")
    assert not tech[0].payload["mfa_enforced"]

    # Custom evidence injection
    custom_pol = Evidence(
        evidence_id="CUSTOM-POL-01",
        evidence_type=EvidenceType.POLICY_DOCUMENT,
        source_system="custom",
        title="Custom Pol",
        payload={"policy_id": "CUSTOM-01", "approved": True},
        collected_at=datetime.now(UTC),
    )
    custom_risk = Evidence(
        evidence_id="CUSTOM-RISK-01",
        evidence_type=EvidenceType.RISK_REGISTER_ENTRY,
        source_system="custom",
        title="Custom Risk",
        payload={"risk_id": "R1"},
        collected_at=datetime.now(UTC),
    )
    sandbox.add_custom_evidence(custom_pol)
    sandbox.add_custom_evidence(custom_risk)

    assert sandbox.fetch_policy("CUSTOM-01") == custom_pol
    assert sandbox.fetch_risk_register("6.1.2") == [custom_risk]
