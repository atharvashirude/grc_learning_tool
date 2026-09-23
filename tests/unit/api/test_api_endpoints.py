"""Unit and integration tests for FastAPI REST endpoints and SSE streaming."""

from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from grc_tool.adapters.agents.graph import LangGraphAuditAgent
from grc_tool.adapters.sandbox.mock_sandbox import MockSandboxAdapter, ScenarioMode
from grc_tool.api.app import create_app


def get_test_client() -> TestClient:
    """Fixture providing a deterministic TestClient wired with mock agent & sandbox."""
    responses = [
        "Opening inquiry for Clause 6.1.2.",
        "Coach hint: verify your risk criteria and risk owners.",
        "Auditor follow-up inquiry.",
    ]
    agent = LangGraphAuditAgent(llm=FakeListChatModel(responses=responses))
    sandbox = MockSandboxAdapter(initial_scenario=ScenarioMode.COMPLIANT)
    app = create_app(agent=agent, sandbox=sandbox)
    return TestClient(app)


def test_list_controls_endpoint() -> None:
    """Verify GET /api/v1/controls returns standard ISO requirements."""
    client = get_test_client()
    res = client.get("/api/v1/controls")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    codes = [item["code"] for item in data]
    assert "6.1.2" in codes
    assert "A.5.15" in codes


def test_create_and_query_session_lifecycle() -> None:
    """Verify session creation, turn processing, and retrieval."""
    client = get_test_client()

    # 1. Create Session
    create_res = client.post("/api/v1/sessions", json={"control_code": "6.1.2"})
    assert create_res.status_code == 201
    created = create_res.json()
    session_id = created["session_id"]
    assert session_id.startswith("sim-")
    assert created["control_code"] == "6.1.2"
    assert created["status"] == "ACTIVE"
    assert len(created["messages"]) >= 2  # Opening human trigger + auditor opening inquiry

    # 2. Process Turn
    turn_res = client.post(
        f"/api/v1/sessions/{session_id}/turns",
        json={"user_message": "Can you give me a hint on what to look for?"},
    )
    assert turn_res.status_code == 200
    turn_data = turn_res.json()
    assert turn_data["phase"] == "COACHING"
    assert any("hint" in m["content"].lower() for m in turn_data["messages"])

    # 3. Retrieve Session
    get_res = client.get(f"/api/v1/sessions/{session_id}")
    assert get_res.status_code == 200
    assert get_res.json()["session_id"] == session_id


def test_turn_non_existent_session_404() -> None:
    """Verify 404 response when querying or processing non-existent sessions."""
    client = get_test_client()

    res_turn = client.post(
        "/api/v1/sessions/sim-missing/turns",
        json={"user_message": "Hello"},
    )
    assert res_turn.status_code == 404
    assert "not found" in res_turn.json()["detail"].lower()

    res_get = client.get("/api/v1/sessions/sim-missing")
    assert res_get.status_code == 404


def test_stream_session_sse() -> None:
    """Verify Server-Sent Events stream for an active session."""
    client = get_test_client()

    create_res = client.post("/api/v1/sessions", json={"control_code": "6.1.2"})
    session_id = create_res.json()["session_id"]

    stream_res = client.get(f"/api/v1/sessions/{session_id}/stream")
    assert stream_res.status_code == 200
    assert "text/event-stream" in stream_res.headers["content-type"]
    assert "event: update" in stream_res.text
    assert session_id in stream_res.text

    # Missing session 404
    stream_404 = client.get("/api/v1/sessions/sim-invalid/stream")
    assert stream_404.status_code == 404


def test_sandbox_scenario_and_health_endpoints() -> None:
    """Verify scenario toggle and sandbox health check endpoints."""
    client = get_test_client()

    # Health
    health_res = client.get("/api/v1/sandbox/health")
    assert health_res.status_code == 200
    assert health_res.json()["healthy"] is True

    # Switch Scenario
    scenario_res = client.post(
        "/api/v1/sandbox/scenario",
        json={"scenario": "deficient_risk_owner"},
    )
    assert scenario_res.status_code == 200
    assert scenario_res.json()["status"] == "updated"
    assert scenario_res.json()["scenario"] == "deficient_risk_owner"


def test_serve_spa_index() -> None:
    """Verify GET / delivers the Single Page Application index HTML."""
    client = get_test_client()
    res = client.get("/")
    assert res.status_code == 200
    assert "ISO 27001:2022 Simulation Terminal" in res.text


def test_default_app_instantiation() -> None:
    """Verify create_app instantiates cleanly with default agent and sandbox."""
    default_app = create_app()
    client = TestClient(default_app)
    res = client.get("/api/v1/controls")
    assert res.status_code == 200


def test_scenario_switch_with_live_eramba() -> None:
    """Verify scenario switch gracefully skips when connected to live ErambaClientAdapter."""
    from grc_tool.adapters.sandbox.eramba_client import ErambaClientAdapter

    live_client = ErambaClientAdapter()
    app = create_app(sandbox=live_client)
    client = TestClient(app)
    res = client.post("/api/v1/sandbox/scenario", json={"scenario": "compliant"})
    assert res.status_code == 200
    assert res.json()["status"] == "skipped"


def test_session_response_with_finding() -> None:
    """Verify finding DTO mapping when session concludes."""
    client = get_test_client()
    create_res = client.post("/api/v1/sessions", json={"control_code": "6.1.2"})
    session_id = create_res.json()["session_id"]

    turn_res = client.post(
        f"/api/v1/sessions/{session_id}/turns",
        json={"user_message": "ready for audit, evaluate evidence"},
    )
    assert turn_res.status_code == 200
    data = turn_res.json()
    assert data["finding"] is not None
    assert data["finding"]["control_code"] == "6.1.2"
    assert data["finding"]["severity"] in [
        "major_non_conformity",
        "minor_non_conformity",
        "conformant",
    ]
