"""LangChain inspection tools bridging the LangGraph auditor agent to the sandbox."""

from langchain_core.tools import BaseTool, tool

from grc_tool.application.ports.sandbox import SandboxPort


def create_sandbox_inspection_tools(sandbox: SandboxPort) -> list[BaseTool]:
    """Create a suite of inspection tools wired to a target SandboxPort."""

    @tool
    def inspect_policy_repository(policy_id: str) -> str:
        """Inspect the GRC policy repository to verify if a policy exists and is approved."""
        evidence = sandbox.fetch_policy(policy_id)
        if not evidence:
            return f"Policy '{policy_id}' was not found in the policy repository."

        payload = evidence.payload
        approved = payload.get("policy_approved", False)
        owner = payload.get("owner", "unknown")
        version = payload.get("version", "unknown")
        status_text = "APPROVED" if approved else "DRAFT / UNAPPROVED"
        return (
            f"Policy '{policy_id}' retrieved from {evidence.source_system}. "
            f"Title: {evidence.title}. Status: {status_text}. Owner: {owner}. Version: {version}."
        )

    @tool
    def inspect_risk_register(control_code: str = "6.1.2") -> str:
        """Inspect the GRC risk register to verify risk assessments, criteria, and owners."""
        records = sandbox.fetch_risk_register(control_code)
        if not records:
            return f"No risk register records found for control '{control_code}'."

        summaries: list[str] = []
        for rec in records:
            p = rec.payload
            has_methodology = p.get("methodology_documented", False)
            has_owner = p.get("risk_owner_assigned", False)
            has_criteria = p.get("risk_criteria_defined", False)
            summaries.append(
                f"[{rec.title}] Methodology: {has_methodology}, "
                f"Owner Assigned: {has_owner}, Criteria Defined: {has_criteria}"
            )
        return (
            f"Retrieved {len(records)} risk assessment record(s) from {records[0].source_system}: "
            + "; ".join(summaries)
        )

    @tool
    def inspect_technical_controls(control_code: str = "A.5.15") -> str:
        """Inspect system configuration telemetry to verify technical security controls (MFA)."""
        records = sandbox.fetch_technical_controls(control_code)
        if not records:
            return f"No technical configuration telemetry available for control '{control_code}'."

        p = records[0].payload
        mfa = "ENFORCED" if p.get("mfa_enforced", False) else "DISABLED / MISSING"
        policy = "APPROVED" if p.get("policy_approved", False) else "NOT APPROVED"
        review = "COMPLETED" if p.get("access_reviewed_recently", False) else "OVERDUE"
        return (
            f"Technical Telemetry for {control_code} ({records[0].source_system}): "
            f"MFA: {mfa}, Access Policy: {policy}, Periodic Review: {review}."
        )

    return [
        inspect_policy_repository,
        inspect_risk_register,
        inspect_technical_controls,
    ]
