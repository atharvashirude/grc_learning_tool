"""Audit finding domain models and ISO 19011 severity classifications."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FindingSeverity(str, Enum):
    """ISO 19011 / ISO 27001 audit finding classification levels."""

    MAJOR_NC = "major_non_conformity"
    MINOR_NC = "minor_non_conformity"
    OFI = "opportunity_for_improvement"
    CONFORMANT = "conformant"

    @property
    def _rank(self) -> int:
        ranks = {
            FindingSeverity.MAJOR_NC: 4,
            FindingSeverity.MINOR_NC: 3,
            FindingSeverity.OFI: 2,
            FindingSeverity.CONFORMANT: 1,
        }
        return ranks[self]

    def _type_error(self, op: str, other: Any) -> TypeError:
        return TypeError(
            f"'{op}' not supported between '{self.__class__.__name__}' and '{type(other).__name__}'"
        )

    def __gt__(self, other: Any) -> bool:
        if not isinstance(other, FindingSeverity):
            raise self._type_error(">", other)
        return self._rank > other._rank

    def __ge__(self, other: Any) -> bool:
        if not isinstance(other, FindingSeverity):
            raise self._type_error(">=", other)
        return self._rank >= other._rank

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, FindingSeverity):
            raise self._type_error("<", other)
        return self._rank < other._rank

    def __le__(self, other: Any) -> bool:
        if not isinstance(other, FindingSeverity):
            raise self._type_error("<=", other)
        return self._rank <= other._rank

    def is_non_conformity(self) -> bool:
        """Return True if severity represents a formal non-conformity."""
        return self in (FindingSeverity.MAJOR_NC, FindingSeverity.MINOR_NC)


class AuditFinding(BaseModel):
    """Immutable finding rendered by an audit evaluation against an ISO control."""

    model_config = ConfigDict(frozen=True)

    finding_id: str = Field(description="Unique identifier for the audit finding")
    control_code: str = Field(description="ISO standard clause or control code, e.g. '6.1.2'")
    severity: FindingSeverity = Field(description="Severity classification level")
    title: str = Field(description="Short summary of the finding")
    statement: str = Field(description="Formal audit statement citing requirements and facts")
    evidence_ids: list[str] = Field(
        default_factory=list, description="IDs of evidence supporting this finding"
    )
    remediation_guidance: str | None = Field(
        default=None, description="Actionable corrective advice (mandatory for non-conformities)"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC creation timestamp",
    )

    @model_validator(mode="after")
    def validate_remediation(self) -> Self:
        """Enforce that all non-conformities include corrective remediation guidance."""
        if self.severity.is_non_conformity() and not self.remediation_guidance:
            raise ValueError("Non-conformities must include remediation guidance")
        return self
