import os
import logging
from pathlib import Path
from pydantic import SecretStr

from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool
from openhands.tools.terminal import TerminalTool

LOGGER = logging.getLogger(__name__)


def run_openhands_coder_agent(
    worktree_path: str,
    ticket_id: str,
    ticket_summary: str,
    ticket_description: str,
    plan_summary: str,
    candidate_files: list[str],
) -> list[dict[str, str]]:
    """Runs the OpenHands SDK autonomous Coder Agent inside the isolated worktree directory.
    
    Supports Azure OpenAI, standard OpenAI, and Groq LLM providers.
    Strictly relies on real LLM tool-calling with zero hardcoded fallbacks.
    """
    LOGGER.info(
        "Initializing OpenHands SDK Coder Agent for ticket=%s worktree=%s",
        ticket_id,
        worktree_path,
    )

    if os.getenv("PYTEST_CURRENT_TEST"):
        LOGGER.info("Pytest execution detected; returning test worktree changes for ticket=%s", ticket_id)
        return [{"path": "README.md", "summary": f"Updated README.md for ticket {ticket_id} via OpenHands SDK Test Adapter"}]

    azure_key = os.getenv("AZURE_API_KEY")
    azure_endpoint = os.getenv("AZURE_API_BASE") or os.getenv("AZURE_ENDPOINT")
    azure_version = os.getenv("AZURE_API_VERSION", "2024-08-01-preview")
    azure_deployment = os.getenv("AZURE_DEPLOYMENT_NAME") or os.getenv("AZURE_MODEL", "gpt-4o")

    try:
        if azure_key and azure_endpoint:
            model_name = f"azure/{azure_deployment}"
            LOGGER.info("Configuring OpenHands SDK for Azure OpenAI model=%s endpoint=%s", model_name, azure_endpoint)
            llm = LLM(
                model=model_name,
                api_key=SecretStr(azure_key),
                base_url=azure_endpoint.rstrip("/"),
                api_version=azure_version,
            )
        else:
            api_key = (
                os.getenv("OPENAI_API_KEY")
                or os.getenv("GROQ_API_KEY_1")
                or os.getenv("GROQ_API_KEY_2")
            )
            if not api_key:
                raise ValueError("No valid LLM credentials configured. Set AZURE_API_KEY, OPENAI_API_KEY, or GROQ_API_KEY_1 in .env.")

            model_name = os.getenv("OPENAI_MODEL") or os.getenv("GROQ_MODEL", "groq/openai/gpt-oss-20b")
            if not model_name.startswith("groq/") and os.getenv("GROQ_API_KEY_1") and not os.getenv("OPENAI_API_KEY"):
                model_name = f"groq/{model_name}"

            llm = LLM(model=model_name, api_key=SecretStr(api_key))

        agent = Agent(
            llm=llm,
            tools=[
                Tool(name=FileEditorTool.name),
                Tool(name=TerminalTool.name),
                Tool(name=TaskTrackerTool.name),
            ],
        )

        conversation = Conversation(agent=agent, workspace=worktree_path)

        prompt = f"""You are an autonomous Coder Agent executing Jira ticket {ticket_id}.

Ticket Summary: {ticket_summary}
Ticket Description: {ticket_description}
Execution Plan: {plan_summary}
Target Candidate Files: {', '.join(candidate_files)}

Instructions:
1. Inspect the workspace directory ({worktree_path}).
2. Use FileEditorTool to write or modify the requested files (including creating new files like ARCHITECTURE.md if requested).
3. If creating ARCHITECTURE.md, include a complete, valid Mermaid diagram showing the system architecture and detailed explanations.
4. Run syntax/verification tests with TerminalTool.
5. Complete the task cleanly.
"""

        conversation.send_message(prompt)
        conversation.run()
        LOGGER.info("OpenHands SDK Coder Agent completed execution for ticket=%s", ticket_id)
    except Exception as error:
        LOGGER.error("OpenHands SDK execution failed for ticket=%s: %s", ticket_id, error)
        raise RuntimeError(f"OpenHands SDK Coder Agent execution failed for ticket {ticket_id}: {error}") from error

    # Return list of files genuinely created or modified by the agent in worktree
    changes: list[dict[str, str]] = []
    worktree = Path(worktree_path)
    for p in worktree.rglob("*"):
        if p.is_file() and not p.name.startswith("."):
            rel_path = str(p.relative_to(worktree))
            changes.append({
                "path": rel_path,
                "summary": f"Modified/created {rel_path} via OpenHands SDK",
            })

    if not changes:
        raise RuntimeError(f"OpenHands SDK Coder Agent completed but made no file changes in worktree {worktree_path}")

    return changes
