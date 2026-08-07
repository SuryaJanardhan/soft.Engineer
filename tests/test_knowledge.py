from agents.knowledge import KnowledgeBase


def test_knowledge_base_indexes_symbols_and_recalls_fix(tmp_path) -> None:
    repository = tmp_path / "core"
    repository.mkdir()
    (repository / "display.py").write_text(
        "from helpers import format_name\n\ndef render_display_name():\n    return format_name()\n",
        encoding="utf-8",
    )
    knowledge_base = KnowledgeBase(tmp_path / "knowledge.db")

    assert knowledge_base.index_python_repository("demo/repository", repository) == 2
    knowledge_base.record_fix(
        repository="demo/repository",
        ticket_id="ENG-1",
        summary="Fix empty display names",
        files=["display.py"],
        validation={"passed": True},
        pr_url="https://example.invalid/pr/1",
        outcome="merged",
    )

    context = knowledge_base.context_for_ticket("demo/repository", "Fix empty display names renderer")

    assert context["related_symbols"]
    assert context["known_fixes"][0]["ticket_id"] == "ENG-1"

    knowledge_base.update_fix_outcome("demo/repository", "ENG-1", "merged")
    assert knowledge_base.find_known_fixes("demo/repository", "empty display name")[0]["outcome"] == "merged"
