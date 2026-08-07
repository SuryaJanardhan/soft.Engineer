from langgraph.graph import END, START, StateGraph

from agents.models import AgentState
from agents.nodes.context import collect_context_node
from agents.nodes.execution import implement_node, route_after_implementation
from agents.nodes.handoff import create_draft_pr_node
from agents.nodes.planning import make_plan_node, route_after_plan
from agents.nodes.preflight import preflight_node, route_after_preflight
from agents.nodes.repair import repair_node
from agents.nodes.stop import stop_node
from agents.nodes.validation import route_after_validation, validate_node
from agents.nodes.workspace import prepare_worktree_node
from agents.services import WorkflowServices


def build_agent_graph(services: WorkflowServices):
    graph = StateGraph(AgentState)
    graph.add_node("preflight", lambda state: preflight_node(state, services))
    graph.add_node("collect_context", lambda state: collect_context_node(state, services))
    graph.add_node("make_plan", lambda state: make_plan_node(state, services))
    graph.add_node("prepare_worktree", lambda state: prepare_worktree_node(state, services))
    graph.add_node("implement", lambda state: implement_node(state, services))
    graph.add_node("validate", lambda state: validate_node(state, services))
    graph.add_node("repair", lambda state: repair_node(state, services))
    graph.add_node("create_draft_pr", lambda state: create_draft_pr_node(state, services))
    graph.add_node("stop", lambda state: stop_node(state, services))

    graph.add_edge(START, "preflight")
    graph.add_conditional_edges("preflight", route_after_preflight)
    graph.add_edge("collect_context", "make_plan")
    graph.add_conditional_edges("make_plan", route_after_plan)
    graph.add_edge("prepare_worktree", "implement")
    graph.add_conditional_edges("implement", route_after_implementation)
    graph.add_conditional_edges("validate", lambda state: route_after_validation(state, services))
    graph.add_edge("repair", "implement")
    graph.add_edge("create_draft_pr", END)
    graph.add_edge("stop", END)
    return graph.compile()
