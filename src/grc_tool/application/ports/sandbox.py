"""Abstract port definition for target GRC and security simulation environments."""

from typing import Protocol

from grc_tool.core.models.evidence import Evidence


class SandboxPort(Protocol):
    """Port defining interaction capabilities with external or simulated GRC targets."""

    def fetch_policy(self, policy_id: str) -> Evidence | None:
        """Retrieve a specific policy document artifact from the target GRC tool.

        Args:
            policy_id: Unique identifier for the policy in the target system.

        Returns:
            Evidence entity containing policy attributes, or None if not found.
        """
        ...

    def fetch_risk_register(self, control_code: str) -> list[Evidence]:
        """Query the target GRC system for risk register records relating to a control.

        Args:
            control_code: ISO standard clause or control identifier (e.g. '6.1.2').

        Returns:
            List of Evidence entities representing risk assessment entries.
        """
        ...

    def fetch_technical_controls(self, control_code: str) -> list[Evidence]:
        """Query target system configurations or security telemetry for technical controls.

        Args:
            control_code: ISO standard clause or control identifier (e.g. 'A.5.15').

        Returns:
            List of Evidence entities representing verified technical configurations.
        """
        ...

    def health_check(self) -> bool:
        """Verify connectivity and operational status of the target sandbox.

        Returns:
            True if healthy and reachable; False otherwise.
        """
        ...
