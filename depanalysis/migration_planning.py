"""
Migration Planning and Pattern Tracking.

Tracks large refactoring efforts across the codebase:
- Python 2 → 3 migrations
- Framework migrations (Flask → FastAPI, etc.)
- Deprecation tracking (old API → new API)
- Monolith → Microservices extraction
"""
import ast
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from depanalysis.db_manager import DatabaseManager


@dataclass
class MigrationPattern:
    """Defines a pattern to search for in migration tracking."""

    pattern_id: str
    name: str
    description: str
    pattern_type: str  # 'ast', 'regex', 'import', 'call'
    search_pattern: str
    file_patterns: list[str] = field(default_factory=lambda: ["**/*.py"])
    severity: str = "info"  # 'critical', 'high', 'medium', 'low', 'info'
    category: str = "general"  # 'migration', 'deprecation', 'refactoring'
    replacement_suggestion: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MigrationPattern":
        """Create MigrationPattern from dictionary."""
        return cls(
            pattern_id=data["id"],
            name=data["name"],
            description=data["description"],
            pattern_type=data["type"],
            search_pattern=data["pattern"],
            file_patterns=data.get("file_patterns", ["**/*.py"]),
            severity=data.get("severity", "info"),
            category=data.get("category", "general"),
            replacement_suggestion=data.get("replacement"),
        )


@dataclass
class MigrationOccurrence:
    """Represents an occurrence of a migration pattern."""

    pattern_id: str
    file_path: str
    line_number: int
    matched_text: str
    context: Optional[str] = None


@dataclass
class MigrationConfig:
    """Configuration for a migration tracking project."""

    migration_id: str
    name: str
    description: str
    patterns: list[MigrationPattern]
    target_completion_date: Optional[str] = None
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "MigrationConfig":
        """
        Load migration configuration from YAML file.

        Example YAML:
            migration_id: "python2to3"
            name: "Python 2 to 3 Migration"
            description: "Track migration from Python 2 to Python 3"
            target_completion_date: "2024-12-31"
            tags: ["migration", "python3"]

            patterns:
              - id: "print_statement"
                name: "Print Statement"
                description: "Python 2 print statement (should be print())"
                type: "regex"
                pattern: "^\\s*print\\s+(?!\\()"
                severity: "high"
                category: "migration"
                replacement: "Use print() function"

              - id: "old_division"
                name: "Classic Division"
                description: "Python 2 division behavior"
                type: "regex"
                pattern: "from __future__ import division"
                severity: "medium"

              - id: "unicode_literals"
                name: "Unicode Literals Import"
                description: "Check for unicode_literals import"
                type: "import"
                pattern: "from __future__ import unicode_literals"
                severity: "low"
        """
        with open(yaml_path) as f:
            config = yaml.safe_load(f)

        patterns = [MigrationPattern.from_dict(p) for p in config.get("patterns", [])]

        return cls(
            migration_id=config["migration_id"],
            name=config["name"],
            description=config["description"],
            patterns=patterns,
            target_completion_date=config.get("target_completion_date"),
            tags=config.get("tags", []),
        )


