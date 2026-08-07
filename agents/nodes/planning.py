from agents.services import WorkflowServices


def call_model_structured(
    ticket: dict[str, str], context: dict[str, object], services: WorkflowServices
) -> dict[str, object]:
    return services.model.make_plan(ticket, context)


def validate_plan_schema(plan: dict[str, object]) -> bool:
    required_fields = {"summary", "files", "validation_commands", "risks", "rollback"}
    return required_fields.issubset(plan) and bool(plan["files"])


def check_plan_scope(plan: dict[str, object], services: WorkflowServices) -> str | None:
    files = [str(path) for path in plan["files"]]
    if len(files) > services.config.max_files_changed:
        return "Plan exceeds file-change budget"
    for path in files:
        if any(fragment in path for fragment in services.config.blocked_path_fragments):
            return f"Plan touches blocked path: {path}"
    return None


def make_plan_node(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    plan = call_model_structured(state["ticket"], state["context"], services)
    if not validate_plan_schema(plan):
        return {"stop_reason": "Model returned an invalid plan"}
    scope_failure = check_plan_scope(plan, services)
    if scope_failure:
        return {"stop_reason": scope_failure}
    return {"plan": plan}


def route_after_plan(state: dict[str, object]) -> str:
    return "stop" if state.get("stop_reason") else "prepare_worktree"
