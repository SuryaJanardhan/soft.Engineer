import logging
from dataclasses import dataclass


LOGGER = logging.getLogger(__name__)


@dataclass
class DemoRepository:
    """Safe local adapter used until real GitHub and Git adapters are configured."""

    repository: str = "demo/repository"

    def collect_context(self, ticket_summary: str) -> dict[str, object]:
        LOGGER.info("Collecting repository context for ticket=%s", ticket_summary)
        summary_lower = ticket_summary.lower()
        if "readme" in summary_lower or "architecture" in summary_lower or "diagram" in summary_lower:
            candidate_files = ["README.md"]
        else:
            candidate_files = ["src/example.py", "tests/test_example.py"]

        return {
            "candidate_files": candidate_files,
            "owners": ["platform-team"],
            "recent_changes": ["No recent conflicting change found in demo adapter"],
            "test_commands": ["unit_tests"],
        }


    def create_worktree(self, job_id: str) -> str:
        worktree_path = f"/tmp/soft-engineer/{job_id}"
        LOGGER.info("Prepared isolated demo worktree job_id=%s", job_id)
        return worktree_path

    def create_branch(self, ticket_id: str) -> str:
        return f"agent/{ticket_id.lower()}"

    def apply_changes(self, plan: dict[str, object]) -> list[dict[str, str]]:
        files = plan["files"]
        return [{"path": str(path), "summary": "Updated by bounded demo adapter"} for path in files]

    def run_check(self, command_id: str) -> dict[str, object]:
        LOGGER.info("Running configured check command_id=%s", command_id)
        return {"command_id": command_id, "passed": True, "output": "Demo validation passed"}

    def create_draft_pr(self, branch_name: str, title: str) -> str:
        safe_branch = branch_name.replace("/", "-")
        LOGGER.info("Created demo draft PR branch=%s", branch_name)
        return f"https://example.invalid/{self.repository}/pull/{safe_branch}?title={title}"