class MigrationScanner:
    """Scans codebase for migration patterns."""

    def __init__(self, repo_path: Path):
        """
        Initialize migration scanner.

        Args:
            repo_path: Path to repository root
        """
        self.repo_path = repo_path

    def scan_pattern(self, pattern: MigrationPattern) -> list[MigrationOccurrence]:
        """
        Scan for a specific migration pattern.

        Args:
            pattern: MigrationPattern to search for

        Returns:
            List of MigrationOccurrence objects
        """
        occurrences = []

        # Find matching files
        matching_files = []
        for file_pattern in pattern.file_patterns:
            matching_files.extend(self.repo_path.glob(file_pattern))

        # Deduplicate
        matching_files = list(set(matching_files))

        for file_path in matching_files:
            if not file_path.is_file():
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")

                if pattern.pattern_type == "regex":
                    occurrences.extend(self._scan_regex(pattern, file_path, lines))
                elif pattern.pattern_type == "import":
                    occurrences.extend(self._scan_import(pattern, file_path, content))
                elif pattern.pattern_type == "ast":
                    occurrences.extend(self._scan_ast(pattern, file_path, content))
                elif pattern.pattern_type == "call":
                    occurrences.extend(self._scan_call(pattern, file_path, content))

            except (UnicodeDecodeError, OSError):
                # Skip files that can't be read
                continue

        return occurrences

    def _scan_regex(
        self, pattern: MigrationPattern, file_path: Path, lines: list[str]
    ) -> list[MigrationOccurrence]:
        """Scan using regex pattern."""
        occurrences = []
        regex = re.compile(pattern.search_pattern, re.MULTILINE)

        for line_num, line in enumerate(lines, start=1):
            if regex.search(line):
                # Get context (3 lines before and after)
                start_line = max(0, line_num - 4)
                end_line = min(len(lines), line_num + 3)
                context = "\n".join(lines[start_line:end_line])

                rel_path = file_path.relative_to(self.repo_path)
                occurrences.append(
                    MigrationOccurrence(
                        pattern_id=pattern.pattern_id,
                        file_path=str(rel_path),
                        line_number=line_num,
                        matched_text=line.strip(),
                        context=context,
                    )
                )

        return occurrences

    def _scan_import(
        self, pattern: MigrationPattern, file_path: Path, content: str
    ) -> list[MigrationOccurrence]:
        """Scan for import statements using AST."""
        occurrences = []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return occurrences

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                import_line = f"from {node.module} import {', '.join(alias.name for alias in node.names)}"
                if pattern.search_pattern in import_line:
                    rel_path = file_path.relative_to(self.repo_path)
                    occurrences.append(
                        MigrationOccurrence(
                            pattern_id=pattern.pattern_id,
                            file_path=str(rel_path),
                            line_number=node.lineno,
                            matched_text=import_line,
                        )
                    )
            elif isinstance(node, ast.Import):
                import_line = f"import {', '.join(alias.name for alias in node.names)}"
                if pattern.search_pattern in import_line:
                    rel_path = file_path.relative_to(self.repo_path)
                    occurrences.append(
                        MigrationOccurrence(
                            pattern_id=pattern.pattern_id,
                            file_path=str(rel_path),
                            line_number=node.lineno,
                            matched_text=import_line,
                        )
                    )

        return occurrences

    def _scan_ast(
        self, pattern: MigrationPattern, file_path: Path, content: str
    ) -> list[MigrationOccurrence]:
        """Scan using AST node type patterns."""
        # This is a simplified implementation
        # Could be extended to match specific AST patterns
        return []

    def _scan_call(
        self, pattern: MigrationPattern, file_path: Path, content: str
    ) -> list[MigrationOccurrence]:
        """Scan for function/method calls."""
        occurrences = []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return occurrences

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Get function name
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                else:
                    continue

                if pattern.search_pattern in func_name:
                    rel_path = file_path.relative_to(self.repo_path)
                    occurrences.append(
                        MigrationOccurrence(
                            pattern_id=pattern.pattern_id,
                            file_path=str(rel_path),
                            line_number=node.lineno,
                            matched_text=func_name,
                        )
                    )

        return occurrences


