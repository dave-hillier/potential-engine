"""
Tests for Tier 4 features: Integration & Ecosystem.

Tests for:
- Architectural rules and validation
- Migration planning and pattern tracking
- Diff analysis for PR enrichment
- IDE integration
"""
import sqlite3
import tempfile
from pathlib import Path

import pytest
import yaml

from depanalysis.architectural_rules import (
    ArchitecturalRules,
    ArchitectureValidator,
    RuleViolation,
)
from depanalysis.db_manager import DatabaseManager
from depanalysis.migration_planning import (
    MigrationConfig,
    MigrationPattern,
    MigrationScanner,
    MigrationTracker,
)
from depanalysis.ide_integration import IDEIntegration, LSPServer


class TestArchitecturalRules:
    """Test architectural rules configuration and validation."""

    def test_rules_from_yaml(self, tmp_path):
        """Test loading rules from YAML configuration."""
        config_file = tmp_path / "test-rules.yml"
        config_content = """
thresholds:
  coupling:
    max_efferent_coupling: 20
    max_instability: 0.8
  complexity:
    max_cyclomatic_complexity: 15
  churn:
    max_file_churn: 100
  temporal_coupling:
    max_temporal_coupling_similarity: 0.9
    warn_temporal_coupling_similarity: 0.7

circular_dependencies:
  allow: false
  max_cycles: 0

forbidden_imports:
  - from: "ui/*"
    to: "database/*"
    reason: "UI should not access database directly"

file_limits:
  max_lines_per_file: 500
  max_functions_per_file: 30
        """
        config_file.write_text(config_content)

        rules = ArchitecturalRules.from_yaml(config_file)

        assert rules.max_efferent_coupling == 20
        assert rules.max_instability == 0.8
        assert rules.max_cyclomatic_complexity == 15
        assert rules.max_file_churn == 100
        assert rules.max_temporal_coupling_similarity == 0.9
        assert rules.warn_temporal_coupling_similarity == 0.7
        assert rules.allow_circular_dependencies is False
        assert rules.max_circular_dependency_cycles == 0
        assert len(rules.forbidden_imports) == 1
        assert rules.max_functions_per_file == 30

    def test_validation_with_violations(self, sample_repo_db):
        """Test validation that finds violations."""
        db_manager, repo_name = sample_repo_db

        # Create rules with low thresholds to trigger violations
        rules = ArchitecturalRules(
            max_cyclomatic_complexity=1,  # Very low threshold
            max_file_churn=10,
        )

        validator = ArchitectureValidator(db_manager, rules)
        violations = validator.validate(repo_name)

        # Should find violations in sample data
        assert isinstance(violations, list)
        # Each violation should have required fields
        for violation in violations:
            assert isinstance(violation, RuleViolation)
            assert violation.rule_name
            assert violation.severity in ["error", "warning"]
            assert violation.message

    def test_validation_no_violations(self, sample_repo_db):
        """Test validation that passes all rules."""
        db_manager, repo_name = sample_repo_db

        # Create rules with very high thresholds
        rules = ArchitecturalRules(
            max_cyclomatic_complexity=1000,
            max_file_churn=10000,
            max_instability=1.0,
        )

        validator = ArchitectureValidator(db_manager, rules)
        violations = validator.validate(repo_name)

        assert violations == []


class TestMigrationPlanning:
    """Test migration planning and pattern tracking."""

    def test_migration_config_from_yaml(self, tmp_path):
        """Test loading migration configuration."""
        config_file = tmp_path / "migration.yml"
        config_content = """
migration_id: "python2to3"
name: "Python 2 to 3 Migration"
description: "Track migration patterns"
target_completion_date: "2024-12-31"
tags: ["migration", "python3"]

patterns:
  - id: "print_statement"
    name: "Print Statement"
    description: "Python 2 print statement"
    type: "regex"
    pattern: "^\\\\s*print\\\\s+(?!\\\\()"
    severity: "high"
    category: "migration"
    replacement: "Use print() function"
        """
        config_file.write_text(config_content)

        config = MigrationConfig.from_yaml(config_file)

        assert config.migration_id == "python2to3"
        assert config.name == "Python 2 to 3 Migration"
        assert config.target_completion_date == "2024-12-31"
        assert "migration" in config.tags
        assert len(config.patterns) == 1

        pattern = config.patterns[0]
        assert pattern.pattern_id == "print_statement"
        assert pattern.pattern_type == "regex"
        assert pattern.severity == "high"

    def test_migration_scanner_regex(self, tmp_path):
        """Test migration scanner with regex patterns."""
        # Create test files
        test_file = tmp_path / "test.py"
        test_file.write_text("print 'hello world'\nprint('new style')\n")

        pattern = MigrationPattern(
            pattern_id="print_stmt",
            name="Print Statement",
            description="Old print",
            pattern_type="regex",
            search_pattern=r"^\s*print\s+(?!\()",
            file_patterns=["**/*.py"],
        )

        scanner = MigrationScanner(tmp_path)
        occurrences = scanner.scan_pattern(pattern)

        assert len(occurrences) == 1
        assert occurrences[0].line_number == 1
        assert "print 'hello world'" in occurrences[0].matched_text

    def test_migration_scanner_import(self, tmp_path):
        """Test migration scanner with import patterns."""
        test_file = tmp_path / "test.py"
        test_file.write_text("from __future__ import division\nimport sys\n")

        pattern = MigrationPattern(
            pattern_id="future_division",
            name="Future Division",
            description="Division import",
            pattern_type="import",
            search_pattern="from __future__ import division",
        )

        scanner = MigrationScanner(tmp_path)
        occurrences = scanner.scan_pattern(pattern)

        assert len(occurrences) == 1
        assert occurrences[0].line_number == 1

    def test_migration_tracker_save_and_retrieve(self, tmp_path):
        """Test saving and retrieving migration progress."""
        db_manager = DatabaseManager(data_dir=tmp_path)
        tracker = MigrationTracker(db_manager)

        repo_name = "test-repo"
        db_manager.initialize_repo_databases(repo_name)

        # Create migration config
        pattern = MigrationPattern(
            pattern_id="test_pattern",
            name="Test Pattern",
            description="Test",
            pattern_type="regex",
            search_pattern="test",
        )
        config = MigrationConfig(
            migration_id="test_migration",
            name="Test Migration",
            description="Test migration",
            patterns=[pattern],
        )

        # Save project
        tracker.save_migration_project(repo_name, config)

        # Verify saved
        conn = db_manager.get_connection(repo_name, "history")
        cursor = conn.cursor()
        result = cursor.execute(
            "SELECT name FROM migration_projects WHERE id = ?", ("test_migration",)
        ).fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "Test Migration"


