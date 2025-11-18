"""Tests for temporal coupling analysis from Git history."""
import pytest
from collections import defaultdict

from depanalysis.git_analyzer import GitAnalyzer


class TestTemporalCoupling:
    """Test suite for temporal coupling calculations."""

    def test_basic_temporal_coupling(self, sample_git_repo, history_db):
        """Test basic temporal coupling analysis on a known repository."""
        analyzer = GitAnalyzer(sample_git_repo, history_db)
        stats = analyzer.analyze()

        # Verify basic statistics
        assert stats["commits_processed"] == 5, "Should have 5 commits"
        assert stats["authors_found"] == 1, "Should have 1 author"
        assert stats["files_tracked"] == 3, "Should track 3 files"

        # Verify temporal coupling was calculated
        assert stats["temporal_couplings"] > 0, "Should have temporal couplings"

    def test_jaccard_similarity_calculation(self, sample_git_repo, history_db):
        """Test Jaccard similarity calculation for file pairs."""
        analyzer = GitAnalyzer(sample_git_repo, history_db)
        analyzer.analyze()

        cursor = history_db.cursor()

        # Get coupling between file_a.py and file_b.py
        # They change together in commits 1, 3 (co-change = 2)
        # file_a.py appears in commits 1, 3, 4 (3 commits)
        # file_b.py appears in commits 1, 3, 5 (3 commits)
        # Union = {1, 3, 4, 5} = 4 commits
        # Intersection = {1, 3} = 2 commits
        # Jaccard = 2/4 = 0.5
        result = cursor.execute("""
            SELECT co_change_count, jaccard_similarity
            FROM temporal_coupling
            WHERE file_a = 'file_a.py' AND file_b = 'file_b.py'
        """).fetchone()

        assert result is not None, "Should find coupling between file_a and file_b"
        assert result[0] == 2, "file_a and file_b co-change 2 times"
        assert abs(result[1] - 0.5) < 0.01, f"Jaccard similarity should be 0.5, got {result[1]}"

    def test_no_coupling_for_independent_files(self, sample_git_repo, history_db):
        """Test that files with no co-changes have no coupling entry."""
        analyzer = GitAnalyzer(sample_git_repo, history_db)
        analyzer.analyze()

        cursor = history_db.cursor()

        # file_a.py and file_c.py never change together
        result = cursor.execute("""
            SELECT co_change_count
            FROM temporal_coupling
            WHERE (file_a = 'file_a.py' AND file_b = 'file_c.py')
               OR (file_a = 'file_c.py' AND file_b = 'file_a.py')
        """).fetchone()

        # Should not exist or have co_change_count = 0
        assert result is None, "Independent files should have no coupling entry"

    def test_coupling_strength_comparison(self, sample_git_repo, history_db):
        """Test comparing coupling strength between different file pairs."""
        analyzer = GitAnalyzer(sample_git_repo, history_db)
        analyzer.analyze()

        cursor = history_db.cursor()

        # Get all couplings sorted by strength
        couplings = cursor.execute("""
            SELECT file_a, file_b, co_change_count, jaccard_similarity
            FROM temporal_coupling
            ORDER BY jaccard_similarity DESC
        """).fetchall()

        assert len(couplings) > 0, "Should have at least one coupling"

        # All Jaccard similarities should be between 0 and 1
        for coupling in couplings:
            jaccard = coupling[3]
            assert 0.0 <= jaccard <= 1.0, f"Jaccard similarity {jaccard} out of range"

    def test_ordered_file_pairs(self, sample_git_repo, history_db):
        """Test that file pairs are consistently ordered (file_a < file_b)."""
        analyzer = GitAnalyzer(sample_git_repo, history_db)
        analyzer.analyze()

        cursor = history_db.cursor()

        # All pairs should have file_a < file_b
        invalid_pairs = cursor.execute("""
            SELECT file_a, file_b
            FROM temporal_coupling
            WHERE file_a >= file_b
        """).fetchall()

        assert len(invalid_pairs) == 0, f"Found unordered pairs: {invalid_pairs}"

    def test_high_temporal_coupling_view(self, sample_git_repo, history_db):
        """Test the high_temporal_coupling view."""
        analyzer = GitAnalyzer(sample_git_repo, history_db)
        analyzer.analyze()

        cursor = history_db.cursor()

        # Query the materialized view for high coupling
        # Threshold: co_change_count >= 3 AND jaccard >= 0.3
        high_coupling = cursor.execute("""
            SELECT * FROM high_temporal_coupling
        """).fetchall()

        # In our sample, no pairs have 3+ co-changes
        # This tests that the view works even when empty
        assert isinstance(high_coupling, list), "View should return a list"

    def test_temporal_coupling_with_file_deletions(self, temp_dir, history_db, schema_dir):
        """Test temporal coupling behavior with file deletions."""
        import git

        # Create a repo where files are added together, then one is deleted
        repo_path = temp_dir / "deletion_test"
        repo_path.mkdir()
        repo = git.Repo.init(repo_path)

        with repo.config_writer() as config:
            config.set_value("user", "name", "Test User")
            config.set_value("user", "email", "test@example.com")

        # Commit 1: Add two files together (they co-change)
        (repo_path / "file1.py").write_text("# File 1\n")
        (repo_path / "file2.py").write_text("# File 2\n")
        repo.index.add(["file1.py", "file2.py"])
        repo.index.commit("Add files")

        # Commit 2: Delete file1, modify file3 (deletion should not create coupling with file3)
        (repo_path / "file1.py").unlink()
        (repo_path / "file3.py").write_text("# File 3\n")
        repo.index.remove(["file1.py"])
        repo.index.add(["file3.py"])
        repo.index.commit("Delete file1 and add file3")

        # Analyze
        analyzer = GitAnalyzer(repo_path, history_db)
        analyzer.analyze()

        cursor = history_db.cursor()

        # Files should still show coupling from before deletion
        # file1.py and file2.py changed together in commit 1
        coupling_before_deletion = cursor.execute("""
            SELECT co_change_count
            FROM temporal_coupling
            WHERE file_a = 'file1.py' AND file_b = 'file2.py'
        """).fetchone()

        assert coupling_before_deletion is not None, "Files should show coupling from before deletion"
        assert coupling_before_deletion[0] == 1, "Should have 1 co-change"

        # But file1's deletion should NOT create coupling with file3
        # (because change_type='D' is filtered out)
        deletion_coupling = cursor.execute("""
            SELECT COUNT(*)
            FROM temporal_coupling
            WHERE (file_a = 'file1.py' AND file_b = 'file3.py')
               OR (file_a = 'file3.py' AND file_b = 'file1.py')
        """).fetchone()[0]

        assert deletion_coupling == 0, "Deletion should not create coupling with other files"

    def test_perfect_coupling(self, temp_dir, history_db):
        """Test files that always change together have Jaccard similarity = 1.0."""
        import git

        repo_path = temp_dir / "perfect_coupling"
        repo_path.mkdir()
        repo = git.Repo.init(repo_path)

        with repo.config_writer() as config:
            config.set_value("user", "name", "Test User")
            config.set_value("user", "email", "test@example.com")

        # Create two files that ALWAYS change together
        for i in range(3):
            (repo_path / "always_a.py").write_text(f"# Version {i}\n")
            (repo_path / "always_b.py").write_text(f"# Version {i}\n")
            repo.index.add(["always_a.py", "always_b.py"])
            repo.index.commit(f"Commit {i}")

        analyzer = GitAnalyzer(repo_path, history_db)
        analyzer.analyze()

        cursor = history_db.cursor()

        result = cursor.execute("""
            SELECT jaccard_similarity
            FROM temporal_coupling
            WHERE file_a = 'always_a.py' AND file_b = 'always_b.py'
        """).fetchone()

        assert result is not None
        assert abs(result[0] - 1.0) < 0.01, f"Perfect coupling should be 1.0, got {result[0]}"

    def test_single_file_no_coupling(self, temp_dir, history_db):
        """Test repository with single file has no coupling entries."""
        import git

        repo_path = temp_dir / "single_file"
        repo_path.mkdir()
        repo = git.Repo.init(repo_path)

        with repo.config_writer() as config:
            config.set_value("user", "name", "Test User")
            config.set_value("user", "email", "test@example.com")

        (repo_path / "solo.py").write_text("# Solo file\n")
        repo.index.add(["solo.py"])
        repo.index.commit("Add solo file")

        analyzer = GitAnalyzer(repo_path, history_db)
        stats = analyzer.analyze()

        assert stats["temporal_couplings"] == 0, "Single file should have no couplings"

    def test_co_change_count_accuracy(self, sample_git_repo, history_db):
        """Test that co-change counts are accurate."""
        analyzer = GitAnalyzer(sample_git_repo, history_db)
        analyzer.analyze()

        cursor = history_db.cursor()

        # Manually calculate expected co-changes
        # file_b.py and file_c.py change together in commit 5
        result = cursor.execute("""
            SELECT co_change_count
            FROM temporal_coupling
            WHERE file_a = 'file_b.py' AND file_b = 'file_c.py'
        """).fetchone()

        assert result is not None
        assert result[0] == 1, "file_b and file_c should co-change exactly once"


