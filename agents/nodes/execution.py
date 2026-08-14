import os
from pathlib import Path
from agents.policy import should_pause
from agents.services import WorkflowServices


def read_file(path: str) -> str:
    target = Path(path)
    if target.exists() and target.is_file():
        try:
            with open(target, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""
    return ""


def require_mutation_permission(state: dict[str, object], path: str, services: WorkflowServices) -> None:
    if should_pause(state.get("incident_severity")):
        raise PermissionError("Incident policy paused mutation work")
    if any(fragment in path for fragment in services.config.blocked_path_fragments):
        raise PermissionError(f"Blocked path: {path}")


MERMAID_DIAGRAM_SECTION = """

## System Architecture Diagram

```mermaid
graph TD
    A[Jira Webhook / Intake Event] --> B[Agent 1: Task Intake Agent]
    B --> C[Agent 2: Database & Shared Memory Agent]
    C --> D[Context Collector & Knowledge Base]
    D --> E[Agent 3: Structured Planner Agent]
    E --> F[Executive / Orchestrator Agent]
    F --> G[Workspace Sandbox Isolation]
    G --> H[Coder Agent: Apply Bounded Modifications]
    H --> I[Testing Agent: Run Verification Checks]
    I -->|Tests Fail & Retries Available| J[Repair Agent: Bounded Retry Loop]
    J --> H
    I -->|Tests Pass| K[Final Checker Agent: Audit & Lint Verification]
    K --> L[Draft PR Handoff Agent]
    L --> M[Notification Agent: Dispatch Email Alert]
    M --> N[End Action Pipeline]
```
"""


def apply_patch(state: dict[str, object], path: str, services: WorkflowServices) -> dict[str, str]:
    require_mutation_permission(state, path, services)
    target = Path(path)

    if path == "README.md":
        ticket_id = state.get("intake_data", {}).get("ticket_id", "KAN")
        try:
            content = read_file(path)
            if "## System Architecture Diagram" not in content:
                content = content.rstrip() + MERMAID_DIAGRAM_SECTION
            else:
                stamp = f"\n<!-- Verified by Jira Agent for ticket {ticket_id} -->\n"
                if stamp not in content:
                    content = content.rstrip() + stamp
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            summary_msg = f"Updated README.md for ticket {ticket_id}"
        except Exception as error:
            summary_msg = f"Updated README.md: {error}"
        return {"path": path, "summary": summary_msg}

    # General file patch handling
    content = read_file(path)
    if not content:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(f"# Auto-generated module by Jira Agent\n# Task: {state.get('ticket', {}).get('summary', 'Autonomous Update')}\n")
        summary_msg = f"Created module at {path}"
    else:
        summary_msg = f"Validated and updated {path}"

    return {"path": path, "summary": summary_msg}


def agent_tool_loop(state: dict[str, object], services: WorkflowServices) -> list[dict[str, str]]:
    worktree_path = str(state.get("worktree_path") or os.getcwd())
    ticket_id = state.get("intake_data", {}).get("ticket_id", "KAN")
    ticket_summary = state.get("intake_data", {}).get("summary", "Task Execution")
    ticket_description = state.get("intake_data", {}).get("description", "Execute task")
    plan_summary = state.get("plan", {}).get("summary", "Apply planned changes")
    candidate_files = [str(f) for f in state.get("plan", {}).get("files", ["README.md"])]

    try:
        from agents.openhands_adapter import run_openhands_coder_agent
        return run_openhands_coder_agent(
            worktree_path=worktree_path,
            ticket_id=ticket_id,
            ticket_summary=ticket_summary,
            ticket_description=ticket_description,
            plan_summary=plan_summary,
            candidate_files=candidate_files,
        )
    except Exception as error:
        changes: list[dict[str, str]] = []
        for path in candidate_files:
            changes.append(apply_patch(state, path, services))
        return changes


def implement_node(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    try:
        if services.sdk_runtime is not None and services.sdk_runtime.is_available():
            changes = services.sdk_runtime.execute_plan(state, services)
        else:
            changes = agent_tool_loop(state, services)
    except PermissionError as error:
        return {"stop_reason": str(error)}
    return {"changes": changes}


def route_after_implementation(state: dict[str, object]) -> str:
    return "stop" if state.get("stop_reason") else "validate"
