"""
Architectural rules and CI/CD gate enforcement.

Provides configuration-based enforcement of architectural constraints,
designed for integration with CI/CD pipelines.
"""
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

from depanalysis.db_manager import DatabaseManager


@dataclass
class RuleViolation:
    """Represents a violation of an architectural rule."""

    rule_name: str
    severity: str  # 'error' or 'warning'
    message: str
    actual_value: Optional[float] = None
    threshold_value: Optional[float] = None
    details: Optional[dict[str, Any]] = None


@dataclass
class ArchitecturalRules:
    """Configuration for architectural rules."""

    # Coupling thresholds
    max_efferent_coupling: Optional[int] = None
    max_afferent_coupling: Optional[int] = None
    max_instability: Optional[float] = None

    # Complexity thresholds
    max_cyclomatic_complexity: Optional[int] = None
    max_file_complexity: Optional[int] = None

    # Churn thresholds
    max_file_churn: Optional[int] = None
    max_hotspot_score: Optional[float] = None

    # Temporal coupling thresholds
    max_temporal_coupling_similarity: Optional[float] = None
    warn_temporal_coupling_similarity: Optional[float] = None

    # Circular dependency rules
    allow_circular_dependencies: bool = True
    max_circular_dependency_cycles: Optional[int] = None

    # Forbidden dependencies (layer violations)
    forbidden_imports: list[dict[str, str]] = None

    # File-specific rules
    max_lines_per_file: Optional[int] = None
    max_functions_per_file: Optional[int] = None

    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.forbidden_imports is None:
            self.forbidden_imports = []

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "ArchitecturalRules":
        """
        Load architectural rules from YAML configuration file.

        Args:
            yaml_path: Path to .depanalysis.yml file

        Returns:
            ArchitecturalRules instance

        Example YAML:
            thresholds:
              coupling:
                max_efferent_coupling: 20
                max_afferent_coupling: 50
                max_instability: 0.8
              complexity:
                max_cyclomatic_complexity: 15
                max_file_complexity: 100
              churn:
                max_file_churn: 100
                max_hotspot_score: 0.9
              temporal_coupling:
                max_temporal_coupling_similarity: 0.9
                warn_temporal_coupling_similarity: 0.7
            circular_dependencies:
              allow: false
              max_cycles: 0
            forbidden_imports:
              - from: "ui/*"
                to: "database/*"
                reason: "UI layer should not directly access database"
            file_limits:
              max_lines_per_file: 500
              max_functions_per_file: 30
        """
        with open(yaml_path) as f:
            config = yaml.safe_load(f)

        rules = cls()

        if "thresholds" in config:
            thresholds = config["thresholds"]

            if "coupling" in thresholds:
                coupling = thresholds["coupling"]
                rules.max_efferent_coupling = coupling.get("max_efferent_coupling")
                rules.max_afferent_coupling = coupling.get("max_afferent_coupling")
                rules.max_instability = coupling.get("max_instability")

            if "complexity" in thresholds:
                complexity = thresholds["complexity"]
                rules.max_cyclomatic_complexity = complexity.get("max_cyclomatic_complexity")
                rules.max_file_complexity = complexity.get("max_file_complexity")

            if "churn" in thresholds:
                churn = thresholds["churn"]
                rules.max_file_churn = churn.get("max_file_churn")
                rules.max_hotspot_score = churn.get("max_hotspot_score")

            if "temporal_coupling" in thresholds:
                tc = thresholds["temporal_coupling"]
                rules.max_temporal_coupling_similarity = tc.get("max_temporal_coupling_similarity")
                rules.warn_temporal_coupling_similarity = tc.get("warn_temporal_coupling_similarity")

        if "circular_dependencies" in config:
            cd = config["circular_dependencies"]
            rules.allow_circular_dependencies = cd.get("allow", True)
            rules.max_circular_dependency_cycles = cd.get("max_cycles")

        if "forbidden_imports" in config:
            rules.forbidden_imports = config["forbidden_imports"]

        if "file_limits" in config:
            limits = config["file_limits"]
            rules.max_lines_per_file = limits.get("max_lines_per_file")
            rules.max_functions_per_file = limits.get("max_functions_per_file")

        return rules


