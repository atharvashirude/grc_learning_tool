"""Abstract port definition for ISO 27001 Audit & Coaching agent orchestration."""

from typing import Any, Protocol

from grc_tool.core.models.evidence import Evidence


class AuditAgentPort(Protocol):
    """Port defining interactions with the cognitive GRC auditor/coach agent."""

    def start_session(self, session_id: str, control_code: str) -> dict[str, Any]:
        """Initialize an audit session for a specific ISO control.

        Args:
            session_id: Unique thread identifier for session checkpointing.
            control_code: The standard clause or control under audit (e.g., '6.1.2').

        Returns:
            The initial state dictionary containing the auditor's opening statement.
        """
        ...

    def process_turn(
        self,
        session_id: str,
        user_message: str,
        evidence: list[Evidence] | None = None,
    ) -> dict[str, Any]:
        """Process a single conversational turn and optional evidence submission.

        Args:
            session_id: Unique thread identifier.
            user_message: Learner's textual response, question, or hint request.
            evidence: Optional list of objective evidence items submitted by the learner.

        Returns:
            Updated session state dictionary after graph execution.
        """
        ...

    def get_state(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve the current persistent state for a session.

        Args:
            session_id: Unique thread identifier.

        Returns:
            Current state dictionary, or None if the session does not exist.
        """
        ...
