"""Unit tests for the Deterministic Rubric Evaluator and criteria checks."""

from datetime import UTC, datetime

from grc_tool.core.evaluator.engine import DeterministicEvaluator
from grc_tool.core.evaluator.rubric import (
    AuditRubric,
    Criterion,
    get_standard_rubric,
)
from grc_tool.core.models.evidence import Evidence, EvidenceType
from grc_tool.core.models.finding import FindingSeverity


def test_rubric_creation() -> None:
    """Verify rubric composition and mandatory criteria counts."""
    rubric = AuditRubric(
        control_code="6.1.2",
        title="Risk Assessment Rubric",
        criteria=[
            Criterion(
                criterion_id="CRIT-1",
                description="A formal risk assessment methodology must be defined.",
                is_mandatory=True,
                required_field="methodology_documented",
            ),
            Criterion(
                criterion_id="CRIT-2",
                description="Risk owners must be assigned for all identified risks.",
                is_mandatory=True,
                required_field="risk_owner_assigned",
            ),
            Criterion(
                criterion_id="CRIT-3",
                description="Risk assessment conducted within the past 12 months.",
                is_mandatory=False,
                required_field="assessed_within_year",
            ),
        ],
    )
    assert rubric.control_code == "6.1.2"
    assert len(rubric.mandatory_criteria) == 2
    assert len(rubric.optional_criteria) == 1


def test_evaluator_all_criteria_met_conformant() -> None:
    """Verify that fulfilling all mandatory and optional criteria yields CONFORMANT."""
    rubric = get_standard_rubric("6.1.2")
    evidence = [
        Evidence(
            evidence_id="EV-101",
            evidence_type=EvidenceType.RISK_REGISTER_ENTRY,
            source_system="eramba",
            title="Enterprise Risk Assessment Register",
            payload={
                "methodology_documented": True,
                "risk_owner_assigned": True,
                "risk_criteria_defined": True,
                "annual_review_completed": True,
            },
            collected_at=datetime.now(UTC),
        )
    ]
    evaluator = DeterministicEvaluator()
    result = evaluator.evaluate(rubric=rubric, evidence_items=evidence)

    assert result.is_compliant
    assert result.finding.severity == FindingSeverity.CONFORMANT
    assert len(result.unmet_criteria) == 0


def test_evaluator_optional_criterion_missed_yields_ofi() -> None:
    """Verify that fulfilling mandatory criteria but missing an optional one yields OFI."""
    rubric = get_standard_rubric("6.1.2")
    evidence = [
        Evidence(
            evidence_id="EV-102",
            evidence_type=EvidenceType.RISK_REGISTER_ENTRY,
            source_system="eramba",
            title="Enterprise Risk Assessment Register",
            payload={
                "methodology_documented": True,
                "risk_owner_assigned": True,
                "risk_criteria_defined": True,
                "annual_review_completed": False,  # Optional recommendation missed
            },
            collected_at=datetime.now(UTC),
        )
    ]
    evaluator = DeterministicEvaluator()
    result = evaluator.evaluate(rubric=rubric, evidence_items=evidence)

    assert result.is_compliant
    assert result.finding.severity == FindingSeverity.OFI
    assert len(result.unmet_criteria) == 1
    assert not result.unmet_criteria[0].is_mandatory


def test_evaluator_mandatory_criterion_missed_yields_minor_nc() -> None:
    """Verify that missing one mandatory criterion while having partial evidence yields MINOR_NC."""
    rubric = get_standard_rubric("6.1.2")
    evidence = [
        Evidence(
            evidence_id="EV-103",
            evidence_type=EvidenceType.RISK_REGISTER_ENTRY,
            source_system="eramba",
            title="Partial Risk Assessment Register",
            payload={
                "methodology_documented": True,
                "risk_criteria_defined": True,
                "risk_owner_assigned": False,  # Missing mandatory risk owner
                "annual_review_completed": True,
            },
            collected_at=datetime.now(UTC),
        )
    ]
    evaluator = DeterministicEvaluator()
    result = evaluator.evaluate(rubric=rubric, evidence_items=evidence)

    assert not result.is_compliant
    assert result.finding.severity == FindingSeverity.MINOR_NC
    assert any(c.criterion_id == "6.1.2-C2" for c in result.unmet_criteria)
    assert result.finding.remediation_guidance is not None


def test_evaluator_total_absence_yields_major_nc() -> None:
    """Verify that missing all mandatory criteria or providing empty evidence yields MAJOR_NC."""
    rubric = get_standard_rubric("6.1.2")
    evaluator = DeterministicEvaluator()

    # Empty evidence provided
    result = evaluator.evaluate(rubric=rubric, evidence_items=[])

    assert not result.is_compliant
    assert result.finding.severity == FindingSeverity.MAJOR_NC
    assert len(result.unmet_criteria) == len(rubric.criteria)
    assert "absence" in result.finding.statement.lower()

    # Non-empty evidence provided, but all mandatory criteria fail
    irrelevant_evidence = [
        Evidence(
            evidence_id="EV-999",
            evidence_type=EvidenceType.AUDIT_LOG,
            source_system="wazuh",
            title="Irrelevant Log",
            payload={"unrelated_metric": 123},
            collected_at=datetime.now(UTC),
        )
    ]
    result_irrelevant = evaluator.evaluate(rubric=rubric, evidence_items=irrelevant_evidence)
    assert not result_irrelevant.is_compliant
    assert result_irrelevant.finding.severity == FindingSeverity.MAJOR_NC
    assert "systemic breakdown" in result_irrelevant.finding.statement.lower()


def test_rubric_without_required_field_auto_satisfied() -> None:
    """Verify criteria with no required_field are satisfied by evidence presence."""
    rubric = AuditRubric(
        control_code="TEST-01",
        title="Presence Rubric",
        criteria=[
            Criterion(
                criterion_id="CRIT-PRESENCE",
                description="Any evidence item must be presented.",
                is_mandatory=True,
                required_field=None,
            )
        ],
    )
    evidence = [
        Evidence(
            evidence_id="EV-100",
            evidence_type=EvidenceType.POLICY_DOCUMENT,
            source_system="eramba",
            title="Any Policy",
            payload={"exists": True},
            collected_at=datetime.now(UTC),
        )
    ]
    evaluator = DeterministicEvaluator()
    result = evaluator.evaluate(rubric=rubric, evidence_items=evidence)
    assert result.is_compliant
    assert result.finding.severity == FindingSeverity.CONFORMANT


def test_invalid_rubric_lookup() -> None:
    """Verify KeyError when requesting non-existent rubric."""
    import pytest

    with pytest.raises(KeyError, match="Rubric for control 'INVALID' not found"):
        get_standard_rubric("INVALID")
