"""Unit tests for repository knowledge tools."""

from pathlib import Path
from agents.knowledge import KnowledgeBase
from agents.tools.repository_tools import (
    get_callers,
    get_dependencies,
    get_related_tests,
    get_symbol,
    search_code,
)


def test_repository_tools(tmp_path: Path):
    db_path = tmp_path / "knowledge.db"
    kb = KnowledgeBase(db_path)

    # Index sample python files
    repo_root = tmp_path / "sample_repo"
    repo_root.mkdir()
    (repo_root / "main.py").write_text("def run():\n    pass\n")
    (repo_root / "tests").mkdir()
    (repo_root / "tests" / "test_main.py").write_text("def test_run():\n    pass\n")

    kb.index_python_repository("test_repo", repo_root)

    # Search code
    symbols = search_code("run", repository="test_repo", db_path=db_path)
    assert len(symbols) > 0

    # Get symbol
    details = get_symbol("run", repository="test_repo", db_path=db_path)
    assert len(details) > 0
    assert details[0]["symbol"] == "run"

    # Get callers
    callers = get_callers("run", repository="test_repo", db_path=db_path)
    assert isinstance(callers, list)

    # Get dependencies
    deps = get_dependencies("main.py", repository="test_repo", db_path=db_path)
    assert isinstance(deps, list)

    # Get related tests
    tests = get_related_tests("main.py", repository="test_repo", db_path=db_path)
    assert any("test_main.py" in t for t in tests)
