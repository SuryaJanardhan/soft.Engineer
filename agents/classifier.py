"""Failure classification module for soft.Engineer test execution output."""

from enum import Enum
import re
import logging

LOGGER = logging.getLogger(__name__)


class FailureCategory(str, Enum):
    IMPLEMENTATION_BUG = "IMPLEMENTATION_BUG"
    GENERATED_TEST_BUG = "GENERATED_TEST_BUG"
    ENVIRONMENT_ERROR = "ENVIRONMENT_ERROR"
    FLAKY_TEST = "FLAKY_TEST"
    REGRESSION = "REGRESSION"


def classify_failure(output: str, modified_files: list[str] | None = None) -> dict[str, str]:
    """Classifies a test failure log output into a structured FailureCategory and explanation.
    
    Rule-based log parser inspecting tracebacks, error types, and file scopes.
    """
    if not output:
        return {
            "category": FailureCategory.IMPLEMENTATION_BUG.value,
            "reason": "Execution output was empty; assuming implementation error.",
        }

    output_lower = output.lower()
    modified = modified_files or []

    # 1. Environment & Credential Errors
    env_patterns = [
        r"modulenotfounderror",
        r"importerror",
        r"nologinerror",
        r"connectionrefusederror",
        r"no valid llm credentials",
        r"permission denied",
        r"command not found",
    ]
    for pattern in env_patterns:
        if re.search(pattern, output_lower):
            LOGGER.info("Failure classified as ENVIRONMENT_ERROR pattern='%s'", pattern)
            return {
                "category": FailureCategory.ENVIRONMENT_ERROR.value,
                "reason": f"Environment or missing credential/dependency issue detected: '{pattern}'",
            }

    # 2. Flaky / Timeout Errors
    flaky_patterns = [
        r"timeouterror",
        r"operation timed out",
        r"connection reset by peer",
        r"interrupted",
    ]
    for pattern in flaky_patterns:
        if re.search(pattern, output_lower):
            LOGGER.info("Failure classified as FLAKY_TEST pattern='%s'", pattern)
            return {
                "category": FailureCategory.FLAKY_TEST.value,
                "reason": f"Intermittent or timeout error detected: '{pattern}'",
            }

    # 3. Generated Test Bug
    if any(f.startswith("tests/") or f.endswith("_test.py") for f in modified):
        if "assertionerror" in output_lower or "syntaxerror" in output_lower:
            LOGGER.info("Failure classified as GENERATED_TEST_BUG in modified test files")
            return {
                "category": FailureCategory.GENERATED_TEST_BUG.value,
                "reason": "Assertion or syntax error in newly generated/modified test files.",
            }

    # 4. Regression in untouched code
    if "failed" in output_lower or "error" in output_lower:
        # Check if error traceback references files outside modified scope
        file_matches = re.findall(r'File "([^"]+)"', output)
        if file_matches and modified:
            unmodified_errors = [f for f in file_matches if not any(m in f for m in modified)]
            if len(unmodified_errors) > len(file_matches) / 2:
                LOGGER.info("Failure classified as REGRESSION in legacy unmodified files")
                return {
                    "category": FailureCategory.REGRESSION.value,
                    "reason": "Test failure occurred primarily in legacy unmodified files.",
                }

    # 5. Default: Core Implementation Bug
    LOGGER.info("Failure classified as IMPLEMENTATION_BUG")
    return {
        "category": FailureCategory.IMPLEMENTATION_BUG.value,
        "reason": "Core implementation logic error or assertion failure in target module.",
    }
