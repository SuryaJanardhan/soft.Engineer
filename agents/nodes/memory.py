import uuid
from agents.services import WorkflowServices


def memory_node(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    job_id = str(state["job_id"])
    memory_id = f"mem-{uuid.uuid4().hex[:8]}"

    memory_payload = {
        "memory_id": memory_id,
        "ticket": state["ticket"],
        "intake_data": state.get("intake_data", {}),
        "policy": state.get("policy", {}),
    }

    services.store.record_state_snapshot(
        job_id=job_id,
        node_name="memory",
        previous_state="intake",
        next_state="collect_context",
        payload=memory_payload,
    )

    return {"memory_id": memory_id}
