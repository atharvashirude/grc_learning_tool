"""Eramba Community Edition REST API client adapter implementing SandboxPort."""

from datetime import UTC, datetime
from typing import Any

import httpx

from grc_tool.application.ports.sandbox import SandboxPort
from grc_tool.core.models.evidence import Evidence, EvidenceType


class ErambaClientAdapter(SandboxPort):
    """Production-grade REST client for inspecting an Eramba GRC instance."""

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        api_token: str | None = None,
        timeout: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token or ""
        self.timeout = timeout
        self._client = client or httpx.Client(timeout=self.timeout)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
            "User-Agent": "GRC-Learning-Tool/0.1.0",
        }

    def fetch_policy(self, policy_id: str) -> Evidence | None:
        """Fetch policy document from Eramba policy repository."""
        url = f"{self.base_url}/api/v2/policies/{policy_id}"
        try:
            response = self._client.get(url, headers=self._headers())
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()

            return Evidence(
                evidence_id=f"EV-ERAMBA-POL-{policy_id}",
                evidence_type=EvidenceType.POLICY_DOCUMENT,
                source_system="eramba",
                title=str(data.get("title", f"Policy {policy_id}")),
                payload={
                    "policy_id": policy_id,
                    "policy_approved": bool(data.get("approved", False)),
                    "owner": data.get("owner", "unassigned"),
                    "version": data.get("version", "1.0"),
                    "raw_attributes": data.get("attributes", {}),
                },
                collected_at=datetime.now(UTC),
            )
        except httpx.HTTPError:
            return None

    def fetch_risk_register(self, control_code: str) -> list[Evidence]:
        """Fetch risk records mapped to a target ISO control code."""
        url = f"{self.base_url}/api/v2/risks"
        try:
            response = self._client.get(
                url, headers=self._headers(), params={"control": control_code}
            )
            response.raise_for_status()
            data = response.json()
            items: list[dict[str, Any]] = data if isinstance(data, list) else data.get("items", [])

            results: list[Evidence] = []
            for item in items:
                r_id = str(item.get("id", "0"))
                results.append(
                    Evidence(
                        evidence_id=f"EV-ERAMBA-RISK-{r_id}",
                        evidence_type=EvidenceType.RISK_REGISTER_ENTRY,
                        source_system="eramba",
                        title=str(item.get("title", f"Risk {r_id}")),
                        payload={
                            "methodology_documented": bool(
                                item.get("methodology_documented", False)
                            ),
                            "risk_owner_assigned": bool(item.get("risk_owner_assigned", False)),
                            "risk_criteria_defined": bool(item.get("risk_criteria_defined", False)),
                            "annual_review_completed": bool(
                                item.get("annual_review_completed", False)
                            ),
                            "likelihood": item.get("likelihood", 1),
                            "impact": item.get("impact", 1),
                        },
                        collected_at=datetime.now(UTC),
                    )
                )
            return results
        except httpx.HTTPError:
            return []

    def fetch_technical_controls(self, control_code: str) -> list[Evidence]:
        """Fetch technical configuration verification records."""
        url = f"{self.base_url}/api/v2/controls/{control_code}/telemetry"
        try:
            response = self._client.get(url, headers=self._headers())
            response.raise_for_status()
            data = response.json()

            return [
                Evidence(
                    evidence_id=f"EV-ERAMBA-TECH-{control_code}",
                    evidence_type=EvidenceType.TECHNICAL_CONFIG,
                    source_system="eramba",
                    title=f"Technical Verification for {control_code}",
                    payload={
                        "mfa_enforced": bool(data.get("mfa_enforced", False)),
                        "policy_approved": bool(data.get("policy_approved", False)),
                        "access_reviewed_recently": bool(
                            data.get("access_reviewed_recently", False)
                        ),
                    },
                    collected_at=datetime.now(UTC),
                )
            ]
        except httpx.HTTPError:
            return []

    def health_check(self) -> bool:
        """Check if Eramba target is operational and reachable."""
        url = f"{self.base_url}/api/v2/health"
        try:
            response = self._client.get(url, headers=self._headers())
            return response.status_code == 200
        except httpx.HTTPError:
            return False