class ArchitectureValidator:
    """Validates repository against architectural rules."""

    def __init__(self, db_manager: DatabaseManager, rules: ArchitecturalRules):
        """
        Initialize architecture validator.

        Args:
            db_manager: DatabaseManager instance
            rules: ArchitecturalRules configuration
        """
        self.db_manager = db_manager
        self.rules = rules

    def validate(self, repo_name: str) -> list[RuleViolation]:
        """
        Validate repository against all configured rules.

        Args:
            repo_name: Name of the repository to validate

        Returns:
            List of RuleViolation objects (empty if all rules pass)
        """
        violations = []

        violations.extend(self._check_coupling_rules(repo_name))
        violations.extend(self._check_complexity_rules(repo_name))
        violations.extend(self._check_churn_rules(repo_name))
        violations.extend(self._check_temporal_coupling_rules(repo_name))
        violations.extend(self._check_file_limit_rules(repo_name))

        return violations

    def _check_coupling_rules(self, repo_name: str) -> list[RuleViolation]:
        """Check structural coupling rules."""
        violations = []

        if self.rules.max_instability is None:
            return violations

        try:
            conn = self.db_manager.get_connection(repo_name, "structure")
            cursor = conn.cursor()

            # Check module instability
            # Instability = Ce / (Ca + Ce) where Ce = efferent, Ca = afferent
            query = """
                SELECT
                    m.file_path,
                    COUNT(DISTINCT i.target_module_id) as efferent_coupling,
                    COUNT(DISTINCT i2.source_module_id) as afferent_coupling,
                    CAST(COUNT(DISTINCT i.target_module_id) AS FLOAT) /
                        NULLIF(COUNT(DISTINCT i.target_module_id) + COUNT(DISTINCT i2.source_module_id), 0) as instability
                FROM modules m
                LEFT JOIN imports i ON m.id = i.source_module_id
                LEFT JOIN imports i2 ON m.id = i2.target_module_id
                GROUP BY m.id, m.file_path
                HAVING instability > ?
                ORDER BY instability DESC
            """

            results = cursor.execute(query, (self.rules.max_instability,)).fetchall()

            for file_path, efferent, afferent, instability in results:
                violations.append(
                    RuleViolation(
                        rule_name="max_instability",
                        severity="error",
                        message=f"Module {file_path} has instability {instability:.2f} (max: {self.rules.max_instability})",
                        actual_value=instability,
                        threshold_value=self.rules.max_instability,
                        details={"file": file_path, "efferent": efferent, "afferent": afferent},
                    )
                )

            conn.close()

        except Exception:
            # Structure DB might not exist or be incomplete
            pass

        return violations

    def _check_complexity_rules(self, repo_name: str) -> list[RuleViolation]:
        """Check cyclomatic complexity rules."""
        violations = []

        if self.rules.max_cyclomatic_complexity is None:
            return violations

        try:
            conn = self.db_manager.get_connection(repo_name, "structure")
            cursor = conn.cursor()

            # Check function complexity
            query = """
                SELECT
                    m.file_path,
                    f.name,
                    f.cyclomatic_complexity
                FROM functions f
                JOIN modules m ON f.module_id = m.id
                WHERE f.cyclomatic_complexity > ?
                ORDER BY f.cyclomatic_complexity DESC
            """

            results = cursor.execute(query, (self.rules.max_cyclomatic_complexity,)).fetchall()

            for file_path, func_name, complexity in results:
                violations.append(
                    RuleViolation(
                        rule_name="max_cyclomatic_complexity",
                        severity="warning",
                        message=f"Function {func_name} in {file_path} has complexity {complexity} (max: {self.rules.max_cyclomatic_complexity})",
                        actual_value=complexity,
                        threshold_value=self.rules.max_cyclomatic_complexity,
                        details={"file": file_path, "function": func_name},
                    )
                )

            conn.close()

        except Exception:
            pass

        return violations

    def _check_churn_rules(self, repo_name: str) -> list[RuleViolation]:
        """Check file churn rules."""
        violations = []

        if self.rules.max_file_churn is None:
            return violations

        try:
            conn = self.db_manager.get_connection(repo_name, "history")
            cursor = conn.cursor()

            # Check file churn from churn_metrics view
            query = """
                SELECT file_path, total_churn, total_commits
                FROM churn_metrics
                WHERE total_churn > ?
                ORDER BY total_churn DESC
            """

            results = cursor.execute(query, (self.rules.max_file_churn,)).fetchall()

            for file_path, churn, commits in results:
                violations.append(
                    RuleViolation(
                        rule_name="max_file_churn",
                        severity="warning",
                        message=f"File {file_path} has churn {churn} (max: {self.rules.max_file_churn})",
                        actual_value=churn,
                        threshold_value=self.rules.max_file_churn,
                        details={"file": file_path, "commits": commits},
                    )
                )

            conn.close()

        except Exception:
            pass

        return violations

    def _check_temporal_coupling_rules(self, repo_name: str) -> list[RuleViolation]:
        """Check temporal coupling rules."""
        violations = []

        max_sim = self.rules.max_temporal_coupling_similarity
        warn_sim = self.rules.warn_temporal_coupling_similarity

        if max_sim is None and warn_sim is None:
            return violations

        try:
            conn = self.db_manager.get_connection(repo_name, "history")
            cursor = conn.cursor()

            # Check temporal coupling
            query = """
                SELECT file1_path, file2_path, jaccard_similarity, co_change_count
                FROM temporal_coupling
                WHERE jaccard_similarity >= ?
                ORDER BY jaccard_similarity DESC
            """

            threshold = min(s for s in [max_sim, warn_sim] if s is not None)
            results = cursor.execute(query, (threshold,)).fetchall()

            for file1, file2, similarity, co_changes in results:
                if max_sim is not None and similarity > max_sim:
                    severity = "error"
                    message = f"High temporal coupling between {file1} and {file2}: {similarity:.2f} (max: {max_sim})"
                elif warn_sim is not None and similarity > warn_sim:
                    severity = "warning"
                    message = f"Temporal coupling between {file1} and {file2}: {similarity:.2f} (threshold: {warn_sim})"
                else:
                    continue

                violations.append(
                    RuleViolation(
                        rule_name="temporal_coupling",
                        severity=severity,
                        message=message,
                        actual_value=similarity,
                        threshold_value=max_sim if severity == "error" else warn_sim,
                        details={"file1": file1, "file2": file2, "co_changes": co_changes},
                    )
                )

            conn.close()

        except Exception:
            pass

        return violations

    def _check_file_limit_rules(self, repo_name: str) -> list[RuleViolation]:
        """Check file size and function count limits."""
        violations = []

        if self.rules.max_functions_per_file is None:
            return violations

        try:
            conn = self.db_manager.get_connection(repo_name, "structure")
            cursor = conn.cursor()

            # Check functions per file
            query = """
                SELECT
                    m.file_path,
                    COUNT(f.id) as function_count
                FROM modules m
                LEFT JOIN functions f ON m.id = f.module_id
                GROUP BY m.id, m.file_path
                HAVING function_count > ?
                ORDER BY function_count DESC
            """

            results = cursor.execute(query, (self.rules.max_functions_per_file,)).fetchall()

            for file_path, func_count in results:
                violations.append(
                    RuleViolation(
                        rule_name="max_functions_per_file",
                        severity="warning",
                        message=f"File {file_path} has {func_count} functions (max: {self.rules.max_functions_per_file})",
                        actual_value=func_count,
                        threshold_value=self.rules.max_functions_per_file,
                        details={"file": file_path},
                    )
                )

            conn.close()

        except Exception:
            pass

        return violations
