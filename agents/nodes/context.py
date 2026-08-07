from agents.services import WorkflowServices


def search_repo(ticket: dict[str, str], services: WorkflowServices) -> dict[str, object]:
    return services.repository.collect_context(ticket["summary"])


def read_codeowners(context: dict[str, object]) -> list[str]:
    return list(context["owners"])


def read_recent_diffs(context: dict[str, object]) -> list[str]:
    return list(context["recent_changes"])


def find_tests(context: dict[str, object]) -> list[str]:
    return list(context["test_commands"])


def collect_context_node(state: dict[str, object], services: WorkflowServices) -> dict[str, object]:
    raw_context = search_repo(state["ticket"], services)
    return {
        "context": {
            "candidate_files": raw_context["candidate_files"],
            "owners": read_codeowners(raw_context),
            "recent_changes": read_recent_diffs(raw_context),
            "test_commands": find_tests(raw_context),
        }
    }
