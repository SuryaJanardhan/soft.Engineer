from agents.services import WorkflowServices


def record_stop_reason(job_id: str, reason: str, services: WorkflowServices) -> None:
    services.store.record_audit_event(job_id, "agent_stopped", reason)


def stop_node(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    reason = str(state.get("stop_reason", "Validation failed after repair limit"))
    record_stop_reason(str(state["job_id"]), reason, services)
    final_state = "paused" if "incident" in reason.lower() else "failed"
    return {"stop_reason": reason, "final_state": final_state}
