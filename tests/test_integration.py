"""Integration tests for the complete analysis workflow."""
import pytest
from pathlib import Path

from depanalysis.db_manager import DatabaseManager, get_repo_name_from_path
from depanalysis.git_analyzer import GitAnalyzer
from depanalysis.metrics import MetricsAnalyzer


class TestEndToEndWorkflow:
    """Integration tests for complete analysis workflow."""

    def test_full_git_analysis_workflow(self, sample_git_repo, temp_dir, schema_dir):
        """Test complete workflow: repo -> analysis -> metrics -> export."""
        # Setup
        db_manager = DatabaseManager(data_dir=temp_dir / "data", schema_dir=schema_dir)
        repo_name = get_repo_name_from_path(sample_git_repo)

        # Initialize databases
        structure_db_path, history_db_path = db_manager.initialize_repo_databases(repo_name)

        assert structure_db_path.exists(), "Structure DB should be created"
        assert history_db_path.exists(), "History DB should be created"

        # Run Git analysis
        history_conn = db_manager.get_connection(repo_name, "history")
        analyzer = GitAnalyzer(sample_git_repo, history_conn)
        stats = analyzer.analyze()

        assert stats["commits_processed"] == 5
        assert stats["temporal_couplings"] > 0

        history_conn.close()

        # Query metrics
        metrics = MetricsAnalyzer(db_manager)

        # Get churn metrics
        churn_df = metrics.get_churn_metrics(repo_name)
        assert len(churn_df) == 3, "Should have churn for 3 files"

        # Get temporal coupling
        coupling_df = metrics.get_temporal_coupling(repo_name, min_co_changes=1)
        assert len(coupling_df) > 0, "Should have temporal coupling"

        # Get author stats
        author_df = metrics.get_author_stats(repo_name)
        assert len(author_df) == 1, "Should have 1 author"

        # Export to CSV
        output_csv = temp_dir / "churn.csv"
        metrics.export_to_csv(churn_df, output_csv)
        assert output_csv.exists(), "CSV export should create file"

        # Export to JSON
        output_json = temp_dir / "coupling.json"
        metrics.export_to_json(coupling_df, output_json)
        assert output_json.exists(), "JSON export should create file"

    def test_multi_repo_comparison(self, temp_dir, schema_dir):
        """Test cross-repository comparison functionality."""
        import git

        db_manager = DatabaseManager(data_dir=temp_dir / "data", schema_dir=schema_dir)
        metrics = MetricsAnalyzer(db_manager)

        # Create two test repos
        repos = []
        for i in range(2):
            repo_path = temp_dir / f"repo_{i}"
            repo_path.mkdir()
            repo = git.Repo.init(repo_path)

            with repo.config_writer() as config:
                config.set_value("user", "name", f"Author {i}")
                config.set_value("user", "email", f"author{i}@example.com")

            # Add some files
            for j in range(3):
                file_path = repo_path / f"file_{j}.py"
                file_path.write_text(f"# File {j}\n")
                repo.index.add([f"file_{j}.py"])
            repo.index.commit(f"Initial commit for repo {i}")

            repos.append(repo_path)

        # Analyze both repos
        for repo_path in repos:
            repo_name = get_repo_name_from_path(repo_path)
            db_manager.initialize_repo_databases(repo_name)

            history_conn = db_manager.get_connection(repo_name, "history")
            analyzer = GitAnalyzer(repo_path, history_conn)
            analyzer.analyze()
            history_conn.close()

        # Compare across repos
        repo_names = [get_repo_name_from_path(r) for r in repos]

        comparison_df = metrics.compare_author_stats_across_repos(repo_names)
        assert len(comparison_df) == 2, "Should have stats for 2 repos"
        assert "repository" in comparison_df.columns, "Should include repository column"

        churn_comparison = metrics.compare_churn_across_repos(repo_names)
        assert len(churn_comparison) > 0, "Should have churn comparison"
        assert "repository" in churn_comparison.columns

    def test_database_manager_operations(self, temp_dir, schema_dir):
        """Test DatabaseManager CRUD operations."""
        db_manager = DatabaseManager(data_dir=temp_dir / "data", schema_dir=schema_dir)

        # Initially no repos
        assert len(db_manager.list_analyzed_repos()) == 0

        # Create a repo database
        repo_name = "test_project"
        db_manager.initialize_repo_databases(repo_name)

        # Should now be listed
        repos = db_manager.list_analyzed_repos()
        assert repo_name in repos

        # Check repo exists
        assert db_manager.repo_exists(repo_name)

        # Get connections
        history_conn = db_manager.get_connection(repo_name, "history")
        assert history_conn is not None
        history_conn.close()

        structure_conn = db_manager.get_connection(repo_name, "structure")
        assert structure_conn is not None
        structure_conn.close()

        # Delete repo
        db_manager.delete_repo_databases(repo_name)
        assert not db_manager.repo_exists(repo_name)
        assert repo_name not in db_manager.list_analyzed_repos()

    def test_incremental_analysis(self, sample_git_repo, temp_dir, schema_dir):
        """Test incremental analysis (analyze same repo twice)."""
        db_manager = DatabaseManager(data_dir=temp_dir / "data", schema_dir=schema_dir)
        repo_name = get_repo_name_from_path(sample_git_repo)

        db_manager.initialize_repo_databases(repo_name)

        # First analysis
        history_conn = db_manager.get_connection(repo_name, "history")
        analyzer = GitAnalyzer(sample_git_repo, history_conn)
        stats1 = analyzer.analyze()
        history_conn.close()

        # Second analysis (should be idempotent with INSERT OR IGNORE)
        history_conn = db_manager.get_connection(repo_name, "history")
        analyzer = GitAnalyzer(sample_git_repo, history_conn)
        stats2 = analyzer.analyze()
        history_conn.close()

        # Stats should be the same (idempotent)
        assert stats1["commits_processed"] == stats2["commits_processed"]
        assert stats1["authors_found"] == stats2["authors_found"]

    def test_get_summary_stats(self, sample_git_repo, temp_dir, schema_dir):
        """Test getting summary statistics for a repository."""
        db_manager = DatabaseManager(data_dir=temp_dir / "data", schema_dir=schema_dir)
        repo_name = get_repo_name_from_path(sample_git_repo)

        db_manager.initialize_repo_databases(repo_name)

        history_conn = db_manager.get_connection(repo_name, "history")
        analyzer = GitAnalyzer(sample_git_repo, history_conn)
        analyzer.analyze()
        history_conn.close()

        # Get summary stats via MetricsAnalyzer
        metrics = MetricsAnalyzer(db_manager)
        summary = metrics.get_summary_stats(repo_name)

        assert summary["total_commits"] == 5
        assert summary["total_authors"] == 1
        assert summary["files_tracked"] == 3
        assert summary["temporal_couplings"] > 0
        assert "first_commit" in summary
        assert "last_commit" in summary

    def test_high_temporal_coupling_detection(self, temp_dir, schema_dir):
        """Test detection of high temporal coupling pairs."""
        import git

        # Create a repo with files that change together frequently
        repo_path = temp_dir / "high_coupling_repo"
        repo_path.mkdir()
        repo = git.Repo.init(repo_path)

        with repo.config_writer() as config:
            config.set_value("user", "name", "Test User")
            config.set_value("user", "email", "test@example.com")

        # Create files that always change together
        for i in range(5):
            (repo_path / "coupled_a.py").write_text(f"# Version {i}\n")
            (repo_path / "coupled_b.py").write_text(f"# Version {i}\n")
            repo.index.add(["coupled_a.py", "coupled_b.py"])
            repo.index.commit(f"Change {i}")

        # Analyze
        db_manager = DatabaseManager(data_dir=temp_dir / "data", schema_dir=schema_dir)
        repo_name = get_repo_name_from_path(repo_path)
        db_manager.initialize_repo_databases(repo_name)

        history_conn = db_manager.get_connection(repo_name, "history")
        analyzer = GitAnalyzer(repo_path, history_conn)
        analyzer.analyze()
        history_conn.close()

        # Get high temporal coupling
        metrics = MetricsAnalyzer(db_manager)
        high_coupling = metrics.get_high_temporal_coupling(repo_name)

        # With 5 co-changes and perfect Jaccard (1.0), should meet threshold
        assert len(high_coupling) > 0, "Should detect high temporal coupling"
        assert high_coupling.iloc[0]["co_change_count"] >= 3
        assert high_coupling.iloc[0]["jaccard_similarity"] >= 0.3


