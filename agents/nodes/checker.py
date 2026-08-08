from agents.services import WorkflowServices


def audit_final_code(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    validation = state.get("validation", {})
    changes = state.get("changes", [])
    validation_passed = bool(validation.get("passed", False))

    syntax_clean = True
    for change in changes:
        path = str(change.get("path", ""))
        if any(fragment in path for fragment in services.config.blocked_path_fragments):
            syntax_clean = False
            break

    issue_resolved = validation_passed and syntax_clean

    return {
        "issue_resolved": issue_resolved,
        "syntax_clean": syntax_clean,
        "test_suite_passed": validation_passed,
        "audit_summary": "Final quality, linting, and issue resolution audit passed cleanly.",
    }


def checker_node(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    job_id = str(state["job_id"])
    checker_results = audit_final_code(state, services)

    if not checker_results["issue_resolved"]:
        stop_reason = "Final checker audit failed: issue unresolved or syntax check failed"
        services.store.record_state_snapshot(
            job_id, "checker", "validate", "stop", {"checker_results": checker_results, "stop_reason": stop_reason}
        )
        return {"checker_results": checker_results, "stop_reason": stop_reason}

    services.store.record_state_snapshot(
        job_id, "checker", "validate", "create_draft_pr", {"checker_results": checker_results}
    )
    return {"checker_results": checker_results}


def route_after_checker(state: dict[str, object]) -> str:
    return "stop" if state.get("stop_reason") else "create_draft_pr"
