from typing import Protocol


class PlanningModel(Protocol):
    def make_plan(self, ticket: dict[str, str], context: dict[str, object]) -> dict[str, object]: ...

    def repair_plan(self, plan: dict[str, object], validation: dict[str, object]) -> dict[str, object]: ...


class DeterministicPlanningModel:
    """Local stand-in for a structured-output LLM provider."""

    def make_plan(self, ticket: dict[str, str], context: dict[str, object]) -> dict[str, object]:
        files = list(context["candidate_files"])
        return {
            "summary": f"Implement: {ticket['summary']}",
            "files": files,
            "validation_commands": list(context["test_commands"]),
            "risks": ["Demo adapter does not inspect a live repository"],
            "rollback": "Revert the agent branch before merge",
        }

    def repair_plan(self, plan: dict[str, object], validation: dict[str, object]) -> dict[str, object]:
        repaired_plan = dict(plan)
        repaired_plan["repair_note"] = f"Repair requested after: {validation['summary']}"
        return repaired_plan
