"""Deterministic rubric evaluation engine for objective audit scoring."""

from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from grc_tool.core.evaluator.rubric import AuditRubric, Criterion
from grc_tool.core.models.evidence import Evidence
from grc_tool.core.models.finding import AuditFinding, FindingSeverity


class EvaluationResult(BaseModel):
    """Result of evaluating a set of evidence against an audit rubric."""

    model_config = ConfigDict(frozen=True)

    control_code: str
    is_compliant: bool
    score: float = Field(ge=0.0, le=1.0)
    satisfied_criteria: list[Criterion]
    unmet_criteria: list[Criterion]
    finding: AuditFinding


class DeterministicEvaluator:
    """Evaluates evidence artifacts against formal criteria without non-deterministic drift."""

    def evaluate(self, rubric: AuditRubric, evidence_items: list[Evidence]) -> EvaluationResult:
        """Evaluate evidence items against an AuditRubric and generate a formal AuditFinding."""
        if not evidence_items:
            unmet_criteria = list(rubric.criteria)
            finding = AuditFinding(
                finding_id=f"FND-{uuid4().hex[:8].upper()}",
                control_code=rubric.control_code,
                severity=FindingSeverity.MAJOR_NC,
                title=f"Absence of Evidence for Control {rubric.control_code}",
                statement=(
                    f"Total absence of objective evidence demonstrated for {rubric.title} "
                    f"({rubric.control_code}). None of the mandatory criteria could be verified."
                ),
                evidence_ids=[],
                remediation_guidance=(
                    "Implement the required governance controls, document processes in the "
                    "GRC platform, and collect verifiable evidence records."
                ),
            )
            return EvaluationResult(
                control_code=rubric.control_code,
                is_compliant=False,
                score=0.0,
                satisfied_criteria=[],
                unmet_criteria=unmet_criteria,
                finding=finding,
            )

        satisfied: list[Criterion] = []
        unmet: list[Criterion] = []

        for criterion in rubric.criteria:
            criterion_met = False
            for ev in evidence_items:
                if criterion.required_field is not None:
                    field_val = ev.get_field(criterion.required_field)
                    if field_val == criterion.expected_value:
                        criterion_met = True
                        break
                else:
                    criterion_met = True
                    break

            if criterion_met:
                satisfied.append(criterion)
            else:
                unmet.append(criterion)

        unmet_mandatory = [c for c in unmet if c.is_mandatory]
        unmet_optional = [c for c in unmet if not c.is_mandatory]
        evidence_ids = [ev.evidence_id for ev in evidence_items]
        score = len(satisfied) / len(rubric.criteria) if rubric.criteria else 1.0

        if not unmet_mandatory and not unmet_optional:
            severity = FindingSeverity.CONFORMANT
            is_compliant = True
            title = f"Conformant Implementation of Control {rubric.control_code}"
            statement = (
                f"All mandatory requirements and recommendations for {rubric.title} "
                f"({rubric.control_code}) were verified with objective evidence."
            )
            remediation = None

        elif not unmet_mandatory and unmet_optional:
            severity = FindingSeverity.OFI
            is_compliant = True
            title = f"Opportunity for Improvement in Control {rubric.control_code}"
            statement = (
                f"Mandatory requirements for {rubric.title} ({rubric.control_code}) are satisfied. "
                f"However, recommended practice criteria were omitted: "
                f"{'; '.join(c.description for c in unmet_optional)}."
            )
            remediation = None

        elif len(unmet_mandatory) == len(rubric.mandatory_criteria):
            severity = FindingSeverity.MAJOR_NC
            is_compliant = False
            title = f"Major Non-Conformity in Control {rubric.control_code}"
            statement = (
                f"Total absence or systemic breakdown in satisfying mandatory requirements for "
                f"{rubric.title} ({rubric.control_code}): "
                f"{'; '.join(c.description for c in unmet_mandatory)}."
            )
            remediation = (
                f"Establish necessary controls and documentation to satisfy: "
                f"{'; '.join(c.description for c in unmet_mandatory)}."
            )

        else:
            severity = FindingSeverity.MINOR_NC
            is_compliant = False
            title = f"Minor Non-Conformity in Control {rubric.control_code}"
            statement = (
                f"Isolated lapse in satisfying mandatory requirements for "
                f"{rubric.title} ({rubric.control_code}): "
                f"{'; '.join(c.description for c in unmet_mandatory)}."
            )
            remediation = (
                f"Remediate specific identified gap: "
                f"{'; '.join(c.description for c in unmet_mandatory)}."
            )

        finding = AuditFinding(
            finding_id=f"FND-{uuid4().hex[:8].upper()}",
            control_code=rubric.control_code,
            severity=severity,
            title=title,
            statement=statement,
            evidence_ids=evidence_ids,
            remediation_guidance=remediation,
        )

        return EvaluationResult(
            control_code=rubric.control_code,
            is_compliant=is_compliant,
            score=score,
            satisfied_criteria=satisfied,
            unmet_criteria=unmet,
            finding=finding,
        )