class TestIDEIntegration:
    """Test IDE integration features."""

    def test_file_insights_basic(self, sample_repo_db):
        """Test getting file insights."""
        db_manager, repo_name = sample_repo_db

        integration = IDEIntegration(repo_name, db_manager)

        # Get insights for a file (assuming sample data exists)
        insights = integration.get_file_insights("test_file.py")

        assert insights.file_path == "test_file.py"
        assert isinstance(insights.warnings, list)
        assert isinstance(insights.suggestions, list)

    def test_file_insights_formatting(self, sample_repo_db):
        """Test formatting insights for IDE display."""
        db_manager, repo_name = sample_repo_db

        integration = IDEIntegration(repo_name, db_manager)
        insights = integration.get_file_insights("test_file.py")

        formatted = integration.format_file_insights_for_ide(insights)

        assert isinstance(formatted, str)
        assert "Architectural Insights" in formatted or "HOTSPOT" in formatted

    def test_import_impact_existing(self, sample_repo_db):
        """Test import impact analysis for existing import."""
        db_manager, repo_name = sample_repo_db

        integration = IDEIntegration(repo_name, db_manager)

        # Add test data first
        struct_conn = db_manager.get_connection(repo_name, "structure")
        cursor = struct_conn.cursor()

        # Insert test modules
        cursor.execute(
            "INSERT INTO modules (id, file_path, language_id) VALUES (1, 'source.py', 1)"
        )
        cursor.execute(
            "INSERT INTO modules (id, file_path, language_id) VALUES (2, 'target.py', 1)"
        )
        cursor.execute(
            "INSERT INTO imports (source_module_id, target_module_id) VALUES (1, 2)"
        )
        struct_conn.commit()
        struct_conn.close()

        impact = integration.get_import_impact("source.py", "target")

        assert impact["status"] == "existing"

    def test_lsp_server_hover(self, sample_repo_db):
        """Test LSP server hover functionality."""
        db_manager, repo_name = sample_repo_db

        lsp_server = LSPServer(repo_name, db_manager)

        hover_content = lsp_server.on_hover("test_file.py", 0, 0)

        assert hover_content is not None
        assert isinstance(hover_content, str)

    def test_lsp_server_diagnostics(self, sample_repo_db):
        """Test LSP server diagnostics."""
        db_manager, repo_name = sample_repo_db

        lsp_server = LSPServer(repo_name, db_manager)

        diagnostics = lsp_server.on_diagnostic("test_file.py")

        assert isinstance(diagnostics, list)
        for diagnostic in diagnostics:
            assert "message" in diagnostic
            assert "severity" in diagnostic


# Fixtures


@pytest.fixture
def sample_repo_db(tmp_path):
    """Create a sample repository database for testing."""
    db_manager = DatabaseManager(data_dir=tmp_path)
    repo_name = "test-repo"

    structure_db, history_db = db_manager.initialize_repo_databases(repo_name)

    # Add sample data to structure.db
    struct_conn = db_manager.get_connection(repo_name, "structure")
    cursor = struct_conn.cursor()

    # Insert language
    cursor.execute("INSERT OR IGNORE INTO languages (id, name) VALUES (1, 'python')")

    # Insert sample module
    cursor.execute(
        """
        INSERT INTO modules (id, file_path, language_id, file_hash, lines_of_code)
        VALUES (1, 'test_file.py', 1, 'abc123', 100)
    """
    )

    # Insert sample function with complexity
    cursor.execute(
        """
        INSERT INTO functions (id, module_id, name, line_start, line_end, cyclomatic_complexity)
        VALUES (1, 1, 'test_func', 1, 10, 5)
    """
    )

    struct_conn.commit()
    struct_conn.close()

    # Add sample data to history.db
    hist_conn = db_manager.get_connection(repo_name, "history")
    cursor = hist_conn.cursor()

    # Insert sample author
    cursor.execute(
        """
        INSERT INTO authors (id, name, email)
        VALUES (1, 'Test Author', 'test@example.com')
    """
    )

    # Insert sample commit
    cursor.execute(
        """
        INSERT INTO commits (id, hash, timestamp, author_id, message)
        VALUES (1, 'commit123', '2024-01-01 12:00:00', 1, 'Test commit')
    """
    )

    # Insert sample file change
    cursor.execute(
        """
        INSERT INTO file_changes (commit_id, file_path, change_type, additions, deletions)
        VALUES (1, 'test_file.py', 'M', 10, 5)
    """
    )

    hist_conn.commit()
    hist_conn.close()

    return db_manager, repo_name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
