"""Contract tests validating ErambaClientAdapter REST payloads and error handling."""

import httpx
import respx

from grc_tool.adapters.sandbox.eramba_client import ErambaClientAdapter
from grc_tool.core.models.evidence import EvidenceType


@respx.mock
def test_fetch_policy_success() -> None:
    """Verify ErambaClientAdapter correctly parses a 200 policy response into Evidence."""
    base_url = "http://eramba.test:8080"
    respx.get(f"{base_url}/api/v2/policies/POL-01").respond(
        status_code=200,
        json={
            "id": "POL-01",
            "title": "Information Security Policy",
            "approved": True,
            "owner": "ciso@company.local",
            "version": "2.1",
            "attributes": {"classification": "Confidential"},
        },
    )

    client = ErambaClientAdapter(base_url=base_url, api_token="test_token")
    evidence = client.fetch_policy("POL-01")

    assert evidence is not None
    assert evidence.evidence_id == "EV-ERAMBA-POL-POL-01"
    assert evidence.evidence_type == EvidenceType.POLICY_DOCUMENT
    assert evidence.source_system == "eramba"
    assert evidence.title == "Information Security Policy"
    assert evidence.payload["policy_approved"] is True
    assert evidence.payload["owner"] == "ciso@company.local"


@respx.mock
def test_fetch_policy_not_found() -> None:
    """Verify ErambaClientAdapter returns None when policy is 404."""
    base_url = "http://eramba.test:8080"
    respx.get(f"{base_url}/api/v2/policies/MISSING").respond(status_code=404)

    client = ErambaClientAdapter(base_url=base_url, api_token="test_token")
    assert client.fetch_policy("MISSING") is None


@respx.mock
def test_fetch_risk_register_contract() -> None:
    """Verify ErambaClientAdapter parses risk register array into Evidence models."""
    base_url = "http://eramba.test:8080"
    respx.get(f"{base_url}/api/v2/risks").respond(
        status_code=200,
        json=[
            {
                "id": "42",
                "title": "Unauthenticated API Exposure",
                "methodology_documented": True,
                "risk_owner_assigned": True,
                "risk_criteria_defined": True,
                "annual_review_completed": True,
                "likelihood": 4,
                "impact": 5,
            }
        ],
    )

    client = ErambaClientAdapter(base_url=base_url, api_token="test_token")
    risks = client.fetch_risk_register("6.1.2")

    assert len(risks) == 1
    r = risks[0]
    assert r.evidence_id == "EV-ERAMBA-RISK-42"
    assert r.evidence_type == EvidenceType.RISK_REGISTER_ENTRY
    assert r.payload["methodology_documented"] is True
    assert r.payload["risk_owner_assigned"] is True


@respx.mock
def test_fetch_technical_controls_contract() -> None:
    """Verify technical telemetry mapping for Annex A controls."""
    base_url = "http://eramba.test:8080"
    respx.get(f"{base_url}/api/v2/controls/A.5.15/telemetry").respond(
        status_code=200,
        json={
            "mfa_enforced": True,
            "policy_approved": True,
            "access_reviewed_recently": True,
        },
    )

    client = ErambaClientAdapter(base_url=base_url, api_token="test_token")
    telemetry = client.fetch_technical_controls("A.5.15")

    assert len(telemetry) == 1
    t = telemetry[0]
    assert t.evidence_type == EvidenceType.TECHNICAL_CONFIG
    assert t.payload["mfa_enforced"] is True


@respx.mock
def test_health_check_status() -> None:
    """Verify health check returns True on 200 and False on network error."""
    base_url = "http://eramba.test:8080"
    respx.get(f"{base_url}/api/v2/health").respond(status_code=200)

    client = ErambaClientAdapter(base_url=base_url, api_token="test_token")
    assert client.health_check() is True

    # Error cases
    respx.get(f"{base_url}/api/v2/health").respond(status_code=500)
    assert client.health_check() is False


@respx.mock
def test_eramba_client_network_error_resilience() -> None:
    """Verify client gracefully handles network timeouts and connection errors."""
    base_url = "http://eramba.test:8080"
    respx.get(f"{base_url}/api/v2/policies/POL-ERR").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )
    respx.get(f"{base_url}/api/v2/risks").mock(side_effect=httpx.TimeoutException("Timeout"))
    respx.get(f"{base_url}/api/v2/controls/A.5.15/telemetry").mock(
        side_effect=httpx.ConnectError("Connection failed")
    )
    respx.get(f"{base_url}/api/v2/health").mock(side_effect=httpx.ConnectError("Down"))

    client = ErambaClientAdapter(base_url=base_url, api_token="test_token")
    assert client.fetch_policy("POL-ERR") is None
    assert client.fetch_risk_register("6.1.2") == []
    assert client.fetch_technical_controls("A.5.15") == []
    assert client.health_check() is False
