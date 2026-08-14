from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _get_sdk_llm(model_name: str | None = None, api_key: str | None = None, base_url: str | None = None):
    """Initialize the OpenHands SDK LLM using officially installed packages."""
    from pydantic import SecretStr
    from openhands.sdk import LLM

    resolved_model = model_name or os.getenv("LLM_MODEL", "gpt-5.5")
    resolved_key = api_key or os.getenv("LLM_API_KEY")
    resolved_base = base_url or os.getenv("LLM_BASE_URL")

    if not resolved_key:
        raise ValueError("LLM_API_KEY is required to initialize the OpenHands SDK runtime")

    return LLM(
        model=resolved_model,
        api_key=SecretStr(resolved_key),
        base_url=resolved_base,
        usage_id="soft-engineer-core-agent",
    )


def build_default_openhands_agent(model_name: str | None = None, api_key: str | None = None, base_url: str | None = None, cli_mode: bool = True):
    """Build a default execution agent using the OpenHands SDK preset."""
    from openhands.tools.preset.default import get_default_agent

    llm = _get_sdk_llm(model_name=model_name, api_key=api_key, base_url=base_url)
    return get_default_agent(llm=llm, cli_mode=cli_mode)


def build_planning_openhands_agent(model_name: str | None = None, api_key: str | None = None, base_url: str | None = None):
    """Build a planning agent using the OpenHands SDK preset."""
    from openhands.tools.preset.planning import get_planning_agent

    llm = _get_sdk_llm(model_name=model_name, api_key=api_key, base_url=base_url)
    return get_planning_agent(llm=llm)


class OpenHandsCodingRuntime:
    """Production-grade coding runtime backed by the OpenHands SDK.
    
    Uses the officially installed openhands-sdk and openhands-tools packages
    to delegate core agent execution, file editing, and terminal operations.
    """

    def __init__(
        self,
        workspace_root: str | Path,
        model_name: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.model_name = model_name or os.getenv("LLM_MODEL", "gpt-5.5")
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL")

    def is_available(self) -> bool:
        """Check if the OpenHands SDK is properly installed and configured."""
        if not self.api_key:
            return False
        try:
            import openhands.sdk  # noqa: F401
            import openhands.tools  # noqa: F401
            return True
        except Exception:
            return False

    def execute_plan(self, state: dict[str, Any], services: Any) -> list[dict[str, str]]:
        """Execute the implementation plan using the OpenHands SDK agent runtime.
        
        Falls back to legacy execution if the SDK is unavailable or LLM is not configured.
        """
        plan = state.get("plan", {})
        files = [str(path) for path in plan.get("files", [])]
        if not files:
            return []

        if not self.is_available():
            return [{"path": path, "summary": "SDK runtime unavailable; using legacy execution path"} for path in files]

        try:
            from openhands.sdk import Conversation

            agent = build_default_openhands_agent(
                model_name=self.model_name,
                api_key=self.api_key,
                base_url=self.base_url,
                cli_mode=True,
            )
            conversation = Conversation(agent=agent, workspace=str(self.workspace_root))

            ticket_summary = state.get("ticket", {}).get("summary", "Implement requested change")
            description = state.get("ticket", {}).get("description", "")
            prompt = (
                "You are operating in a bounded software engineering workflow. "
                "Implement the requested change in the current workspace with surgical scope. "
                f"Ticket summary: {ticket_summary}\n"
                f"Description: {description}\n"
                f"Files in scope: {files}\n"
                "Use the local repository, keep changes minimal, and validate with focused checks."
            )
            conversation.send_message(prompt)
            conversation.run()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                "OpenHands SDK execution failed; falling back to legacy path. Error: %s", e
            )
            return [{"path": path, "summary": f"SDK execution failed; legacy fallback for {Path(path).name}"} for path in files]

        executed = []
        for path in files:
            executed.append({"path": path, "summary": f"Executed via OpenHands SDK runtime for {Path(path).name}"})
        return executed
