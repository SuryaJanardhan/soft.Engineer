"""Root-cause diagnosis module for test failure logs prior to bounded repair."""

from dataclasses import dataclass
import re
import logging

LOGGER = logging.getLogger(__name__)


@dataclass
class RootCauseDiagnosis:
    root_cause: str
    evidence: str
    affected_symbols: list[str]
    proposed_fix: str
    confidence: float  # 0.0 to 1.0


def diagnose_failure(log_output: str, modified_files: list[str]) -> RootCauseDiagnosis:
    """Performs structured root-cause analysis on test failure output."""
    if not log_output:
        return RootCauseDiagnosis(
            root_cause="Unknown empty output",
            evidence="No log output produced",
            affected_symbols=[],
            proposed_fix="Re-run tests with verbose logging",
            confidence=0.2,
        )

    lines = log_output.splitlines()
    error_lines = [line for line in lines if "Error" in line or "FAILED" in line or "AssertionError" in line]

    # Extract symbol references from traceback lines
    symbol_matches = re.findall(r"(\b[A-Za-z_][A-Za-z0-9_]+\b)\(", log_output)
    unique_symbols = list(set(symbol_matches) - {"print", "len", "set", "dict", "list", "str", "int", "isinstance", "type", "open", "super", "getattr", "setattr"})[:5]

    evidence_str = "\n".join(error_lines[:3]) if error_lines else log_output[:300]

    if "AssertionError" in log_output:
        return RootCauseDiagnosis(
            root_cause="Assertion mismatch in return value or state output.",
            evidence=evidence_str,
            affected_symbols=unique_symbols,
            proposed_fix="Adjust core logic implementation to return expected value matching assertion.",
            confidence=0.85,
        )
    elif "TypeError" in log_output or "AttributeError" in log_output:
        return RootCauseDiagnosis(
            root_cause="Type incompatibility or missing symbol property access.",
            evidence=evidence_str,
            affected_symbols=unique_symbols,
            proposed_fix="Check method signature and object initialization parameters.",
            confidence=0.90,
        )
    elif "SyntaxError" in log_output:
        return RootCauseDiagnosis(
            root_cause="Syntax or indent error in code generation.",
            evidence=evidence_str,
            affected_symbols=unique_symbols,
            proposed_fix="Fix syntax syntax and missing closing brackets.",
            confidence=0.95,
        )

    return RootCauseDiagnosis(
        root_cause="General runtime execution failure.",
        evidence=evidence_str,
        affected_symbols=unique_symbols,
        proposed_fix="Review target candidate module for exception handling.",
        confidence=0.60,
    )
