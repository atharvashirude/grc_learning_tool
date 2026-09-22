"""LangGraph state machine implementation for ISO 27001 Lead Auditor and GRC Coach."""

from collections.abc import Callable
from typing import Any, Literal, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from grc_tool.adapters.agents.prompts import (
    COACH_SYSTEM_PROMPT,
    LEAD_AUDITOR_SYSTEM_PROMPT,
)
from grc_tool.adapters.agents.state import AuditGraphState
from grc_tool.application.ports.agent import AuditAgentPort
from grc_tool.core.evaluator.engine import DeterministicEvaluator
from grc_tool.core.evaluator.rubric import get_standard_rubric
from grc_tool.core.models.evidence import Evidence
from grc_tool.core.models.iso_standard import get_control


def route_user_turn(
    state: AuditGraphState,
) -> Literal["auditor", "coach", "evaluator"]:
    """Route user turn to appropriate node based on intent detection."""
    if not state.get("messages"):
        return "auditor"

    last_msg = state["messages"][-1]
    text = last_msg.content if isinstance(last_msg.content, str) else str(last_msg.content)
    lowered = text.lower()

    # Hint / coaching request triggers
    coach_triggers = {
        "hint",
        "help",
        "coach",
        "stuck",
        "guidance",
        "what should i do",
    }
    if any(trigger in lowered for trigger in coach_triggers):
        return "coach"

    # Evaluation / conclusion triggers
    eval_triggers = {
        "evaluate",
        "ready for audit",
        "conclude audit",
        "finish audit",
        "render finding",
        "submit evidence",
    }
    if any(trigger in lowered for trigger in eval_triggers):
        return "evaluator"

    return "auditor"


def create_auditor_node(
    llm: BaseChatModel,
) -> Callable[[AuditGraphState], dict[str, Any]]:
    """Factory creating the Lead Auditor interrogation node."""

    def auditor_node(state: AuditGraphState) -> dict[str, Any]:
        control = get_control(state["control_code"])
        system_prompt = LEAD_AUDITOR_SYSTEM_PROMPT.format(
            control_code=control.code,
            control_title=control.title,
            control_statement=control.statement,
        )
        conversation: list[BaseMessage] = [SystemMessage(content=system_prompt)]
        conversation.extend(state["messages"])
        response = llm.invoke(conversation)
        return {
            "messages": [response],
            "phase": "INQUIRY",
            "status": "ACTIVE",
        }

    return auditor_node


def create_coach_node(
    llm: BaseChatModel,
) -> Callable[[AuditGraphState], dict[str, Any]]:
    """Factory creating the Socratic GRC Coach tutor node."""

    def coach_node(state: AuditGraphState) -> dict[str, Any]:
        control = get_control(state["control_code"])
        system_prompt = COACH_SYSTEM_PROMPT.format(
            control_code=control.code,
            control_title=control.title,
        )
        conversation: list[BaseMessage] = [SystemMessage(content=system_prompt)]
        conversation.extend(state["messages"])
        response = llm.invoke(conversation)
        return {
            "messages": [response],
            "phase": "COACHING",
            "status": "ACTIVE",
        }

    return coach_node


def create_evaluator_node() -> Callable[[AuditGraphState], dict[str, Any]]:
    """Factory creating the deterministic rubric evaluation node."""
    evaluator = DeterministicEvaluator()

    def evaluator_node(state: AuditGraphState) -> dict[str, Any]:
        rubric = get_standard_rubric(state["control_code"])
        evidence = state.get("collected_evidence", [])
        result = evaluator.evaluate(rubric=rubric, evidence_items=evidence)
        finding = result.finding

        if finding.severity.is_non_conformity():
            summary = (
                f"[AUDIT CONCLUSION - {finding.severity.value.upper()}]\n"
                f"Finding: {finding.title}\n"
                f"Statement: {finding.statement}\n"
                f"Corrective Action Required: {finding.remediation_guidance}"
            )
        else:
            summary = (
                f"[AUDIT CONCLUSION - {finding.severity.value.upper()}]\n"
                f"Result: {finding.title}\n"
                f"Details: {finding.statement}"
            )

        return {
            "evaluation_result": result,
            "finding": finding,
            "messages": [AIMessage(content=summary)],
            "phase": "CONCLUDED",
            "status": "CONCLUDED",
        }

    return evaluator_node


def build_audit_graph(llm: BaseChatModel, checkpointer: MemorySaver | None = None) -> Any:
    """Compile the LangGraph state machine with memory checkpointer."""
    workflow = StateGraph(AuditGraphState)

    workflow.add_node("auditor", cast(Any, create_auditor_node(llm)))
    workflow.add_node("coach", cast(Any, create_coach_node(llm)))
    workflow.add_node("evaluator", cast(Any, create_evaluator_node()))

    workflow.add_conditional_edges(
        START,
        route_user_turn,
        {
            "auditor": "auditor",
            "coach": "coach",
            "evaluator": "evaluator",
        },
    )
    workflow.add_edge("auditor", END)
    workflow.add_edge("coach", END)
    workflow.add_edge("evaluator", END)

    return workflow.compile(checkpointer=checkpointer or MemorySaver())


class LangGraphAuditAgent(AuditAgentPort):
    """Implementation of AuditAgentPort using a compiled LangGraph StateGraph."""

    def __init__(self, llm: BaseChatModel, checkpointer: MemorySaver | None = None) -> None:
        self._llm = llm
        self._checkpointer = checkpointer or MemorySaver()
        self._graph = build_audit_graph(self._llm, self._checkpointer)

    def start_session(self, session_id: str, control_code: str) -> dict[str, Any]:
        """Initialize session and generate opening auditor inquiry."""
        config: RunnableConfig = {"configurable": {"thread_id": session_id}}
        initial_input: dict[str, Any] = {
            "session_id": session_id,
            "control_code": control_code,
            "messages": [
                HumanMessage(
                    content=(
                        f"Commence formal ISO 27001 audit for control {control_code}. "
                        "State your opening audit inquiry."
                    )
                )
            ],
            "collected_evidence": [],
            "evaluation_result": None,
            "finding": None,
            "phase": "INITIALIZING",
            "status": "ACTIVE",
        }
        res = self._graph.invoke(initial_input, config=config)
        return cast(dict[str, Any], res)

    def process_turn(
        self,
        session_id: str,
        user_message: str,
        evidence: list[Evidence] | None = None,
    ) -> dict[str, Any]:
        """Process user message and optional evidence submission through the graph."""
        config: RunnableConfig = {"configurable": {"thread_id": session_id}}
        inputs: dict[str, Any] = {"messages": [HumanMessage(content=user_message)]}
        if evidence:
            inputs["collected_evidence"] = evidence
        res = self._graph.invoke(inputs, config=config)
        return cast(dict[str, Any], res)

    def get_state(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve latest snapshot state from checkpointer."""
        config: RunnableConfig = {"configurable": {"thread_id": session_id}}
        snapshot = self._graph.get_state(config)
        if snapshot and snapshot.values:
            return dict(snapshot.values)
        return None
