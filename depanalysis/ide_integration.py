"""
IDE Integration Foundation.

Provides real-time architectural feedback while coding.
Foundation for Language Server Protocol (LSP) integration with VS Code, PyCharm, etc.

Features:
- Hotspot warnings (high churn + complexity files)
- Coupling alerts (high dependency modules)
- Circular dependency detection
- Code ownership context
"""
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from depanalysis.db_manager import DatabaseManager


@dataclass
class FileInsight:
    """Architectural insights for a specific file."""

    file_path: str
    is_hotspot: bool
    hotspot_score: Optional[float]
    churn: Optional[int]
    complexity: Optional[float]
    efferent_coupling: Optional[int]
    afferent_coupling: Optional[int]
    last_modified_by: Optional[str]
    last_modified_date: Optional[str]
    circular_dependencies: list[str]
    warnings: list[str]
    suggestions: list[str]


@dataclass
class ModuleInsight:
    """Architectural insights for a module/class."""

    module_name: str
    file_path: str
    instability: float
    coupling_score: float
    dependents: list[str]
    dependencies: list[str]
    warnings: list[str]


class IDEIntegration:
    """Provides architectural insights for IDE integration."""

    def __init__(self, repo_name: str, db_manager: DatabaseManager):
        """
        Initialize IDE integration.

        Args:
            repo_name: Repository name
            db_manager: DatabaseManager instance
        """
        self.repo_name = repo_name
        self.db_manager = db_manager

    def get_file_insights(self, file_path: str) -> FileInsight:
        """
        Get architectural insights for a file.

        Args:
            file_path: Path to file (relative to repo root)

        Returns:
            FileInsight with warnings and suggestions
        """
        warnings = []
        suggestions = []

        # Get structure metrics
        struct_conn = self.db_manager.get_connection(self.repo_name, "structure")
        struct_cursor = struct_conn.cursor()

        # Get module info
        module_info = struct_cursor.execute(
            """
            SELECT id, file_path, lines_of_code
            FROM modules
            WHERE file_path = ?
        """,
            (file_path,),
        ).fetchone()

        efferent_coupling = None
        afferent_coupling = None
        complexity = None

        if module_info:
            module_id = module_info[0]

            # Efferent coupling (outgoing)
            efferent_coupling = struct_cursor.execute(
                """
                SELECT COUNT(DISTINCT target_module_id)
                FROM imports
                WHERE source_module_id = ?
            """,
                (module_id,),
            ).fetchone()[0]

            # Afferent coupling (incoming)
            afferent_coupling = struct_cursor.execute(
                """
                SELECT COUNT(DISTINCT source_module_id)
                FROM imports
                WHERE target_module_id = ?
            """,
                (module_id,),
            ).fetchone()[0]

            # Average complexity
            complexity = struct_cursor.execute(
                """
                SELECT AVG(cyclomatic_complexity)
                FROM functions
                WHERE module_id = ? AND cyclomatic_complexity > 0
            """,
                (module_id,),
            ).fetchone()[0]

            # Check for high coupling
            if efferent_coupling and efferent_coupling > 10:
                warnings.append(f"High efferent coupling ({efferent_coupling} outgoing dependencies)")
                suggestions.append("Consider extracting interfaces or using dependency injection")

            if complexity and complexity > 10:
                warnings.append(f"High average complexity ({complexity:.1f})")
                suggestions.append("Consider breaking down complex functions")

        struct_conn.close()

        # Get temporal metrics
        hist_conn = self.db_manager.get_connection(self.repo_name, "history")
        hist_cursor = hist_conn.cursor()

        churn = None
        last_modified_by = None
        last_modified_date = None

        # Get churn
        churn_info = hist_cursor.execute(
            """
            SELECT total_churn, total_commits
            FROM churn_metrics
            WHERE file_path = ?
        """,
            (file_path,),
        ).fetchone()

        if churn_info:
            churn = churn_info[0]
            commits = churn_info[1]

            if churn > 100:
                warnings.append(f"High churn ({churn} total changes across {commits} commits)")
                suggestions.append("Consider stabilizing this module - frequent changes indicate potential issues")

        # Get last author
        last_commit = hist_cursor.execute(
            """
            SELECT a.name, c.timestamp
            FROM file_changes fc
            JOIN commits c ON fc.commit_id = c.id
            JOIN authors a ON c.author_id = a.id
            WHERE fc.file_path = ?
            ORDER BY c.timestamp DESC
            LIMIT 1
        """,
            (file_path,),
        ).fetchone()

        if last_commit:
            last_modified_by = last_commit[0]
            last_modified_date = last_commit[1]

        hist_conn.close()

        # Determine if hotspot
        is_hotspot = False
        hotspot_score = None

        if churn and complexity:
            # Simple hotspot heuristic: high churn + high complexity
            normalized_churn = min(churn / 100.0, 1.0)
            normalized_complexity = min((complexity or 0) / 20.0, 1.0)
            hotspot_score = (normalized_churn + normalized_complexity) / 2.0

            if hotspot_score > 0.7:
                is_hotspot = True
                warnings.append(f"⚠️  HOTSPOT: High churn + high complexity (score: {hotspot_score:.2f})")
                suggestions.append("This file is a maintenance hotspot - prioritize for refactoring")

        return FileInsight(
            file_path=file_path,
            is_hotspot=is_hotspot,
            hotspot_score=hotspot_score,
            churn=churn,
            complexity=complexity,
            efferent_coupling=efferent_coupling,
            afferent_coupling=afferent_coupling,
            last_modified_by=last_modified_by,
            last_modified_date=last_modified_date,
            circular_dependencies=[],  # Would be populated by cycle detection
            warnings=warnings,
            suggestions=suggestions,
        )

    def get_import_impact(self, source_file: str, target_module: str) -> dict[str, Any]:
        """
        Analyze impact of adding an import.

        Args:
            source_file: File that will import
            target_module: Module to be imported

        Returns:
            Dictionary with impact assessment
        """
        struct_conn = self.db_manager.get_connection(self.repo_name, "structure")
        cursor = struct_conn.cursor()

        # Check if import already exists
        existing = cursor.execute(
            """
            SELECT 1
            FROM imports i
            JOIN modules source ON i.source_module_id = source.id
            JOIN modules target ON i.target_module_id = target.id
            WHERE source.file_path = ? AND target.file_path LIKE ?
        """,
            (source_file, f"%{target_module}%"),
        ).fetchone()

        if existing:
            struct_conn.close()
            return {"status": "existing", "message": "Import already exists"}

        # Get current coupling
        source_module = cursor.execute("SELECT id FROM modules WHERE file_path = ?", (source_file,)).fetchone()

        if not source_module:
            struct_conn.close()
            return {"status": "error", "message": "Source file not in database"}

        current_coupling = cursor.execute(
            "SELECT COUNT(DISTINCT target_module_id) FROM imports WHERE source_module_id = ?",
            (source_module[0],),
        ).fetchone()[0]

        struct_conn.close()

        # Calculate new coupling
        new_coupling = current_coupling + 1
        coupling_increase = ((new_coupling - current_coupling) / max(current_coupling, 1)) * 100

        # Assess impact
        impact_level = "low"
        message = f"Adding import will increase coupling from {current_coupling} to {new_coupling}"

        if new_coupling > 20:
            impact_level = "high"
            message += " ⚠️  High coupling - consider refactoring"
        elif new_coupling > 10:
            impact_level = "medium"
            message += " ⚠️  Moderate coupling"

        return {
            "status": "new",
            "current_coupling": current_coupling,
            "new_coupling": new_coupling,
            "coupling_increase_percent": coupling_increase,
            "impact_level": impact_level,
            "message": message,
        }

    def format_file_insights_for_ide(self, insights: FileInsight) -> str:
        """
        Format file insights for IDE display (hover tooltip, status bar, etc.).

        Args:
            insights: FileInsight object

        Returns:
            Formatted string for IDE
        """
        lines = []

        # Header
        if insights.is_hotspot:
            lines.append("🔥 MAINTENANCE HOTSPOT")
        else:
            lines.append("📊 Architectural Insights")

        lines.append("")

        # Metrics
        if insights.churn is not None:
            lines.append(f"Churn: {insights.churn} changes")

        if insights.complexity is not None:
            lines.append(f"Avg Complexity: {insights.complexity:.1f}")

        if insights.efferent_coupling is not None:
            lines.append(f"Dependencies: {insights.efferent_coupling} outgoing")

        if insights.afferent_coupling is not None:
            lines.append(f"Dependents: {insights.afferent_coupling} incoming")

        if insights.last_modified_by:
            lines.append(f"Last modified by: {insights.last_modified_by}")

        # Warnings
        if insights.warnings:
            lines.append("")
            lines.append("⚠️  Warnings:")
            for warning in insights.warnings:
                lines.append(f"  • {warning}")

        # Suggestions
        if insights.suggestions:
            lines.append("")
            lines.append("💡 Suggestions:")
            for suggestion in insights.suggestions:
                lines.append(f"  • {suggestion}")

        return "\n".join(lines)


