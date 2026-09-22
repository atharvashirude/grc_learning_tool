"""Audit rubric and evaluation criteria definitions."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Criterion(BaseModel):
    """An individual objective requirement that must be satisfied for compliance."""

    model_config = ConfigDict(frozen=True)

    criterion_id: str = Field(description="Unique identifier for the criterion")
    description: str = Field(description="Description of what is evaluated")
    is_mandatory: bool = Field(
        default=True,
        description="True if non-satisfaction causes a non-conformity; False if recommendation",
    )
    required_field: str | None = Field(
        default=None,
        description="Attribute or field expected in the evidence payload",
    )
    expected_value: Any = Field(
        default=True,
        description="Value expected for the field in the evidence payload",
    )


class AuditRubric(BaseModel):
    """Rubric defining the acceptance criteria for an ISO control."""

    model_config = ConfigDict(frozen=True)

    control_code: str = Field(description="ISO standard clause or control code, e.g. '6.1.2'")
    title: str = Field(description="Title of the rubric")
    criteria: list[Criterion] = Field(description="Ordered list of criteria to evaluate")
    minimum_conformant_score: float = Field(
        default=1.0, description="Minimum ratio of satisfied criteria needed for full compliance"
    )

    @property
    def mandatory_criteria(self) -> list[Criterion]:
        """List of non-negotiable mandatory criteria."""
        return [c for c in self.criteria if c.is_mandatory]

    @property
    def optional_criteria(self) -> list[Criterion]:
        """List of optional / best-practice criteria."""
        return [c for c in self.criteria if not c.is_mandatory]


STANDARD_RUBRICS_REGISTRY: dict[str, AuditRubric] = {
    "6.1.2": AuditRubric(
        control_code="6.1.2",
        title="Information Security Risk Assessment Rubric",
        criteria=[
            Criterion(
                criterion_id="6.1.2-C1",
                description="A formal risk assessment methodology must be defined.",
                is_mandatory=True,
                required_field="methodology_documented",
            ),
            Criterion(
                criterion_id="6.1.2-C2",
                description="Risk owners must be assigned for all identified risks.",
                is_mandatory=True,
                required_field="risk_owner_assigned",
            ),
            Criterion(
                criterion_id="6.1.2-C3",
                description="Risk acceptance and assessment criteria must be defined.",
                is_mandatory=True,
                required_field="risk_criteria_defined",
            ),
            Criterion(
                criterion_id="6.1.2-C4",
                description="Annual review or update of the risk assessment must be completed.",
                is_mandatory=False,
                required_field="annual_review_completed",
            ),
        ],
    ),
    "A.5.15": AuditRubric(
        control_code="A.5.15",
        title="Access Control Rubric",
        criteria=[
            Criterion(
                criterion_id="A.5.15-C1",
                description="Formal access control policy documented and approved.",
                is_mandatory=True,
                required_field="policy_approved",
            ),
            Criterion(
                criterion_id="A.5.15-C2",
                description=(
                    "Multi-factor authentication (MFA) enforced on all administrative access."
                ),
                is_mandatory=True,
                required_field="mfa_enforced",
            ),
            Criterion(
                criterion_id="A.5.15-C3",
                description="Periodic access rights review conducted at least semi-annually.",
                is_mandatory=False,
                required_field="access_reviewed_recently",
            ),
        ],
    ),
}


def get_standard_rubric(control_code: str) -> AuditRubric:
    """Retrieve standard rubric for an ISO control.

    Raises:
        KeyError: If no rubric exists for the specified control code.
    """
    if control_code not in STANDARD_RUBRICS_REGISTRY:
        raise KeyError(f"Rubric for control '{control_code}' not found in registry")
    return STANDARD_RUBRICS_REGISTRY[control_code]
