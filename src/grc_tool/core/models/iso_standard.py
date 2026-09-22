"""ISO/IEC 27001:2022 domain models and standards registry."""

from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StandardClause(str, Enum):
    """ISO/IEC 27001:2022 Management System Clauses (Clauses 4 through 10)."""

    CLAUSE_4_CONTEXT = "Clause 4: Context of the organization"
    CLAUSE_5_LEADERSHIP = "Clause 5: Leadership"
    CLAUSE_6_PLANNING = "Clause 6: Planning"
    CLAUSE_7_SUPPORT = "Clause 7: Support"
    CLAUSE_8_OPERATION = "Clause 8: Operation"
    CLAUSE_9_PERFORMANCE = "Clause 9: Performance evaluation"
    CLAUSE_10_IMPROVEMENT = "Clause 10: Improvement"


class AnnexATheme(str, Enum):
    """ISO/IEC 27001:2022 Annex A Consolidated Control Themes."""

    ORGANIZATIONAL = "Theme 5: Organizational controls"
    PEOPLE = "Theme 6: People controls"
    PHYSICAL = "Theme 7: Physical controls"
    TECHNOLOGICAL = "Theme 8: Technological controls"


class ISOControl(BaseModel):
    """Specification of an ISO/IEC 27001 requirement or Annex A control."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(description="Unique standard identifier, e.g., '6.1.2' or 'A.5.15'")
    title: str = Field(description="Official title of the clause or control")
    statement: str = Field(description="Normative requirement or control statement")
    is_annex_a: bool = Field(
        default=False, description="True if Annex A control; False if ISMS management clause"
    )
    theme: AnnexATheme | None = Field(
        default=None, description="Annex A theme (mandatory if is_annex_a=True)"
    )
    clause: StandardClause | None = Field(
        default=None, description="ISMS Clause category (mandatory if is_annex_a=False)"
    )

    @model_validator(mode="after")
    def validate_theme_or_clause(self) -> Self:
        """Enforce standard classification integrity."""
        if self.is_annex_a and self.theme is None:
            raise ValueError("Annex A controls must specify an AnnexATheme")
        if not self.is_annex_a and self.clause is None:
            raise ValueError("Non-Annex A controls must specify a StandardClause")
        return self


# Pre-populated registry for Milestone 1 focal controls
STANDARD_CONTROLS_REGISTRY: dict[str, ISOControl] = {
    "6.1.2": ISOControl(
        code="6.1.2",
        title="Information security risk assessment",
        statement=(
            "The organization shall define and apply an information security risk assessment "
            "process that establishes and maintains information security risk criteria, produces "
            "consistent, valid and comparable results, and identifies information security risks."
        ),
        is_annex_a=False,
        clause=StandardClause.CLAUSE_6_PLANNING,
    ),
    "6.1.3": ISOControl(
        code="6.1.3",
        title="Information security risk treatment",
        statement=(
            "The organization shall define and apply an information security risk treatment "
            "process to select appropriate information security risk treatment options."
        ),
        is_annex_a=False,
        clause=StandardClause.CLAUSE_6_PLANNING,
    ),
    "9.2": ISOControl(
        code="9.2",
        title="Internal audit",
        statement=(
            "The organization shall conduct internal audits at planned intervals to provide "
            "information on whether the information security management system conforms to "
            "the organization's own requirements and the requirements of this document."
        ),
        is_annex_a=False,
        clause=StandardClause.CLAUSE_9_PERFORMANCE,
    ),
    "A.5.15": ISOControl(
        code="A.5.15",
        title="Access control",
        statement=(
            "Rules to control physical and logical access to information and other associated "
            "assets shall be established and implemented based on business and information "
            "security requirements."
        ),
        is_annex_a=True,
        theme=AnnexATheme.ORGANIZATIONAL,
    ),
    "A.8.8": ISOControl(
        code="A.8.8",
        title="Management of technical vulnerabilities",
        statement=(
            "Information about technical vulnerabilities of information systems in use shall "
            "be obtained, the organization's exposure to such vulnerabilities evaluated and "
            "appropriate measures taken to address the associated risk."
        ),
        is_annex_a=True,
        theme=AnnexATheme.TECHNOLOGICAL,
    ),
    "A.8.15": ISOControl(
        code="A.8.15",
        title="Logging",
        statement=(
            "Logs that record activities, exceptions, faults and other relevant events shall "
            "be produced, kept, protected and analyzed."
        ),
        is_annex_a=True,
        theme=AnnexATheme.TECHNOLOGICAL,
    ),
}


def get_control(code: str) -> ISOControl:
    """Retrieve an ISOControl by standard code identifier.

    Raises:
        KeyError: If the control code is not present in the registry.
    """
    if code not in STANDARD_CONTROLS_REGISTRY:
        raise KeyError(f"Control with code '{code}' not found in registry")
    return STANDARD_CONTROLS_REGISTRY[code]


def list_controls(annex_a_only: bool = False, clauses_only: bool = False) -> list[ISOControl]:
    """List registered ISO controls with optional filtering."""
    controls = list(STANDARD_CONTROLS_REGISTRY.values())
    if annex_a_only:
        return [c for c in controls if c.is_annex_a]
    if clauses_only:
        return [c for c in controls if not c.is_annex_a]
    return controls
