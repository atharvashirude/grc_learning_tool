"""Unit tests for ISO 27001:2022 domain models and control registry."""

import pytest
from pydantic import ValidationError

from grc_tool.core.models.iso_standard import (
    AnnexATheme,
    ISOControl,
    StandardClause,
    get_control,
    list_controls,
)


def test_iso_control_creation_clause() -> None:
    """Verify ISOControl instantiation for an ISMS management clause."""
    control = ISOControl(
        code="6.1.2",
        title="Information security risk assessment",
        statement=(
            "The organization shall define and apply an information security risk "
            "assessment process."
        ),
        clause=StandardClause.CLAUSE_6_PLANNING,
        is_annex_a=False,
    )
    assert control.code == "6.1.2"
    assert control.clause == StandardClause.CLAUSE_6_PLANNING
    assert control.theme is None
    assert not control.is_annex_a


def test_iso_control_creation_annex_a() -> None:
    """Verify ISOControl instantiation for an Annex A 2022 control."""
    control = ISOControl(
        code="A.5.15",
        title="Access control",
        statement=(
            "Rules to control physical and logical access shall be established " "and implemented."
        ),
        theme=AnnexATheme.ORGANIZATIONAL,
        is_annex_a=True,
    )
    assert control.code == "A.5.15"
    assert control.theme == AnnexATheme.ORGANIZATIONAL
    assert control.clause is None
    assert control.is_annex_a


def test_iso_control_immutability() -> None:
    """Verify that ISOControl instances are frozen/immutable to prevent domain drift."""
    control = ISOControl(
        code="A.8.8",
        title="Management of technical vulnerabilities",
        statement="Information about technical vulnerabilities shall be obtained.",
        theme=AnnexATheme.TECHNOLOGICAL,
        is_annex_a=True,
    )
    with pytest.raises(ValidationError):
        control.title = "Altered Title"


def test_iso_control_validation_rules() -> None:
    """Verify validation: Annex A must have a theme; Clauses must have a clause."""
    # Annex A without theme must fail validation
    with pytest.raises(ValidationError, match="Annex A controls must specify an AnnexATheme"):
        ISOControl(
            code="A.5.1",
            title="Policies for information security",
            statement="Policies shall be defined.",
            is_annex_a=True,
            theme=None,
        )

    # Clause without clause category must fail validation
    with pytest.raises(ValidationError, match="Non-Annex A controls must specify a StandardClause"):
        ISOControl(
            code="4.1",
            title="Understanding the organization",
            statement="Determine external and internal issues.",
            is_annex_a=False,
            clause=None,
        )


def test_standard_controls_registry_lookup() -> None:
    """Verify retrieving controls from the standard registry."""
    risk_ctrl = get_control("6.1.2")
    assert risk_ctrl.code == "6.1.2"
    assert risk_ctrl.title == "Information security risk assessment"

    access_ctrl = get_control("A.5.15")
    assert access_ctrl.code == "A.5.15"
    assert access_ctrl.theme == AnnexATheme.ORGANIZATIONAL

    vuln_ctrl = get_control("A.8.8")
    assert vuln_ctrl.code == "A.8.8"
    assert vuln_ctrl.theme == AnnexATheme.TECHNOLOGICAL

    with pytest.raises(KeyError, match="Control with code 'INVALID.99' not found in registry"):
        get_control("INVALID.99")


def test_list_controls_filtering() -> None:
    """Verify filtering controls by Annex A flag or theme."""
    all_controls = list_controls()
    assert len(all_controls) >= 5

    annex_a_only = list_controls(annex_a_only=True)
    assert all(c.is_annex_a for c in annex_a_only)

    clauses_only = list_controls(clauses_only=True)
    assert all(not c.is_annex_a for c in clauses_only)
