from agents.services import WorkflowServices



def run_configured_checks(plan: dict[str, object], services: WorkflowServices) -> list[dict[str, object]]:
    return [services.repository.run_check(str(command_id)) for command_id in plan["validation_commands"]]


def collect_diff(changes: list[dict[str, str]]) -> str:
    return ", ".join(change["path"] for change in changes)


def evaluate_validation(results: list[dict[str, object]], diff_summary: str) -> dict[str, object]:
    passed = all(bool(result["passed"]) for result in results)
    return {"passed": passed, "summary": f"Validated changes: {diff_summary}", "results": results}


def validate_node(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    results = run_configured_checks(state["plan"], services)
    validation = evaluate_validation(results, collect_diff(state["changes"]))
    return {"validation": validation}


def route_after_validation(state: dict[str, object], services: WorkflowServices) -> str:
    if state["validation"]["passed"]:
        return "create_draft_pr"
    if int(state.get("repair_attempts", 0)) < services.config.max_repair_attempts:
        return "repair"
    return "stop"
