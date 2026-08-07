from agents.policy import should_pause
from agents.services import WorkflowServices


def read_file(path: str) -> str:
    return f"Demo file content for {path}"


def require_mutation_permission(state: dict[str, object], path: str, services: WorkflowServices) -> None:
    if should_pause(state.get("incident_severity")):
        raise PermissionError("Incident policy paused mutation work")
    if any(fragment in path for fragment in services.config.blocked_path_fragments):
        raise PermissionError(f"Blocked path: {path}")


def apply_patch(state: dict[str, object], path: str, services: WorkflowServices) -> dict[str, str]:
    require_mutation_permission(state, path, services)
    read_file(path)
    return {"path": path, "summary": "Applied bounded change"}


def agent_tool_loop(state: dict[str, object], services: WorkflowServices) -> list[dict[str, str]]:
    changes: list[dict[str, str]] = []
    for path in state["plan"]["files"]:
        changes.append(apply_patch(state, str(path), services))
    return changes


def implement_node(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    try:
        changes = agent_tool_loop(state, services)
    except PermissionError as error:
        return {"stop_reason": str(error)}
    return {"changes": changes}


def route_after_implementation(state: dict[str, object]) -> str:
    return "stop" if state.get("stop_reason") else "validate"
