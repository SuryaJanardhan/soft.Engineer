from agents.services import WorkflowServices


def increment_repair_attempt(attempts: int) -> int:
    return attempts + 1


def repair_node(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    repair_attempts = increment_repair_attempt(int(state.get("repair_attempts", 0)))
    repaired_plan = services.model.repair_plan(state["plan"], state["validation"])
    return {"plan": repaired_plan, "repair_attempts": repair_attempts}
