"""End-to-End Fixture Repository Benchmark Suite."""

from pathlib import Path
from agents.contract import RiskLevel, StructuredEngineeringContract
from agents.knowledge import KnowledgeBase
from agents.openhands_adapter import run_openhands_coder_agent
from agents.validator import validate_patch_quality


def test_fixture_repository_benchmark(tmp_path: Path):
    """End-to-End benchmark testing ticket -> Brain -> OpenHands -> Git scope -> validation."""
    fixture_repo = tmp_path / "benchmark_fixture"
    fixture_repo.mkdir()

    # Seed intentional bug in fixture repository
    (fixture_repo / "calculator.py").write_text(
        "def add(a, b):\n    return a - b  # Intentional bug: minus instead of plus\n"
    )
    (fixture_repo / "tests").mkdir()
    (fixture_repo / "tests" / "test_calculator.py").write_text(
        "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    )

    # Initialize Git repository inside fixture
    import subprocess
    subprocess.run(["git", "init"], cwd=fixture_repo, check=True)
    subprocess.run(["git", "add", "."], cwd=fixture_repo, check=True)
    subprocess.run(["git", "config", "user.name", "BenchmarkTest"], cwd=fixture_repo, check=True)
    subprocess.run(["git", "config", "user.email", "benchmark@example.com"], cwd=fixture_repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=fixture_repo, check=True)

    # Index repository into KnowledgeBase
    db_path = tmp_path / "knowledge.db"
    kb = KnowledgeBase(db_path)
    kb.index_python_repository("benchmark_repo", fixture_repo)

    # Formulate StructuredEngineeringContract
    contract = StructuredEngineeringContract(
        task_id="BENCH-001",
        summary="Fix calculator add function bug",
        description="calculator.py add function performs subtraction instead of addition.",
        acceptance_criteria=["add(a, b) returns a + b."],
        target_symbols=["add"],
        allowed_files=["calculator.py", "README.md"],
        forbidden_files=[".env"],
        expected_behavior="add(2, 3) returns 5",
        relevant_callers=["test_add"],
        relevant_tests=["tests/test_calculator.py"],
        historical_evidence=[],
        risk_level=RiskLevel.LOW,
        validation_commands=["python -m pytest tests/"],
        stop_conditions=["Stop if tests pass"],
    )

    # Execute OpenHands Coder Agent with mocked LLM conversation applying real worktree file edit
    from unittest.mock import patch
    from openhands.sdk import LLM
    from pydantic import SecretStr

    mock_llm = LLM(model="groq/qwen/qwen3.6-27b", api_key=SecretStr("mock_key"))

    with patch("agents.openhands_adapter.Conversation") as mock_conv, patch("agents.openhands_adapter.LLMProviderFactory.create_llm", return_value=mock_llm):
        def mock_run():
            (fixture_repo / "calculator.py").write_text("def add(a, b):\n    return a + b  # Fixed addition bug\n")
        mock_conv.return_value.run.side_effect = mock_run

        changes = run_openhands_coder_agent(
            worktree_path=str(fixture_repo),
            ticket_id="BENCH-001",
            ticket_summary=contract.summary,
            ticket_description=contract.description,
            plan_summary="Fix calculator.py add function",
            candidate_files=contract.allowed_files,
            contract=contract,
        )

    assert len(changes) > 0

    # Validate patch quality
    report = validate_patch_quality(changes, contract=contract)
    assert report.is_valid is True
