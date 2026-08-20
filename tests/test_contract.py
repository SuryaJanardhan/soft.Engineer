"""Unit tests for StructuredEngineeringContract."""

from agents.contract import RiskLevel, StructuredEngineeringContract


def test_structured_engineering_contract_formatting():
    contract = StructuredEngineeringContract(
        task_id="ENG-101",
        summary="Fix user profile caching issue",
        description="Users see stale profile data after updating details.",
        acceptance_criteria=["Profile details update immediately upon save."],
        target_symbols=["get_user_profile", "clear_cache"],
        allowed_files=["services/user.py", "tests/test_user.py"],
        forbidden_files=[".env", "config/secrets.json"],
        expected_behavior="Cache invalidation is triggered on save.",
        relevant_callers=["update_user_profile_handler"],
        relevant_tests=["tests/test_user.py"],
        historical_evidence=[{"ticket_id": "ENG-50", "summary": "Cache invalidation bug", "outcome": "merged"}],
        risk_level=RiskLevel.LOW,
        validation_commands=["pytest tests/test_user.py"],
        stop_conditions=["Stop if tests pass cleanly"],
    )

    prompt = contract.to_prompt_contract()
    assert "ENG-101" in prompt
    assert "Fix user profile caching issue" in prompt
    assert "services/user.py" in prompt
    assert "LOW" in prompt
