"""Patch quality and security evidence validator."""

from dataclasses import dataclass
import re
import logging
from agents.contract import StructuredEngineeringContract

LOGGER = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    is_valid: bool
    score: float  # 0.0 to 1.0
    violations: list[str]
    summary: str


def validate_patch_quality(
    changes: list[dict[str, str]],
    contract: StructuredEngineeringContract | None = None,
    max_lines_changed: int = 500,
) -> ValidationReport:
    """Evaluates patch quality, diff size, forbidden file access, secret leaks, and scope adherence."""
    violations: list[str] = []
    score = 1.0

    if not changes:
        return ValidationReport(
            is_valid=False,
            score=0.0,
            violations=["No files changed"],
            summary="Patch failed: zero files modified.",
        )

    # 1. Scope & Forbidden Files Validation
    forbidden = contract.forbidden_files if contract else [".env", "secrets", "billing"]
    allowed = contract.allowed_files if contract else []

    for change in changes:
        path = change.get("path", "")
        if any(f in path for f in forbidden):
            violations.append(f"Forbidden file modified: {path}")
            score -= 0.5

        if allowed and not any(path.startswith(a) or a in path for a in allowed):
            violations.append(f"File outside allowed contract scope: {path}")
            score -= 0.3

    # 2. Patch Size Validation
    if len(changes) > 10:
        violations.append(f"Patch too broad: modified {len(changes)} files (max allowed 10).")
        score -= 0.3

    # 3. Secret & Credential Scanning
    secret_patterns = [
        r"sk-[a-zA-Z0-9]{32,}",
        r"ghp_[a-zA-Z0-9]{36}",
        r"-----BEGIN PRIVATE KEY-----",
    ]
    for change in changes:
        content = change.get("summary", "")
        for pattern in secret_patterns:
            if re.search(pattern, content):
                violations.append(f"Potential secret key leaked in change summary for {change.get('path')}")
                score -= 0.8

    is_valid = len(violations) == 0 and score >= 0.7
    summary_msg = "Patch passed evidence validation cleanly." if is_valid else f"Patch validation failed with {len(violations)} violations."

    LOGGER.info("Patch quality validation result is_valid=%s score=%.2f violations=%d", is_valid, score, len(violations))
    return ValidationReport(
        is_valid=is_valid,
        score=max(0.0, score),
        violations=violations,
        summary=summary_msg,
    )