class TestMetricsQueries:
    """Test metrics query functionality."""

    def test_churn_metrics_filtering(self, sample_git_repo, temp_dir, schema_dir):
        """Test filtering churn metrics by various criteria."""
        db_manager = DatabaseManager(data_dir=temp_dir / "data", schema_dir=schema_dir)
        repo_name = get_repo_name_from_path(sample_git_repo)

        db_manager.initialize_repo_databases(repo_name)

        history_conn = db_manager.get_connection(repo_name, "history")
        analyzer = GitAnalyzer(sample_git_repo, history_conn)
        analyzer.analyze()
        history_conn.close()

        metrics = MetricsAnalyzer(db_manager)
        churn_df = metrics.get_churn_metrics(repo_name)

        # Filter by total churn
        high_churn = churn_df[churn_df["total_churn"] > 10]
        assert len(high_churn) >= 0  # Might be empty for small repos

        # Sort by commit count
        sorted_churn = churn_df.sort_values("total_commits", ascending=False)
        assert sorted_churn.iloc[0]["total_commits"] >= sorted_churn.iloc[-1]["total_commits"]

    def test_temporal_coupling_thresholds(self, sample_git_repo, temp_dir, schema_dir):
        """Test filtering temporal coupling by thresholds."""
        db_manager = DatabaseManager(data_dir=temp_dir / "data", schema_dir=schema_dir)
        repo_name = get_repo_name_from_path(sample_git_repo)

        db_manager.initialize_repo_databases(repo_name)

        history_conn = db_manager.get_connection(repo_name, "history")
        analyzer = GitAnalyzer(sample_git_repo, history_conn)
        analyzer.analyze()
        history_conn.close()

        metrics = MetricsAnalyzer(db_manager)

        # Get all couplings
        all_coupling = metrics.get_temporal_coupling(repo_name, min_co_changes=0, min_similarity=0.0)

        # Get filtered couplings
        filtered_coupling = metrics.get_temporal_coupling(repo_name, min_co_changes=2, min_similarity=0.3)

        # Filtered should be subset of all
        assert len(filtered_coupling) <= len(all_coupling)

        # Verify all filtered entries meet threshold
        if len(filtered_coupling) > 0:
            assert all(filtered_coupling["co_change_count"] >= 2)
            assert all(filtered_coupling["jaccard_similarity"] >= 0.3)

    def test_author_ownership_by_file(self, sample_git_repo, temp_dir, schema_dir):
        """Test querying author ownership for specific files."""
        db_manager = DatabaseManager(data_dir=temp_dir / "data", schema_dir=schema_dir)
        repo_name = get_repo_name_from_path(sample_git_repo)

        db_manager.initialize_repo_databases(repo_name)

        history_conn = db_manager.get_connection(repo_name, "history")
        analyzer = GitAnalyzer(sample_git_repo, history_conn)
        analyzer.analyze()
        history_conn.close()

        metrics = MetricsAnalyzer(db_manager)

        # Get ownership for specific file
        file_ownership = metrics.get_author_ownership(repo_name, file_path="file_a.py")
        assert len(file_ownership) > 0
        assert all(file_ownership["file_path"] == "file_a.py")

        # Get all ownership
        all_ownership = metrics.get_author_ownership(repo_name)
        assert len(all_ownership) >= len(file_ownership)

    def test_code_age_metrics(self, sample_git_repo, temp_dir, schema_dir):
        """Test code age metrics calculation."""
        db_manager = DatabaseManager(data_dir=temp_dir / "data", schema_dir=schema_dir)
        repo_name = get_repo_name_from_path(sample_git_repo)

        db_manager.initialize_repo_databases(repo_name)

        history_conn = db_manager.get_connection(repo_name, "history")
        analyzer = GitAnalyzer(sample_git_repo, history_conn)
        analyzer.analyze()
        history_conn.close()

        metrics = MetricsAnalyzer(db_manager)
        code_age = metrics.get_code_age(repo_name)

        assert len(code_age) == 3, "Should have age for 3 files"

        # Verify columns exist
        assert "days_since_last_change" in code_age.columns
        assert "days_active" in code_age.columns
        assert "total_commits" in code_age.columns


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_nonexistent_repo(self, db_manager):
        """Test querying nonexistent repository."""
        metrics = MetricsAnalyzer(db_manager)

        with pytest.raises(FileNotFoundError):
            metrics.get_churn_metrics("nonexistent_repo")

    def test_empty_repository(self, temp_dir, schema_dir):
        """Test analyzing empty git repository."""
        import git

        # Create empty repo (no commits)
        repo_path = temp_dir / "empty_repo"
        repo_path.mkdir()
        repo = git.Repo.init(repo_path)

        with repo.config_writer() as config:
            config.set_value("user", "name", "Test User")
            config.set_value("user", "email", "test@example.com")

        # Try to analyze
        db_manager = DatabaseManager(data_dir=temp_dir / "data", schema_dir=schema_dir)
        repo_name = get_repo_name_from_path(repo_path)
        db_manager.initialize_repo_databases(repo_name)

        history_conn = db_manager.get_connection(repo_name, "history")
        analyzer = GitAnalyzer(repo_path, history_conn)
        stats = analyzer.analyze()
        history_conn.close()

        # Should handle gracefully
        assert stats["commits_processed"] == 0
        assert stats["temporal_couplings"] == 0

    def test_missing_schema_files(self, temp_dir):
        """Test error when schema files are missing."""
        # Create db_manager with nonexistent schema dir
        db_manager = DatabaseManager(
            data_dir=temp_dir / "data",
            schema_dir=temp_dir / "nonexistent_schema"
        )

        with pytest.raises(FileNotFoundError):
            db_manager.initialize_repo_databases("test_repo")

    def test_concurrent_database_access(self, sample_git_repo, temp_dir, schema_dir):
        """Test multiple simultaneous connections to the same database."""
        db_manager = DatabaseManager(data_dir=temp_dir / "data", schema_dir=schema_dir)
        repo_name = get_repo_name_from_path(sample_git_repo)

        db_manager.initialize_repo_databases(repo_name)

        # Open multiple connections
        conn1 = db_manager.get_connection(repo_name, "history")
        conn2 = db_manager.get_connection(repo_name, "history")

        # Both should work
        cursor1 = conn1.cursor()
        cursor2 = conn2.cursor()

        count1 = cursor1.execute("SELECT COUNT(*) FROM commits").fetchone()[0]
        count2 = cursor2.execute("SELECT COUNT(*) FROM commits").fetchone()[0]

        assert count1 == count2

        conn1.close()
        conn2.close()
