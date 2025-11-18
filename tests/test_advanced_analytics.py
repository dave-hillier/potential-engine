"""
Tests for Tier 3 Advanced Analytics features.

Tests:
- Feature 7: Change Impact Analysis
- Feature 8: Architectural Pattern Detection
- Feature 9: Code Quality Trends
- Feature 10: Developer Productivity Insights
"""
import pytest
import sqlite3
import tempfile
from pathlib import Path

from depanalysis.db_manager import DatabaseManager
from depanalysis.advanced_analytics import (
    ChangeImpactAnalyzer,
    ArchitecturalPatternDetector,
    CodeQualityTrendsAnalyzer,
    DeveloperProductivityAnalyzer,
    AdvancedAnalyticsAPI
)


@pytest.fixture
def db_manager_with_data(tmp_path):
    """Create a database manager with sample data."""
    db_manager = DatabaseManager(data_dir=tmp_path / "data", schema_dir=Path("schema"))

    # Initialize databases
    struct_db, hist_db = db_manager.initialize_repo_databases("test-repo")

    # Populate structure.db with sample data
    struct_conn = db_manager.get_connection("test-repo", "structure")
    cursor = struct_conn.cursor()

    # Create some modules
    modules = [
        ("src/main.py", "main", "hash1"),
        ("src/utils.py", "utils", "hash2"),
        ("src/models.py", "models", "hash3"),
        ("tests/test_main.py", "test_main", "hash4"),
        ("src/api/routes.py", "routes", "hash5"),
        ("src/api/handlers.py", "handlers", "hash6"),
    ]

    for path, name, file_hash in modules:
        cursor.execute(
            "INSERT INTO modules (language_id, path, name, file_hash) VALUES (1, ?, ?, ?)",
            (path, name, file_hash)
        )

    # Create some classes
    cursor.execute(
        "INSERT INTO classes (module_id, name, kind, line_start, line_end) VALUES (3, 'User', 'class', 1, 50)"
    )
    cursor.execute(
        "INSERT INTO classes (module_id, name, kind, line_start, line_end) VALUES (3, 'Product', 'class', 52, 100)"
    )

    # Create some functions
    functions = [
        (1, None, "main", "function", 1, 10, 3),
        (1, None, "process_data", "function", 12, 25, 5),
        (2, None, "helper", "function", 1, 5, 2),
        (3, 1, "__init__", "constructor", 2, 5, 1),
        (3, 1, "save", "method", 7, 15, 4),
        (3, 1, "delete", "method", 17, 25, 3),
        (3, 1, "update", "method", 27, 35, 4),
        (3, 1, "validate", "method", 37, 45, 6),
    ]

    for mod_id, class_id, name, kind, line_start, line_end, complexity in functions:
        cursor.execute(
            """INSERT INTO functions
            (module_id, class_id, name, kind, line_start, line_end, cyclomatic_complexity)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (mod_id, class_id, name, kind, line_start, line_end, complexity)
        )

    # Create some imports
    imports = [
        (1, "utils", "utils", None),  # main imports utils
        (1, "models", "models", None),  # main imports models
        (4, "main", "main", None),  # test_main imports main
        (5, "models", "models", None),  # routes imports models
        (6, "models", "models", None),  # handlers imports models
        (5, "handlers", "handlers", None),  # routes imports handlers
    ]

    for from_id, to_mod, import_name, alias in imports:
        cursor.execute(
            """INSERT INTO imports
            (from_module_id, to_module, import_name, alias, import_kind, line_number)
            VALUES (?, ?, ?, ?, 'import', 1)""",
            (from_id, to_mod, import_name, alias)
        )

    struct_conn.commit()
    struct_conn.close()

    # Populate history.db with sample data
    hist_conn = db_manager.get_connection("test-repo", "history")
    cursor = hist_conn.cursor()

    # Create some commits
    commits = [
        ("a" * 40, "Alice", "alice@example.com", "2024-01-01 10:00:00", "Initial commit"),
        ("b" * 40, "Bob", "bob@example.com", "2024-01-02 10:00:00", "Add models"),
        ("c" * 40, "Alice", "alice@example.com", "2024-01-03 10:00:00", "Update main"),
        ("d" * 40, "Charlie", "charlie@example.com", "2024-01-04 10:00:00", "Add tests"),
        ("e" * 40, "Bob", "bob@example.com", "2024-01-05 10:00:00", "Refactor"),
    ]

    for commit_hash, author_name, author_email, timestamp, message in commits:
        cursor.execute(
            "INSERT INTO commits (hash, author_name, author_email, timestamp, message) VALUES (?, ?, ?, ?, ?)",
            (commit_hash, author_name, author_email, timestamp, message)
        )

    # Create authors
    authors = [
        ("Alice", "alice@example.com"),
        ("Bob", "bob@example.com"),
        ("Charlie", "charlie@example.com"),
    ]

    for name, email in authors:
        cursor.execute(
            "INSERT INTO authors (name, email) VALUES (?, ?)",
            (name, email)
        )

    # Create file changes
    file_changes = [
        (1, "src/main.py", 10, 0, "A"),
        (2, "src/models.py", 20, 0, "A"),
        (2, "src/main.py", 5, 2, "M"),
        (3, "src/main.py", 3, 1, "M"),
        (3, "src/utils.py", 15, 0, "A"),
        (4, "tests/test_main.py", 30, 0, "A"),
        (4, "src/main.py", 2, 1, "M"),
        (5, "src/models.py", 10, 5, "M"),
        (5, "src/main.py", 1, 1, "M"),
    ]

    for commit_id, file_path, lines_added, lines_deleted, change_type in file_changes:
        cursor.execute(
            """INSERT INTO file_changes
            (commit_id, file_path, lines_added, lines_deleted, change_type)
            VALUES (?, ?, ?, ?, ?)""",
            (commit_id, file_path, lines_added, lines_deleted, change_type)
        )

    # Create temporal coupling
    temporal_couplings = [
        ("src/main.py", "src/models.py", 3, 0.6),
        ("src/main.py", "src/utils.py", 2, 0.4),
    ]

    for file_a, file_b, co_change_count, similarity in temporal_couplings:
        cursor.execute(
            """INSERT INTO temporal_coupling
            (file_a, file_b, co_change_count, jaccard_similarity)
            VALUES (?, ?, ?, ?)""",
            (file_a, file_b, co_change_count, similarity)
        )

    # Create author ownership
    ownerships = [
        (1, "src/main.py", 3, 15),
        (2, "src/models.py", 2, 25),
        (1, "src/models.py", 1, 5),
        (3, "tests/test_main.py", 1, 30),
    ]

    for author_id, file_path, commit_count, lines_contributed in ownerships:
        cursor.execute(
            """INSERT INTO author_ownership
            (author_id, file_path, commit_count, lines_contributed)
            VALUES (?, ?, ?, ?)""",
            (author_id, file_path, commit_count, lines_contributed)
        )

    hist_conn.commit()
    hist_conn.close()

    return db_manager


# =============================================================================
# FEATURE 7: Change Impact Analysis Tests
# =============================================================================

def test_transitive_dependencies(db_manager_with_data):
    """Test transitive dependency closure calculation."""
    analyzer = ChangeImpactAnalyzer(db_manager_with_data)

    # Test for main.py which imports utils and models
    result = analyzer.get_transitive_dependencies("test-repo", "src/main.py")

    assert result["source_module"] == "src/main.py"
    assert result["total_dependencies"] >= 2  # At least utils and models
    assert 0 in result["by_depth"]
    assert "utils" in result["by_depth"][0] or "models" in result["by_depth"][0]


def test_reverse_dependencies(db_manager_with_data):
    """Test reverse dependency calculation."""
    analyzer = ChangeImpactAnalyzer(db_manager_with_data)

    # Test for models.py which is imported by multiple modules
    result = analyzer.get_reverse_dependencies("test-repo", "src/models.py")

    assert result["target_module"] == "src/models.py"
    assert result["total_dependents"] >= 1  # At least main.py imports models


def test_test_impact_analysis(db_manager_with_data):
    """Test impact analysis."""
    analyzer = ChangeImpactAnalyzer(db_manager_with_data)

    # Test for main.py which has test_main.py
    result = analyzer.get_test_impact("test-repo", "src/main.py")

    assert result["changed_file"] == "src/main.py"
    assert "total_test_files" in result
    assert isinstance(result["all_tests"], list)


def test_blast_radius(db_manager_with_data):
    """Test blast radius calculation combining structural and temporal coupling."""
    analyzer = ChangeImpactAnalyzer(db_manager_with_data)

    result = analyzer.get_blast_radius("test-repo", "src/main.py")

    assert result["module"] == "src/main.py"
    assert "total_affected_files" in result
    assert "high_risk_files" in result
    assert "hidden_dependencies" in result
    assert isinstance(result["temporal_details"], list)


# =============================================================================
# FEATURE 8: Architectural Pattern Detection Tests
# =============================================================================

def test_centrality_metrics(db_manager_with_data):
    """Test module centrality metrics calculation."""
    detector = ArchitecturalPatternDetector(db_manager_with_data)

    result = detector.calculate_centrality_metrics("test-repo")

    assert len(result) > 0
    assert "module_path" in result.columns
    assert "in_degree" in result.columns
    assert "out_degree" in result.columns
    assert "pagerank_score" in result.columns
    assert "is_hub" in result.columns

    # models.py should have high in_degree (many modules import it)
    models_row = result[result["module_path"] == "src/models.py"]
    if len(models_row) > 0:
        assert models_row.iloc[0]["in_degree"] >= 1


def test_layered_architecture_detection(db_manager_with_data):
    """Test layered architecture detection."""
    detector = ArchitecturalPatternDetector(db_manager_with_data)

    result = detector.detect_layered_architecture("test-repo")

    assert "layers" in result
    assert "layer_dependencies" in result
    assert "total_layers" in result
    assert result["total_layers"] >= 1

    # Should detect src and tests as separate layers
    assert "src" in result["layers"] or "tests" in result["layers"]


def test_god_classes_detection(db_manager_with_data):
    """Test God class detection."""
    detector = ArchitecturalPatternDetector(db_manager_with_data)

    # Use low thresholds for testing
    result = detector.detect_god_classes("test-repo", complexity_threshold=10, method_threshold=3)

    # User class has 4 methods with total complexity > 10
    assert len(result) >= 1
    assert "name" in result.columns
    assert "method_count" in result.columns
    assert "total_complexity" in result.columns


def test_shotgun_surgery_detection(db_manager_with_data):
    """Test shotgun surgery anti-pattern detection."""
    detector = ArchitecturalPatternDetector(db_manager_with_data)

    # Use low threshold for testing
    result = detector.detect_shotgun_surgery("test-repo", min_files=2)

    # Should find commits that changed multiple files
    assert isinstance(result, list)


# =============================================================================
# FEATURE 9: Code Quality Trends Tests
# =============================================================================

def test_snapshot_current_metrics(db_manager_with_data):
    """Test metric snapshot creation."""
    analyzer = CodeQualityTrendsAnalyzer(db_manager_with_data)

    result = analyzer.snapshot_current_metrics("test-repo", "a" * 40)

    assert result["commit_hash"] == "a" * 40
    assert "metrics" in result
    assert "module_count" in result["metrics"]
    assert "class_count" in result["metrics"]
    assert "function_count" in result["metrics"]
    assert "avg_complexity" in result["metrics"]
    assert result["metrics"]["module_count"] > 0
    assert result["metrics"]["class_count"] >= 2
    assert result["metrics"]["function_count"] >= 8


# =============================================================================
# FEATURE 10: Developer Productivity Insights Tests
# =============================================================================

def test_onboarding_metrics(db_manager_with_data):
    """Test onboarding metrics calculation."""
    analyzer = DeveloperProductivityAnalyzer(db_manager_with_data)

    result = analyzer.get_onboarding_metrics("test-repo")

    assert len(result) > 0
    assert "name" in result.columns
    assert "email" in result.columns
    assert "first_commit" in result.columns
    assert "total_commits" in result.columns
    assert "files_touched" in result.columns

    # Should have data for all 3 authors
    assert len(result) == 3


def test_collaboration_patterns(db_manager_with_data):
    """Test collaboration pattern detection."""
    analyzer = DeveloperProductivityAnalyzer(db_manager_with_data)

    result = analyzer.get_collaboration_patterns("test-repo")

    assert "shared_file_ownership" in result
    assert "top_collaborations" in result
    assert isinstance(result["shared_file_ownership"], list)
    assert isinstance(result["top_collaborations"], list)


def test_cognitive_load_metrics(db_manager_with_data):
    """Test cognitive load calculation."""
    analyzer = DeveloperProductivityAnalyzer(db_manager_with_data)

    result = analyzer.get_cognitive_load_metrics("test-repo")

    assert len(result) > 0
    assert "name" in result.columns
    assert "files_owned" in result.columns
    assert "total_complexity" in result.columns
    assert "cognitive_load_score" in result.columns


def test_code_ownership_evolution(db_manager_with_data):
    """Test code ownership evolution tracking."""
    analyzer = DeveloperProductivityAnalyzer(db_manager_with_data)

    result = analyzer.get_code_ownership_evolution("test-repo")

    assert isinstance(result, list)
    # Should find files with multiple owners
    if len(result) > 0:
        assert "file_path" in result[0]
        assert "primary_owner" in result[0]
        assert "primary_percentage" in result[0]


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

def test_advanced_analytics_api(db_manager_with_data, tmp_path):
    """Test the unified Advanced Analytics API."""
    api = AdvancedAnalyticsAPI(db_manager_with_data)

    # Test that all analyzers are accessible
    assert api.change_impact is not None
    assert api.patterns is not None
    assert api.trends is not None
    assert api.productivity is not None

    # Test export functionality
    output_dir = tmp_path / "exports"
    result = api.export_all_metrics("test-repo", output_dir)

    assert isinstance(result, dict)
    assert len(result) > 0

    # Verify files were created
    for metric_name, file_path in result.items():
        assert Path(file_path).exists()


def test_empty_repository_handling(tmp_path):
    """Test that analytics handle empty repositories gracefully."""
    db_manager = DatabaseManager(data_dir=tmp_path / "data", schema_dir=Path("schema"))
    db_manager.initialize_repo_databases("empty-repo")

    # All analyzers should handle empty data gracefully
    impact = ChangeImpactAnalyzer(db_manager)
    patterns = ArchitecturalPatternDetector(db_manager)
    trends = CodeQualityTrendsAnalyzer(db_manager)
    productivity = DeveloperProductivityAnalyzer(db_manager)

    # Should not raise exceptions
    deps = impact.get_transitive_dependencies("empty-repo", "nonexistent.py")
    assert "error" in deps or deps["total_dependencies"] == 0

    centrality = patterns.calculate_centrality_metrics("empty-repo")
    assert len(centrality) == 0

    metrics = trends.snapshot_current_metrics("empty-repo", "a" * 40)
    assert metrics["metrics"]["module_count"] == 0

    onboarding = productivity.get_onboarding_metrics("empty-repo")
    assert len(onboarding) == 0


def test_max_depth_limiting(db_manager_with_data):
    """Test that max_depth parameter limits transitive dependency traversal."""
    analyzer = ChangeImpactAnalyzer(db_manager_with_data)

    # Test with depth limit
    result_depth1 = analyzer.get_transitive_dependencies("test-repo", "src/main.py", max_depth=1)
    result_unlimited = analyzer.get_transitive_dependencies("test-repo", "src/main.py", max_depth=None)

    # Depth 1 should not exceed depth 1
    if result_depth1["total_dependencies"] > 0:
        assert result_depth1["max_depth"] <= 1

    # Unlimited may have deeper dependencies
    assert result_unlimited["max_depth"] >= result_depth1["max_depth"]
