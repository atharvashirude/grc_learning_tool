"""Unit tests for the Evidence domain model and validation rules."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from grc_tool.core.models.evidence import Evidence, EvidenceType


def test_valid_evidence_creation() -> None:
    """Verify standard instantiation of an Evidence entity."""
    now = datetime.now(UTC)
    ev = Evidence(
        evidence_id="EV-001",
        evidence_type=EvidenceType.POLICY_DOCUMENT,
        source_system="eramba",
        title="Information Security Policy v2.1",
        payload={
            "document_id": "POL-01",
            "owner": "ciso@company.local",
            "approved": True,
            "version": "2.1",
        },
        collected_at=now,
        metadata={"reviewer": "internal_auditor"},
    )
    assert ev.evidence_id == "EV-001"
    assert ev.evidence_type == EvidenceType.POLICY_DOCUMENT
    assert ev.source_system == "eramba"
    assert ev.payload["owner"] == "ciso@company.local"
    assert ev.payload["approved"] is True
    assert ev.collected_at == now


def test_evidence_immutability() -> None:
    """Verify that Evidence models are immutable once created."""
    ev = Evidence(
        evidence_id="EV-002",
        evidence_type=EvidenceType.TECHNICAL_CONFIG,
        source_system="wazuh",
        title="Password Complexity Policy Config",
        payload={"min_length": 14, "require_mfa": True},
        collected_at=datetime.now(UTC),
    )
    with pytest.raises(ValidationError):
        ev.title = "Tampered Title"


def test_evidence_requires_non_empty_payload() -> None:
    """Verify that evidence with an empty payload is rejected."""
    with pytest.raises(ValidationError, match="Evidence payload must not be empty"):
        Evidence(
            evidence_id="EV-003",
            evidence_type=EvidenceType.AUDIT_LOG,
            source_system="wazuh",
            title="Empty Audit Log",
            payload={},
            collected_at=datetime.now(UTC),
        )


def test_evidence_payload_lookup_helper() -> None:
    """Verify safe attribute extraction helper method on evidence."""
    ev = Evidence(
        evidence_id="EV-004",
        evidence_type=EvidenceType.RISK_REGISTER_ENTRY,
        source_system="eramba",
        title="Unpatched Edge Firewall Risk",
        payload={
            "risk_id": "RSK-042",
            "likelihood": 4,
            "impact": 5,
            "risk_owner": "secops_lead",
            "treatment": "Mitigate via patching within 48h",
        },
        collected_at=datetime.now(UTC),
    )
    assert ev.get_field("risk_id") == "RSK-042"
    assert ev.get_field("likelihood") == 4
    assert ev.get_field("missing_key", default="fallback") == "fallback"
