"""Structured Engineering Contract schema for soft.Engineer Brain -> OpenHands Coder execution."""

from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class StructuredEngineeringContract:
    task_id: str
    summary: str
    description: str
    acceptance_criteria: list[str]
    target_symbols: list[str]
    allowed_files: list[str]
    forbidden_files: list[str]
    expected_behavior: str
    relevant_callers: list[str]
    relevant_tests: list[str]
    historical_evidence: list[dict[str, object]]
    risk_level: RiskLevel
    validation_commands: list[str]
    stop_conditions: list[str]
    is_ambiguous: bool = False
    ambiguity_reason: str = ""

    def to_prompt_contract(self) -> str:
        """Formats contract into an explicit engineering contract string for the LLM Coder."""
        historical_str = "\n".join(
            f"  - Ticket {h.get('ticket_id')}: {h.get('summary')} (Outcome: {h.get('outcome')})"
            for h in self.historical_evidence
        ) or "  - None"

        return f"""=== STRUCTURED ENGINEERING CONTRACT ===
Task ID: {self.task_id}
Summary: {self.summary}
Description: {self.description}

Acceptance Criteria:
{chr(10).join(f"- {c}" for c in self.acceptance_criteria) or "- Resolve ticket issue successfully."}

Scope Rules:
- Target Symbols: {', '.join(self.target_symbols) or 'Unspecified'}
- Allowed Files (STRICTLY ENFORCED): {', '.join(self.allowed_files) or 'All non-forbidden files'}
- Forbidden Files (STRICTLY PROHIBITED): {', '.join(self.forbidden_files) or 'None'}

Engineering Context:
- Expected Behavior: {self.expected_behavior}
- Relevant Callers / Entrypoints: {', '.join(self.relevant_callers) or 'None'}
- Relevant Test Suite Files: {', '.join(self.relevant_tests) or 'None'}

Historical Evidence:
{historical_str}

Risk & Validation:
- Risk Level: {self.risk_level.value}
- Validation Commands: {', '.join(self.validation_commands) or 'python -m pytest'}
- Stop Conditions: {', '.join(self.stop_conditions) or 'Stop if tests pass or unresolvable error occurs.'}
======================================="""