class TestChurnMetrics:
    """Test suite for file churn metrics."""

    def test_churn_metrics_calculation(self, sample_git_repo, history_db):
        """Test that churn metrics are calculated correctly."""
        analyzer = GitAnalyzer(sample_git_repo, history_db)
        analyzer.analyze()

        cursor = history_db.cursor()

        # Get churn for file_a.py
        # Appears in commits: 1 (added), 3 (modified), 4 (modified)
        result = cursor.execute("""
            SELECT total_commits, author_count
            FROM churn_metrics
            WHERE file_path = 'file_a.py'
        """).fetchone()

        assert result is not None
        assert result[0] == 3, "file_a.py should have 3 commits"
        assert result[1] == 1, "file_a.py should have 1 author"

    def test_lines_added_deleted_tracking(self, sample_git_repo, history_db):
        """Test that line additions and deletions are tracked."""
        analyzer = GitAnalyzer(sample_git_repo, history_db)
        analyzer.analyze()

        cursor = history_db.cursor()

        # All files should have some lines added
        result = cursor.execute("""
            SELECT file_path, total_lines_added, total_lines_deleted
            FROM churn_metrics
        """).fetchall()

        assert len(result) == 3, "Should have metrics for 3 files"

        for file_path, lines_added, lines_deleted in result:
            assert lines_added > 0, f"{file_path} should have lines added"
            # lines_deleted might be 0 for some files


class TestAuthorOwnership:
    """Test suite for author ownership analysis."""

    def test_author_ownership_calculation(self, sample_git_repo, history_db):
        """Test author ownership metrics."""
        analyzer = GitAnalyzer(sample_git_repo, history_db)
        analyzer.analyze()

        cursor = history_db.cursor()

        # Should have ownership records for each file
        ownership = cursor.execute("""
            SELECT COUNT(DISTINCT file_path)
            FROM author_ownership
        """).fetchone()[0]

        assert ownership == 3, "Should have ownership for 3 files"

    def test_author_stats_view(self, sample_git_repo, history_db):
        """Test the author_stats materialized view."""
        analyzer = GitAnalyzer(sample_git_repo, history_db)
        analyzer.analyze()

        cursor = history_db.cursor()

        stats = cursor.execute("""
            SELECT name, email, total_commits, files_touched
            FROM author_stats
        """).fetchone()

        assert stats is not None
        assert stats[0] == "Test User"
        assert stats[1] == "test@example.com"
        assert stats[2] == 5, "Should have 5 commits"
        assert stats[3] == 3, "Should have touched 3 files"
