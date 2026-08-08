from agents.services import WorkflowServices


def allocate_subagent_tasks(plan: dict[str, object]) -> list[dict[str, str]]:
    tasks: list[dict[str, str]] = []
    files = plan.get("files", [])
    validation_commands = plan.get("validation_commands", [])

    for file_path in files:
        tasks.append({
            "agent": "CoderAgent",
            "task": f"Apply requested change to {file_path}",
            "target": str(file_path),
        })

    for cmd in validation_commands:
        tasks.append({
            "agent": "TestingAgent",
            "task": f"Run verification test suite {cmd}",
            "target": str(cmd),
        })

    tasks.append({
        "agent": "CheckerAgent",
        "task": "Execute final syntax, linting, and issue resolution audit",
        "target": "full_codebase",
    })

    return tasks


def executive_node(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    job_id = str(state["job_id"])
    plan = state["plan"]
    allocated_tasks = allocate_subagent_tasks(plan)

    services.store.record_state_snapshot(
        job_id=job_id,
        node_name="executive",
        previous_state="make_plan",
        next_state="prepare_worktree",
        payload={"allocated_tasks": allocated_tasks},
    )

    return {"allocated_tasks": allocated_tasks}
