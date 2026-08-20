"""Unit tests for patch quality validator."""

from agents.contract import RiskLevel, StructuredEngineeringContract
from agents.validator import validate_patch_quality


def test_validator_valid_patch():
    contract = StructuredEngineeringContract(
        task_id="ENG-101",
        summary="Fix bug",
        description="Fix small bug",
        acceptance_criteria=[],
        target_symbols=[],
        allowed_files=["services/user.py"],
        forbidden_files=[".env"],
        expected_behavior="Behavior fixed",
        relevant_callers=[],
        relevant_tests=[],
        historical_evidence=[],
        risk_level=RiskLevel.LOW,
        validation_commands=[],
        stop_conditions=[],
    )

    changes = [{"path": "services/user.py", "summary": "Modified services/user.py"}]
    report = validate_patch_quality(changes, contract=contract)
    assert report.is_valid is True
    assert report.score >= 0.7


def test_validator_forbidden_file_violation():
    contract = StructuredEngineeringContract(
        task_id="ENG-101",
        summary="Fix bug",
        description="Fix small bug",
        acceptance_criteria=[],
        target_symbols=[],
        allowed_files=["services/user.py"],
        forbidden_files=[".env"],
        expected_behavior="Behavior fixed",
        relevant_callers=[],
        relevant_tests=[],
        historical_evidence=[],
        risk_level=RiskLevel.LOW,
        validation_commands=[],
        stop_conditions=[],
    )

    changes = [{"path": ".env", "summary": "Modified .env file"}]
    report = validate_patch_quality(changes, contract=contract)
    assert report.is_valid is False
    assert len(report.violations) > 0
