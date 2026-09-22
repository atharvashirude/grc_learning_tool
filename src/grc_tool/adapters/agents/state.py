"""State schema and reducers for the LangGraph audit orchestration engine."""

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from grc_tool.core.evaluator.engine import EvaluationResult
from grc_tool.core.models.evidence import Evidence
from grc_tool.core.models.finding import AuditFinding


def append_unique_evidence(current: list[Evidence], new_items: list[Evidence]) -> list[Evidence]:
    """Reducer that appends new evidence while preserving uniqueness by evidence_id."""
    if not new_items:
        return current
    seen_ids = {e.evidence_id for e in current}
    updated = list(current)
    for item in new_items:
        if item.evidence_id not in seen_ids:
            updated.append(item)
            seen_ids.add(item.evidence_id)
    return updated


class AuditGraphState(TypedDict):
    """Persistent cognitive state across multi-turn audit and coaching interactions."""

    session_id: str
    control_code: str
    messages: Annotated[list[BaseMessage], add_messages]
    collected_evidence: Annotated[list[Evidence], append_unique_evidence]
    evaluation_result: EvaluationResult | None
    finding: AuditFinding | None
    phase: str  # "INITIALIZING", "INQUIRY", "COACHING", "EVALUATING", "CONCLUDED"
    status: str  # "ACTIVE", "CONCLUDED"
