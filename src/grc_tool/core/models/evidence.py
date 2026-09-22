"""Evidence domain model for GRC simulations and audit evaluation."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvidenceType(str, Enum):
    """Categorization of audit evidence artifacts."""

    POLICY_DOCUMENT = "policy_document"
    TECHNICAL_CONFIG = "technical_config"
    AUDIT_LOG = "audit_log"
    INTERVIEW_TRANSCRIPT = "interview_transcript"
    RISK_REGISTER_ENTRY = "risk_register_entry"


class Evidence(BaseModel):
    """Immutable audit evidence artifact gathered from simulated or external systems."""

    model_config = ConfigDict(frozen=True)

    evidence_id: str = Field(description="Unique identifier for the evidence artifact")
    evidence_type: EvidenceType = Field(description="Classification of evidence")
    source_system: str = Field(
        description="Originating system or component (e.g., 'eramba', 'wazuh', 'interview')"
    )
    title: str = Field(description="Descriptive title of the evidence artifact")
    payload: dict[str, Any] = Field(description="Structured evidence payload / state inspection")
    collected_at: datetime = Field(description="UTC timestamp when evidence was retrieved")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Supplementary contextual attributes"
    )

    @field_validator("payload")
    @classmethod
    def validate_payload_non_empty(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Ensure evidence contains actual content."""
        if not value:
            raise ValueError("Evidence payload must not be empty")
        return value

    def get_field(self, key: str, default: Any = None) -> Any:
        """Safely retrieve a field value from the evidence payload."""
        return self.payload.get(key, default)
