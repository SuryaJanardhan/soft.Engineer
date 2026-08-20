"""Custom repository intelligence tools wrapping soft.Engineer KnowledgeBase for OpenHands SDK."""

import logging
from pathlib import Path
from agents.config import KnowledgeBaseSettings
from agents.knowledge import KnowledgeBase

LOGGER = logging.getLogger(__name__)

_DEFAULT_SETTINGS = KnowledgeBaseSettings.from_environment()
_DEFAULT_DB_PATH = _DEFAULT_SETTINGS.database_path
_DEFAULT_REPO_NAME = _DEFAULT_SETTINGS.repository_name


def _get_kb(db_path: Path | None = None) -> KnowledgeBase:
    target_path = db_path or _DEFAULT_DB_PATH
    return KnowledgeBase(target_path)


def search_code(query: str, repository: str = _DEFAULT_REPO_NAME, db_path: Path | None = None) -> list[dict[str, str]]:
    """Search code symbols (functions, classes, modules) matching query."""
    kb = _get_kb(db_path)
    results = kb.search_symbols(repository, query)
    LOGGER.info("search_code query='%s' found %d results", query, len(results))
    return results


def get_symbol(symbol_name: str, repository: str = _DEFAULT_REPO_NAME, db_path: Path | None = None) -> list[dict[str, str]]:
    """Fetch exact definition and path for a target symbol."""
    kb = _get_kb(db_path)
    results = kb.get_symbol_details(repository, symbol_name)
    LOGGER.info("get_symbol symbol='%s' found %d results", symbol_name, len(results))
    return results


def get_callers(symbol_name: str, repository: str = _DEFAULT_REPO_NAME, db_path: Path | None = None) -> list[dict[str, str]]:
    """Find caller relationships and target symbol edges."""
    kb = _get_kb(db_path)
    results = kb.get_symbol_callers(repository, symbol_name)
    LOGGER.info("get_callers symbol='%s' found %d results", symbol_name, len(results))
    return results


def get_dependencies(file_path: str, repository: str = _DEFAULT_REPO_NAME, db_path: Path | None = None) -> list[dict[str, str]]:
    """Get import and dependency graph for a file path."""
    kb = _get_kb(db_path)
    results = kb.get_file_dependencies(repository, file_path)
    LOGGER.info("get_dependencies path='%s' found %d results", file_path, len(results))
    return results


def get_related_tests(file_path: str, repository: str = _DEFAULT_REPO_NAME, db_path: Path | None = None) -> list[str]:
    """Find associated test files for a source module."""
    kb = _get_kb(db_path)
    results = kb.get_related_tests(repository, file_path)
    LOGGER.info("get_related_tests path='%s' found %d test files", file_path, len(results))
    return results
