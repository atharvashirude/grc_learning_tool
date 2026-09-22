"""Unit tests for the AuditFinding domain model and ISO 19011 classifications."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from grc_tool.core.models.finding import AuditFinding, FindingSeverity


def test_finding_severity_hierarchy() -> None:
    """Verify ISO 19011 severity ranking and ordering."""
    assert FindingSeverity.MAJOR_NC > FindingSeverity.MINOR_NC
    assert FindingSeverity.MAJOR_NC >= FindingSeverity.MAJOR_NC
    assert FindingSeverity.MINOR_NC < FindingSeverity.MAJOR_NC
    assert FindingSeverity.MINOR_NC <= FindingSeverity.MINOR_NC
    assert FindingSeverity.MINOR_NC > FindingSeverity.OFI
    assert FindingSeverity.OFI > FindingSeverity.CONFORMANT
    assert FindingSeverity.CONFORMANT <= FindingSeverity.OFI
    assert FindingSeverity.MAJOR_NC.is_non_conformity()
    assert FindingSeverity.MINOR_NC.is_non_conformity()
    assert not FindingSeverity.OFI.is_non_conformity()
    assert not FindingSeverity.CONFORMANT.is_non_conformity()

    # Invalid comparison types should return NotImplemented (TypeError in comparisons)
    with pytest.raises(TypeError):
        _ = FindingSeverity.MAJOR_NC > "invalid_string"
    with pytest.raises(TypeError):
        _ = FindingSeverity.MAJOR_NC >= 42
    with pytest.raises(TypeError):
        _ = FindingSeverity.MAJOR_NC < 3.14
    with pytest.raises(TypeError):
        _ = FindingSeverity.MAJOR_NC <= None


def test_conformant_finding_creation() -> None:
    """Verify creating a conformant audit finding."""
    now = datetime.now(UTC)
    finding = AuditFinding(
        finding_id="FND-001",
        control_code="A.5.15",
        severity=FindingSeverity.CONFORMANT,
        title="Access Control Requirements Satisfied",
        statement=(
            "Documented access control policy and MFA enforcement verified "
            "across all admin endpoints."
        ),
        evidence_ids=["EV-001", "EV-002"],
        created_at=now,
    )
    assert finding.finding_id == "FND-001"
    assert finding.severity == FindingSeverity.CONFORMANT
    assert len(finding.evidence_ids) == 2
    assert finding.remediation_guidance is None


def test_non_conformity_requires_remediation() -> None:
    """Verify that Major or Minor NCs must have non-empty remediation guidance."""
    with pytest.raises(ValidationError, match="Non-conformities must include remediation guidance"):
        AuditFinding(
            finding_id="FND-002",
            control_code="6.1.2",
            severity=FindingSeverity.MAJOR_NC,
            title="Absence of Risk Assessment Methodology",
            statement="No formal risk criteria or methodology documented.",
            evidence_ids=["EV-003"],
            remediation_guidance=None,
        )


def test_finding_immutability() -> None:
    """Verify audit findings cannot be tampered with after creation."""
    finding = AuditFinding(
        finding_id="FND-003",
        control_code="A.8.8",
        severity=FindingSeverity.MINOR_NC,
        title="Outdated Vulnerability Scan Frequency",
        statement="Scans conducted quarterly instead of monthly.",
        evidence_ids=["EV-004"],
        remediation_guidance="Update automated scan schedule in Wazuh to monthly intervals.",
    )
    with pytest.raises(ValidationError):
        finding.severity = FindingSeverity.CONFORMANT
