"""Unit tests for failure classifier."""

from agents.classifier import FailureCategory, classify_failure


def test_classify_environment_error():
    log = "ModuleNotFoundError: No module named 'nonexistent_package'"
    result = classify_failure(log)
    assert result["category"] == FailureCategory.ENVIRONMENT_ERROR.value


def test_classify_flaky_test():
    log = "TimeoutError: The operation timed out after 30000ms"
    result = classify_failure(log)
    assert result["category"] == FailureCategory.FLAKY_TEST.value


def test_classify_generated_test_bug():
    log = "AssertionError: expected 'foo' to equal 'bar'"
    modified = ["tests/test_feature.py"]
    result = classify_failure(log, modified_files=modified)
    assert result["category"] == FailureCategory.GENERATED_TEST_BUG.value


def test_classify_implementation_bug():
    log = "ValueError: invalid literal for int() with base 10: 'abc'"
    modified = ["agents/nodes/execution.py"]
    result = classify_failure(log, modified_files=modified)
    assert result["category"] == FailureCategory.IMPLEMENTATION_BUG.value
