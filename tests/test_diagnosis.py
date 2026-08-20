"""Unit tests for root-cause diagnosis."""

from agents.diagnosis import diagnose_failure


def test_diagnose_assertion_failure():
    log = "AssertionError: expected 'active' but got 'inactive'\n  File 'services/user.py', line 42 in test_user_status"
    diagnosis = diagnose_failure(log, modified_files=["services/user.py"])
    assert diagnosis.confidence >= 0.8
    assert "Assertion mismatch" in diagnosis.root_cause


def test_diagnose_type_error():
    log = "TypeError: missing 1 required positional argument: 'user_id'\n  File 'services/user.py', line 12 in get_user"
    diagnosis = diagnose_failure(log, modified_files=["services/user.py"])
    assert diagnosis.confidence >= 0.85
    assert "Type incompatibility" in diagnosis.root_cause
