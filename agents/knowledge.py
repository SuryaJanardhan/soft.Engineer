import ast
import hashlib
import json
import logging
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class KnowledgeBase:
    """Central, local code graph and prior-fix memory for one core repository."""

    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.database_path = database_path
        self._create_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS code_nodes (
                    repository TEXT NOT NULL,
                    node_key TEXT NOT NULL,
                    path TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(repository, node_key)
                );
                CREATE TABLE IF NOT EXISTS code_edges (
                    repository TEXT NOT NULL,
                    source_key TEXT NOT NULL,
                    target_key TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    PRIMARY KEY(repository, source_key, target_key, relation)
                );
                CREATE TABLE IF NOT EXISTS fix_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repository TEXT NOT NULL,
                    ticket_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    files_json TEXT NOT NULL,
                    validation_json TEXT NOT NULL,
                    pr_url TEXT,
                    outcome TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS fix_history_fingerprint ON fix_history(repository, fingerprint);
                """
            )

    def index_python_repository(self, repository: str, root: Path) -> int:
        if not root.is_dir():
            raise FileNotFoundError(f"Core repository path does not exist: {root}")
        indexed_nodes = 0
        with self._connect() as connection:
            connection.execute("DELETE FROM code_nodes WHERE repository = ?", (repository,))
            connection.execute("DELETE FROM code_edges WHERE repository = ?", (repository,))
            for file_path in root.rglob("*.py"):
                if any(part in {".git", ".venv", "node_modules", "__pycache__"} for part in file_path.parts):
                    continue
                indexed_nodes += self._index_python_file(connection, repository, root, file_path)
        LOGGER.info("Indexed Python knowledge graph repository=%s nodes=%s", repository, indexed_nodes)
        return indexed_nodes

    def _index_python_file(
        self, connection: sqlite3.Connection, repository: str, root: Path, file_path: Path
    ) -> int:
        relative_path = str(file_path.relative_to(root))
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=relative_path)
        except (OSError, SyntaxError, UnicodeDecodeError):
            LOGGER.warning("Skipped unreadable Python file path=%s", relative_path)
            return 0

        module_key = f"module:{relative_path}"
        self._insert_node(connection, repository, module_key, relative_path, relative_path, "module")
        count = 1
        for item in tree.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                kind = "class" if isinstance(item, ast.ClassDef) else "function"
                symbol_key = f"{module_key}:{item.name}"
                self._insert_node(connection, repository, symbol_key, relative_path, item.name, kind)
                self._insert_edge(connection, repository, module_key, symbol_key, "defines")
                count += 1
            elif isinstance(item, ast.Import):
                for alias in item.names:
                    self._insert_edge(connection, repository, module_key, f"import:{alias.name}", "imports")
            elif isinstance(item, ast.ImportFrom) and item.module:
                self._insert_edge(connection, repository, module_key, f"import:{item.module}", "imports")
        return count

    def context_for_ticket(self, repository: str, text: str) -> dict[str, object]:
        tokens = self._tokens(text)
        with self._connect() as connection:
            nodes = connection.execute(
                "SELECT path, symbol, kind FROM code_nodes WHERE repository = ? LIMIT 200", (repository,)
            ).fetchall()
        related_symbols = [
            dict(row)
            for row in nodes
            if tokens.intersection(self._tokens(f"{row['path']} {row['symbol']}"))
        ][:10]
        return {"related_symbols": related_symbols, "known_fixes": self.find_known_fixes(repository, text)}

    def record_fix(
        self,
        repository: str,
        ticket_id: str,
        summary: str,
        files: list[str],
        validation: dict[str, object],
        pr_url: str | None,
        outcome: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO fix_history(repository, ticket_id, fingerprint, summary, files_json, validation_json, pr_url, outcome, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    repository,
                    ticket_id,
                    self._fingerprint(summary),
                    summary,
                    json.dumps(files),
                    json.dumps(validation),
                    pr_url,
                    outcome,
                    self._now(),
                ),
            )
        LOGGER.info("Recorded prior fix ticket_id=%s outcome=%s", ticket_id, outcome)

    def find_known_fixes(self, repository: str, issue_text: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT ticket_id, summary, files_json, validation_json, pr_url, outcome "
                "FROM fix_history WHERE repository = ? ORDER BY id DESC LIMIT 100",
                (repository,),
            ).fetchall()
        issue_tokens = self._tokens(issue_text)
        ranked_fixes: list[tuple[float, dict[str, object]]] = []
        for row in rows:
            fix_tokens = self._tokens(row["summary"])
            union_size = len(issue_tokens.union(fix_tokens))
            score = len(issue_tokens.intersection(fix_tokens)) / union_size if union_size else 0.0
            if score < 0.4:
                continue
            ranked_fixes.append(
                (score, {
                "ticket_id": row["ticket_id"],
                "summary": row["summary"],
                "files": json.loads(row["files_json"]),
                "validation": json.loads(row["validation_json"]),
                "pr_url": row["pr_url"],
                "outcome": row["outcome"],
                })
            )
        return [fix for _, fix in sorted(ranked_fixes, key=lambda item: item[0], reverse=True)[:5]]

    def search_symbols(self, repository: str, query: str) -> list[dict[str, str]]:
        """Search code symbols matching query string."""
        pattern = f"%{query}%"
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT path, symbol, kind FROM code_nodes WHERE repository = ? AND (symbol LIKE ? OR path LIKE ?) LIMIT 20",
                (repository, pattern, pattern),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_symbol_details(self, repository: str, symbol: str) -> list[dict[str, str]]:
        """Get definitions and location details for a given symbol name."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT path, symbol, kind, node_key FROM code_nodes WHERE repository = ? AND symbol = ?",
                (repository, symbol),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_symbol_callers(self, repository: str, symbol: str) -> list[dict[str, str]]:
        """Find callers and edge relationships pointing to or from a symbol."""
        pattern = f"%:{symbol}"
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT source_key, target_key, relation FROM code_edges WHERE repository = ? AND (target_key LIKE ? OR source_key LIKE ?)",
                (repository, pattern, pattern),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_file_dependencies(self, repository: str, path: str) -> list[dict[str, str]]:
        """Get import and dependency edges for a specific file path."""
        module_key = f"module:{path}"
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT source_key, target_key, relation FROM code_edges WHERE repository = ? AND source_key = ?",
                (repository, module_key),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_related_tests(self, repository: str, path: str) -> list[str]:
        """Find candidate test files associated with a source path."""
        stem = Path(path).stem
        test_pattern = f"test_{stem}.py"
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT path FROM code_nodes WHERE repository = ? AND (path LIKE ? OR path LIKE ?) GROUP BY path",
                (repository, f"%{test_pattern}", f"%tests/%"),
            ).fetchall()
        return [row["path"] for row in rows]

    def update_fix_outcome(self, repository: str, ticket_id: str, outcome: str) -> None:
        if outcome not in {"merged", "rejected", "reverted"}:
            raise ValueError("Outcome must be merged, rejected, or reverted")
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE fix_history SET outcome = ? WHERE id = ("
                "SELECT id FROM fix_history WHERE repository = ? AND ticket_id = ? ORDER BY id DESC LIMIT 1"
                ")",
                (outcome, repository, ticket_id),
            )
        if cursor.rowcount != 1:
            raise KeyError(f"No fix history exists for ticket: {ticket_id}")
        LOGGER.info("Updated prior fix outcome ticket_id=%s outcome=%s", ticket_id, outcome)

    def _insert_node(
        self, connection: sqlite3.Connection, repository: str, node_key: str, path: str, symbol: str, kind: str
    ) -> None:
        connection.execute(
            "INSERT INTO code_nodes(repository, node_key, path, symbol, kind, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (repository, node_key, path, symbol, kind, self._now()),
        )

    @staticmethod
    def _insert_edge(connection: sqlite3.Connection, repository: str, source: str, target: str, relation: str) -> None:
        connection.execute(
            "INSERT OR IGNORE INTO code_edges(repository, source_key, target_key, relation) VALUES (?, ?, ?, ?)",
            (repository, source, target, relation),
        )

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z][a-z0-9_]{2,}", text.lower()))

    def _fingerprint(self, text: str) -> str:
        normalized = " ".join(sorted(self._tokens(text)))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()
