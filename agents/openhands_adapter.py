import logging
import os
import subprocess
from pathlib import Path

from openhands.sdk import Agent, Conversation, Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool
from openhands.tools.terminal import TerminalTool

from agents.contract import StructuredEngineeringContract
from agents.providers import LLMProviderFactory

LOGGER = logging.getLogger(__name__)


def _get_git_changed_files(worktree_path: str) -> set[str]:
    """Returns exact set of modified/untracked files relative to worktree root using git status & diff."""
    try:
        status = subprocess.check_output(
            ["git", "status", "--short"], cwd=worktree_path, encoding="utf-8"
        )
        changed = set()
        for line in status.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                changed.add(parts[1].strip())
        return changed
    except subprocess.SubprocessError as err:
        LOGGER.warning("Failed to inspect git status in worktree=%s: %s", worktree_path, err)
        return set()


def run_openhands_coder_agent(
    worktree_path: str,
    ticket_id: str,
    ticket_summary: str,
    ticket_description: str,
    plan_summary: str,
    candidate_files: list[str],
    hypothesis: dict[str, object] | None = None,
    contract: StructuredEngineeringContract | None = None,
) -> list[dict[str, str]]:
    """Runs the OpenHands SDK autonomous Coder Agent inside the isolated worktree directory.
    
    Uses LLMProviderFactory for clean provider selection (Azure OpenAI, OpenAI, Groq).
    Strict single execution path with zero fallbacks. Enforces strict Git diff scope validation.
    """
    LOGGER.info(
        "Initializing OpenHands SDK Coder Agent for ticket=%s worktree=%s",
        ticket_id,
        worktree_path,
    )

    # Capture pre-execution git snapshot
    pre_changed_files = _get_git_changed_files(worktree_path)

    try:
        llm = LLMProviderFactory.create_llm()

        agent = Agent(
            llm=llm,
            tools=[
                Tool(name=FileEditorTool.name),
                Tool(name=TerminalTool.name),
                Tool(name=TaskTrackerTool.name),
            ],
        )

        conversation = Conversation(agent=agent, workspace=worktree_path)

        contract_prompt = ""
        if contract:
            contract_prompt = f"\n{contract.to_prompt_contract()}\n"
        elif hypothesis:
            contract_prompt = (
                f"\nStructured Hypothesis from soft.Engineer Brain:\n"
                f"- Target Symbols: {hypothesis.get('target_symbols', [])}\n"
                f"- Expected Behavior: {hypothesis.get('expected_behavior', '')}\n"
                f"- Proposed Patch: {hypothesis.get('proposed_change', '')}\n"
                f"- Risk Level: {hypothesis.get('risk_level', 'LOW')}\n"
            )

        prompt = f"""You are an autonomous Coder Agent executing Jira ticket {ticket_id}.

Ticket Summary: {ticket_summary}
Ticket Description: {ticket_description}
Execution Plan: {plan_summary}
Target Candidate Files: {', '.join(candidate_files)}
{contract_prompt}

Instructions:
1. Inspect the workspace directory ({worktree_path}).
2. Use FileEditorTool to write or modify requested files.
3. You are STRICTLY RESTRICTED to candidate / allowed files. Do NOT edit forbidden or outside files.
4. Run syntax/verification tests with TerminalTool.
5. Complete the task cleanly.
"""

        conversation.send_message(prompt)
        conversation.run()
        LOGGER.info("OpenHands SDK Coder Agent completed execution for ticket=%s", ticket_id)
    except Exception as error:
        LOGGER.error("OpenHands SDK execution failed for ticket=%s: %s", ticket_id, error)
        raise RuntimeError(f"OpenHands SDK Coder Agent execution failed for ticket {ticket_id}: {error}") from error

    # Post-execution Git diff scope validation
    post_changed_files = _get_git_changed_files(worktree_path)
    newly_changed = post_changed_files - pre_changed_files

    if contract and contract.allowed_files:
        unauthorized = [
            f for f in newly_changed
            if not any(f.startswith(allowed) or allowed in f for allowed in contract.allowed_files)
        ]
        if unauthorized:
            LOGGER.error("Hard scope violation detected! Unauthorized changed files: %s", unauthorized)
            # Revert unauthorized worktree modifications
            subprocess.run(["git", "checkout", "--", "."], cwd=worktree_path, check=False)
            raise RuntimeError(f"OpenHands Coder violated allowed scope by modifying unauthorized files: {unauthorized}")

    changes: list[dict[str, str]] = []
    for rel_path in sorted(newly_changed):
        changes.append({
            "path": rel_path,
            "summary": f"Modified/created {rel_path} via OpenHands SDK",
        })

    if not changes:
        raise RuntimeError(f"OpenHands SDK Coder Agent completed but made no file changes in worktree {worktree_path}")

    return changes
