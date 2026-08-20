from agents.classifier import FailureCategory, classify_failure
from agents.services import WorkflowServices


def run_configured_checks(plan: dict[str, object], services: WorkflowServices) -> list[dict[str, object]]:
    return [services.repository.run_check(str(command_id)) for command_id in plan["validation_commands"]]


def collect_diff(changes: list[dict[str, str]]) -> str:
    return ", ".join(change["path"] for change in changes)


def evaluate_validation(results: list[dict[str, object]], diff_summary: str, modified_files: list[str]) -> dict[str, object]:
    passed = all(bool(result["passed"]) for result in results)
    classification = None
    if not passed:
        combined_output = "\n".join(str(r.get("output", "")) for r in results if not r.get("passed"))
        classification = classify_failure(combined_output, modified_files)

    return {
        "passed": passed,
        "summary": f"Validated changes: {diff_summary}",
        "results": results,
        "classification": classification,
    }


def validate_node(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    job_id = str(state["job_id"])
    results = run_configured_checks(state["plan"], services)
    modified_files = [c.get("path", "") for c in state.get("changes", [])]
    validation = evaluate_validation(results, collect_diff(state["changes"]), modified_files)
    
    next_node = route_after_validation({"validation": validation, "repair_attempts": state.get("repair_attempts", 0)}, services)
    
    services.store.record_state_snapshot(
        job_id=job_id,
        node_name="validate",
        previous_state="implement",
        next_state=next_node,
        payload={"validation": validation},
    )
    return {"validation": validation}


def route_after_validation(state: dict[str, object], services: WorkflowServices) -> str:
    validation = state.get("validation", {})
    if validation.get("passed"):
        return "checker"

    classification = validation.get("classification")
    if classification:
        cat = classification.get("category")
        # Non-repairable failure types route immediately to graceful stop for human intervention
        if cat in {FailureCategory.ENVIRONMENT_ERROR.value, FailureCategory.FLAKY_TEST.value, FailureCategory.REGRESSION.value}:
            return "stop"

    if int(state.get("repair_attempts", 0)) < services.config.max_repair_attempts:
        return "repair"
    return "stop"

