"""Mock sandbox adapter for deterministic local simulations and CI/CD testing."""

from datetime import UTC, datetime
from enum import Enum

from grc_tool.application.ports.sandbox import SandboxPort
from grc_tool.core.models.evidence import Evidence, EvidenceType


class ScenarioMode(str, Enum):
    """Pre-configured simulation scenarios for ISO 27001 auditing."""

    COMPLIANT = "compliant"
    DEFICIENT_RISK_OWNER = "deficient_risk_owner"
    MISSING_MFA = "missing_mfa"
    EMPTY = "empty"


class MockSandboxAdapter(SandboxPort):
    """Deterministic in-memory sandbox simulating target GRC systems."""

    def __init__(self, initial_scenario: ScenarioMode = ScenarioMode.COMPLIANT) -> None:
        self.scenario = initial_scenario
        self.custom_evidence: list[Evidence] = []
        self.is_healthy: bool = True

    def set_scenario(self, scenario: ScenarioMode) -> None:
        """Switch simulation scenario state."""
        self.scenario = scenario

    def add_custom_evidence(self, evidence: Evidence) -> None:
        """Inject custom evidence artifact into mock repository."""
        self.custom_evidence.append(evidence)

    def fetch_policy(self, policy_id: str) -> Evidence | None:
        """Retrieve policy artifact based on current scenario."""
        if self.scenario == ScenarioMode.EMPTY:
            return None

        for ev in self.custom_evidence:
            if (
                ev.evidence_type == EvidenceType.POLICY_DOCUMENT
                and ev.payload.get("policy_id") == policy_id
            ):
                return ev

        is_approved = self.scenario != ScenarioMode.MISSING_MFA
        return Evidence(
            evidence_id=f"MOCK-POL-{policy_id}",
            evidence_type=EvidenceType.POLICY_DOCUMENT,
            source_system="mock_eramba",
            title=f"Access Control Policy ({policy_id})",
            payload={
                "policy_id": policy_id,
                "policy_approved": is_approved,
                "owner": "ciso@company.local",
                "version": "2.0",
            },
            collected_at=datetime.now(UTC),
        )

    def fetch_risk_register(self, control_code: str) -> list[Evidence]:
        """Retrieve risk register records based on current scenario."""
        if self.scenario == ScenarioMode.EMPTY:
            return []

        custom = [
            ev
            for ev in self.custom_evidence
            if ev.evidence_type == EvidenceType.RISK_REGISTER_ENTRY
        ]
        if custom:
            return custom

        if self.scenario == ScenarioMode.DEFICIENT_RISK_OWNER:
            return [
                Evidence(
                    evidence_id="MOCK-RISK-01",
                    evidence_type=EvidenceType.RISK_REGISTER_ENTRY,
                    source_system="mock_eramba",
                    title="Deficient Risk Assessment Record",
                    payload={
                        "methodology_documented": True,
                        "risk_criteria_defined": True,
                        "risk_owner_assigned": False,  # Deficient
                        "annual_review_completed": True,
                    },
                    collected_at=datetime.now(UTC),
                )
            ]

        # Default compliant
        return [
            Evidence(
                evidence_id="MOCK-RISK-01",
                evidence_type=EvidenceType.RISK_REGISTER_ENTRY,
                source_system="mock_eramba",
                title="Compliant Risk Assessment Record",
                payload={
                    "methodology_documented": True,
                    "risk_criteria_defined": True,
                    "risk_owner_assigned": True,
                    "annual_review_completed": True,
                },
                collected_at=datetime.now(UTC),
            )
        ]

    def fetch_technical_controls(self, control_code: str) -> list[Evidence]:
        """Retrieve technical verification telemetry based on scenario."""
        if self.scenario == ScenarioMode.EMPTY:
            return []

        mfa_enabled = self.scenario != ScenarioMode.MISSING_MFA
        return [
            Evidence(
                evidence_id=f"MOCK-TECH-{control_code}",
                evidence_type=EvidenceType.TECHNICAL_CONFIG,
                source_system="mock_wazuh",
                title=f"Technical Verification for {control_code}",
                payload={
                    "mfa_enforced": mfa_enabled,
                    "policy_approved": True,
                    "access_reviewed_recently": True,
                },
                collected_at=datetime.now(UTC),
            )
        ]

    def health_check(self) -> bool:
        """Return operational status."""
        return self.is_healthy