class MigrationTracker:
    """Tracks migration progress over time."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize migration tracker.

        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager

    def initialize_migration_tracking(self, repo_name: str) -> None:
        """
        Initialize migration tracking tables in the database.

        Args:
            repo_name: Name of the repository
        """
        conn = self.db_manager.get_connection(repo_name, "history")
        cursor = conn.cursor()

        # Migration projects table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS migration_projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                target_date TEXT,
                created_at TEXT NOT NULL,
                tags TEXT
            )
        """
        )

        # Migration patterns table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS migration_patterns (
                id TEXT PRIMARY KEY,
                migration_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                pattern_type TEXT NOT NULL,
                search_pattern TEXT NOT NULL,
                severity TEXT,
                category TEXT,
                FOREIGN KEY (migration_id) REFERENCES migration_projects(id)
            )
        """
        )

        # Migration occurrences table (snapshot at each scan)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS migration_occurrences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                line_number INTEGER NOT NULL,
                matched_text TEXT,
                scanned_at TEXT NOT NULL,
                commit_hash TEXT,
                FOREIGN KEY (pattern_id) REFERENCES migration_patterns(id)
            )
        """
        )

        # Migration progress view
        cursor.execute(
            """
            CREATE VIEW IF NOT EXISTS migration_progress AS
            SELECT
                mp.migration_id,
                mp.id as pattern_id,
                mp.name as pattern_name,
                mp.severity,
                COUNT(mo.id) as occurrence_count,
                COUNT(DISTINCT mo.file_path) as affected_files,
                MAX(mo.scanned_at) as last_scan
            FROM migration_patterns mp
            LEFT JOIN migration_occurrences mo ON mp.id = mo.pattern_id
            GROUP BY mp.migration_id, mp.id, mp.name, mp.severity
        """
        )

        conn.commit()
        conn.close()

    def save_migration_project(
        self, repo_name: str, config: MigrationConfig, commit_hash: Optional[str] = None
    ) -> None:
        """
        Save migration project and scan results to database.

        Args:
            repo_name: Name of the repository
            config: MigrationConfig with patterns
            commit_hash: Optional Git commit hash for tracking
        """
        self.initialize_migration_tracking(repo_name)
        conn = self.db_manager.get_connection(repo_name, "history")
        cursor = conn.cursor()

        # Save migration project
        cursor.execute(
            """
            INSERT OR REPLACE INTO migration_projects
            (id, name, description, target_date, created_at, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                config.migration_id,
                config.name,
                config.description,
                config.target_completion_date,
                datetime.now().isoformat(),
                ",".join(config.tags),
            ),
        )

        # Save patterns
        for pattern in config.patterns:
            cursor.execute(
                """
                INSERT OR REPLACE INTO migration_patterns
                (id, migration_id, name, description, pattern_type, search_pattern, severity, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    pattern.pattern_id,
                    config.migration_id,
                    pattern.name,
                    pattern.description,
                    pattern.pattern_type,
                    pattern.search_pattern,
                    pattern.severity,
                    pattern.category,
                ),
            )

        conn.commit()
        conn.close()

    def save_scan_results(
        self, repo_name: str, occurrences: list[MigrationOccurrence], commit_hash: Optional[str] = None
    ) -> None:
        """
        Save scan results to database.

        Args:
            repo_name: Name of the repository
            occurrences: List of MigrationOccurrence objects
            commit_hash: Optional Git commit hash
        """
        conn = self.db_manager.get_connection(repo_name, "history")
        cursor = conn.cursor()

        scan_time = datetime.now().isoformat()

        for occ in occurrences:
            cursor.execute(
                """
                INSERT INTO migration_occurrences
                (pattern_id, file_path, line_number, matched_text, scanned_at, commit_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (occ.pattern_id, occ.file_path, occ.line_number, occ.matched_text, scan_time, commit_hash),
            )

        conn.commit()
        conn.close()

    def get_migration_progress(self, repo_name: str, migration_id: str) -> dict[str, Any]:
        """
        Get progress summary for a migration project.

        Args:
            repo_name: Name of the repository
            migration_id: Migration project ID

        Returns:
            Dictionary with progress statistics
        """
        conn = self.db_manager.get_connection(repo_name, "history")
        cursor = conn.cursor()

        # Get total occurrences
        total = cursor.execute(
            """
            SELECT COUNT(DISTINCT mo.id)
            FROM migration_occurrences mo
            JOIN migration_patterns mp ON mo.pattern_id = mp.id
            WHERE mp.migration_id = ?
        """,
            (migration_id,),
        ).fetchone()[0]

        # Get by severity
        by_severity = {}
        rows = cursor.execute(
            """
            SELECT mp.severity, COUNT(DISTINCT mo.id)
            FROM migration_occurrences mo
            JOIN migration_patterns mp ON mo.pattern_id = mp.id
            WHERE mp.migration_id = ?
            GROUP BY mp.severity
        """,
            (migration_id,),
        ).fetchall()

        for severity, count in rows:
            by_severity[severity] = count

        # Get affected files
        affected_files = cursor.execute(
            """
            SELECT COUNT(DISTINCT mo.file_path)
            FROM migration_occurrences mo
            JOIN migration_patterns mp ON mo.pattern_id = mp.id
            WHERE mp.migration_id = ?
        """,
            (migration_id,),
        ).fetchone()[0]

        conn.close()

        return {
            "migration_id": migration_id,
            "total_occurrences": total,
            "by_severity": by_severity,
            "affected_files": affected_files,
        }
