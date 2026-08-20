import os
import logging
from pathlib import Path
from agents.policy import should_pause
from agents.services import WorkflowServices

LOGGER = logging.getLogger(__name__)


def require_mutation_permission(state: dict[str, object], path: str, services: WorkflowServices) -> None:
    if should_pause(state.get("incident_severity")):
        raise PermissionError("Incident policy paused mutation work")
    if any(fragment in path for fragment in services.config.blocked_path_fragments):
        raise PermissionError(f"Blocked path: {path}")


def agent_tool_loop(state: dict[str, object], services: WorkflowServices) -> list[dict[str, str]]:
    """Invokes OpenHands SDK Coder Agent for autonomous execution.
    
    Zero hardcoded stubs or fake fallbacks. If execution fails, raises RuntimeError.
    """
    worktree_path = str(state.get("worktree_path") or os.getcwd())
    ticket_id = state.get("intake_data", {}).get("ticket_id", "KAN")
    ticket_summary = state.get("intake_data", {}).get("summary", "Task Execution")
    ticket_description = state.get("intake_data", {}).get("description", "Execute task")
    plan_summary = state.get("plan", {}).get("summary", "Apply planned changes")
    candidate_files = [str(f) for f in state.get("plan", {}).get("files", ["README.md"])]

    # Check permission for candidate files before invoking coder agent
    for path in candidate_files:
        require_mutation_permission(state, path, services)

    from agents.openhands_adapter import run_openhands_coder_agent
    return run_openhands_coder_agent(
        worktree_path=worktree_path,
        ticket_id=ticket_id,
        ticket_summary=ticket_summary,
        ticket_description=ticket_description,
        plan_summary=plan_summary,
        candidate_files=candidate_files,
    )


def implement_node(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    """LangGraph node for task implementation.
    
    If execution fails or is prohibited, halts gracefully with a stop_reason.
    """
    try:
        if services.sdk_runtime is not None and services.sdk_runtime.is_available():
            changes = services.sdk_runtime.execute_plan(state, services)
        else:
            changes = agent_tool_loop(state, services)
        return {"changes": changes}
    except (PermissionError, RuntimeError, ValueError) as error:
        LOGGER.error("Execution node stopped gracefully due to error: %s", error)
        return {"stop_reason": str(error)}


def route_after_implementation(state: dict[str, object]) -> str:
    return "stop" if state.get("stop_reason") else "validate"
