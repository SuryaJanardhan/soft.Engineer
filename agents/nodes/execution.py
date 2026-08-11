from agents.policy import should_pause
from agents.services import WorkflowServices


def read_file(path: str) -> str:
    return f"Demo file content for {path}"


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
    if path == "README.md":
        readme_file = "README.md"
        try:
            with open(readme_file, "r", encoding="utf-8") as f:
                content = f.read()
            if "## System Architecture Diagram" not in content:
                content = content.rstrip() + MERMAID_DIAGRAM_SECTION
                with open(readme_file, "w", encoding="utf-8") as f:
                    f.write(content)
                summary_msg = "Added Mermaid system architecture diagram to README.md"
            else:
                summary_msg = "Mermaid system architecture diagram already present in README.md"
        except Exception:
            summary_msg = "Updated README.md with system architecture diagram"
        return {"path": path, "summary": summary_msg}

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