class LSPServer:
    """
    Foundation for Language Server Protocol integration.

    This is a minimal LSP server foundation that can be extended
    to provide real-time architectural feedback in IDEs.

    For full LSP implementation, use python-lsp-server or pygls.
    """

    def __init__(self, repo_name: str, db_manager: DatabaseManager):
        """
        Initialize LSP server.

        Args:
            repo_name: Repository name
            db_manager: DatabaseManager instance
        """
        self.integration = IDEIntegration(repo_name, db_manager)

    def on_hover(self, file_path: str, line: int, column: int) -> Optional[str]:
        """
        Handle hover request from IDE.

        Args:
            file_path: File being hovered over
            line: Line number
            column: Column number

        Returns:
            Hover content (markdown string)
        """
        insights = self.integration.get_file_insights(file_path)
        return self.integration.format_file_insights_for_ide(insights)

    def on_diagnostic(self, file_path: str) -> list[dict[str, Any]]:
        """
        Provide diagnostics (warnings/errors) for a file.

        Args:
            file_path: File to diagnose

        Returns:
            List of LSP diagnostic objects
        """
        insights = self.integration.get_file_insights(file_path)

        diagnostics = []

        for warning in insights.warnings:
            diagnostics.append(
                {
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}},
                    "severity": 2,  # Warning
                    "source": "depanalysis",
                    "message": warning,
                }
            )

        return diagnostics
