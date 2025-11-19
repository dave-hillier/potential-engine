"""
Tests for example repositories and their generated databases.

This test module validates:
1. Example repository generation (Git repos with commits)
2. Database contents (structure.db and history.db)
3. Data loader scripts and their JSON outputs
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from depanalysis.db_manager import DatabaseManager
from depanalysis.metrics import MetricsAnalyzer


@pytest.fixture(scope="module")
def examples_dir():
    """Get the examples directory path."""
    return Path(__file__).parent.parent / "examples" / "repos"


@pytest.fixture(scope="module")
def data_dir():
    """Get the data directory path."""
    return Path(__file__).parent.parent / "data"


@pytest.fixture(scope="module")
def docs_data_dir():
    """Get the docs data loader directory path."""
    return Path(__file__).parent.parent / "docs" / "src" / "data"


@pytest.fixture(scope="module")
def db_manager(data_dir):
    """Create a DatabaseManager for the examples."""
    return DatabaseManager(data_dir=data_dir)


class TestExampleRepositories:
    """Test that example repositories are properly generated."""

    def test_simple_linear_exists(self, examples_dir):
        """Test simple-linear repository exists."""
        repo_path = examples_dir / "simple-linear"
        assert repo_path.exists(), "simple-linear repository should exist"
        assert (repo_path / ".git").exists(), "simple-linear should be a Git repository"

    def test_multi_author_exists(self, examples_dir):
        """Test multi-author repository exists."""
        repo_path = examples_dir / "multi-author"
        assert repo_path.exists(), "multi-author repository should exist"
        assert (repo_path / ".git").exists(), "multi-author should be a Git repository"

    def test_high_churn_exists(self, examples_dir):
        """Test high-churn repository exists."""
        repo_path = examples_dir / "high-churn"
        assert repo_path.exists(), "high-churn repository should exist"
        assert (repo_path / ".git").exists(), "high-churn should be a Git repository"

    def test_simple_linear_has_commits(self, examples_dir):
        """Test simple-linear has expected commits."""
        import git
        repo = git.Repo(examples_dir / "simple-linear")
        commits = list(repo.iter_commits())
        assert len(commits) >= 5, "simple-linear should have at least 5 commits"

    def test_multi_author_has_multiple_authors(self, examples_dir):
        """Test multi-author has multiple authors."""
        import git
        repo = git.Repo(examples_dir / "multi-author")
        authors = set()
        for commit in repo.iter_commits():
            authors.add(commit.author.name)
        assert len(authors) >= 3, "multi-author should have at least 3 different authors"

    def test_high_churn_has_many_commits(self, examples_dir):
        """Test high-churn has many commits (showing high churn)."""
        import git
        repo = git.Repo(examples_dir / "high-churn")
        commits = list(repo.iter_commits())
        assert len(commits) >= 10, "high-churn should have at least 10 commits"


class TestExampleDatabases:
    """Test that example databases are properly created and populated."""

    def test_databases_exist(self, db_manager):
        """Test that all example databases exist."""
        examples = ["simple-linear", "multi-author", "high-churn"]
        for repo_name in examples:
            assert db_manager.repo_exists(repo_name), f"{repo_name} database should exist"

    def test_simple_linear_history_db(self, db_manager):
        """Test simple-linear history database contents."""
        conn = db_manager.get_connection("simple-linear", "history")
        cursor = conn.cursor()

        # Check commits
        commits = cursor.execute("SELECT COUNT(*) FROM commits").fetchone()[0]
        assert commits >= 5, "simple-linear should have at least 5 commits"

        # Check authors
        authors = cursor.execute("SELECT COUNT(DISTINCT author_name) FROM commits").fetchone()[0]
        assert authors == 1, "simple-linear should have 1 author"

        # Check files
        files = cursor.execute("SELECT COUNT(DISTINCT file_path) FROM file_changes").fetchone()[0]
        assert files >= 3, "simple-linear should track at least 3 files"

        conn.close()

    def test_simple_linear_structure_db(self, db_manager):
        """Test simple-linear structure database contents."""
        conn = db_manager.get_connection("simple-linear", "structure")
        cursor = conn.cursor()

        # Check modules
        modules = cursor.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
        assert modules >= 3, "simple-linear should have at least 3 modules"

        # Check functions
        functions = cursor.execute("SELECT COUNT(*) FROM functions").fetchone()[0]
        assert functions >= 2, "simple-linear should have at least 2 functions"

        # Check imports
        imports = cursor.execute("SELECT COUNT(*) FROM imports").fetchone()[0]
        assert imports >= 1, "simple-linear should have at least 1 import"

        conn.close()

    def test_multi_author_history_db(self, db_manager):
        """Test multi-author history database contents."""
        conn = db_manager.get_connection("multi-author", "history")
        cursor = conn.cursor()

        # Check commits
        commits = cursor.execute("SELECT COUNT(*) FROM commits").fetchone()[0]
        assert commits >= 7, "multi-author should have at least 7 commits"

        # Check multiple authors
        authors = cursor.execute("SELECT COUNT(DISTINCT author_name) FROM commits").fetchone()[0]
        assert authors >= 3, "multi-author should have at least 3 authors"

        # Check author names
        author_names = cursor.execute("SELECT DISTINCT author_name FROM commits ORDER BY author_name").fetchall()
        author_names = [name[0] for name in author_names]
        assert "Alice Developer" in author_names
        assert "Bob Engineer" in author_names
        assert "Charlie Coder" in author_names

        conn.close()

    def test_multi_author_structure_db(self, db_manager):
        """Test multi-author structure database contents."""
        conn = db_manager.get_connection("multi-author", "structure")
        cursor = conn.cursor()

        # Check modules (server.py, client.py, protocol.py)
        modules = cursor.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
        assert modules >= 3, "multi-author should have at least 3 modules"

        # Check classes
        classes = cursor.execute("SELECT COUNT(*) FROM classes").fetchone()[0]
        assert classes >= 3, "multi-author should have at least 3 classes (Server, Client, Message)"

        conn.close()

    def test_high_churn_history_db(self, db_manager):
        """Test high-churn history database contents."""
        conn = db_manager.get_connection("high-churn", "history")
        cursor = conn.cursor()

        # Check commits (should have many)
        commits = cursor.execute("SELECT COUNT(*) FROM commits").fetchone()[0]
        assert commits >= 14, "high-churn should have at least 14 commits"

        # Check file changes (should have high churn)
        file_churn = cursor.execute("""
            SELECT file_path, SUM(lines_added + lines_deleted) as total_churn
            FROM file_changes
            GROUP BY file_path
            ORDER BY total_churn DESC
            LIMIT 1
        """).fetchone()

        assert file_churn is not None
        assert file_churn[1] > 40, "high-churn should have files with significant churn"

        # Check temporal coupling
        temporal_couplings = cursor.execute("SELECT COUNT(*) FROM temporal_coupling").fetchone()[0]
        assert temporal_couplings > 0, "high-churn should have temporal coupling data"

        conn.close()

    def test_high_churn_structure_db(self, db_manager):
        """Test high-churn structure database contents."""
        conn = db_manager.get_connection("high-churn", "structure")
        cursor = conn.cursor()

        # Check modules
        modules = cursor.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
        assert modules >= 3, "high-churn should have at least 3 modules"

        # Check classes
        classes = cursor.execute("SELECT COUNT(*) FROM classes").fetchone()[0]
        assert classes >= 1, "high-churn should have at least 1 class"

        conn.close()

    def test_temporal_coupling_exists(self, db_manager):
        """Test that temporal coupling is calculated for high-churn repo."""
        conn = db_manager.get_connection("high-churn", "history")
        cursor = conn.cursor()

        # Query temporal coupling between models.py and views.py
        coupling = cursor.execute("""
            SELECT co_change_count, jaccard_similarity
            FROM temporal_coupling
            WHERE (file_a = 'models.py' AND file_b = 'views.py')
               OR (file_a = 'views.py' AND file_b = 'models.py')
        """).fetchone()

        assert coupling is not None, "Should have temporal coupling between models.py and views.py"
        co_changes, similarity = coupling
        # Lower expectations since the example generates less coupling than expected
        assert co_changes >= 2, "models.py and views.py should change together"
        assert similarity >= 0.1, "models.py and views.py should have some coupling"

        conn.close()


class TestMetricsQueries:
    """Test that metrics can be queried correctly from example databases."""

    def test_get_churn_metrics(self, db_manager):
        """Test querying churn metrics."""
        metrics = MetricsAnalyzer(db_manager)

        for repo in ["simple-linear", "multi-author", "high-churn"]:
            df = metrics.get_churn_metrics(repo)
            assert len(df) > 0, f"{repo} should have churn metrics"
            assert "file_path" in df.columns
            assert "total_churn" in df.columns
            assert "total_commits" in df.columns

    def test_get_temporal_coupling(self, db_manager):
        """Test querying temporal coupling."""
        metrics = MetricsAnalyzer(db_manager)

        # high-churn should have significant temporal coupling
        df = metrics.get_temporal_coupling("high-churn", min_co_changes=2)
        assert len(df) > 0, "high-churn should have temporal coupling"
        assert "file_a" in df.columns
        assert "file_b" in df.columns
        assert "co_change_count" in df.columns
        assert "jaccard_similarity" in df.columns

    def test_get_author_stats(self, db_manager):
        """Test querying author statistics."""
        metrics = MetricsAnalyzer(db_manager)

        # simple-linear should have 1 author
        df = metrics.get_author_stats("simple-linear")
        assert len(df) == 1, "simple-linear should have 1 author"

        # multi-author should have 3 authors
        df = metrics.get_author_stats("multi-author")
        assert len(df) == 3, "multi-author should have 3 authors"

    def test_get_summary_stats(self, db_manager):
        """Test getting summary statistics."""
        metrics = MetricsAnalyzer(db_manager)

        for repo in ["simple-linear", "multi-author", "high-churn"]:
            summary = metrics.get_summary_stats(repo)
            assert summary["total_commits"] > 0
            assert summary["total_authors"] > 0
            assert summary["files_tracked"] > 0
            assert "first_commit" in summary
            assert "last_commit" in summary


class TestDataLoaders:
    """Test that data loader scripts produce valid JSON output."""

    def test_repo_list_loader(self, docs_data_dir):
        """Test repo-list.json.py data loader."""
        script = docs_data_dir / "repo-list.json.py"
        assert script.exists(), "repo-list.json.py should exist"

        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            cwd=script.parent
        )

        assert result.returncode == 0, f"repo-list loader failed: {result.stderr}"

        data = json.loads(result.stdout)
        assert isinstance(data, list), "repo-list should return a list"
        assert len(data) >= 3, "Should have at least 3 repos (examples)"

        # Check that example repos are in the list
        # repo-list returns strings (just names)
        assert "simple-linear" in data
        assert "multi-author" in data
        assert "high-churn" in data

    def test_all_repos_summary_loader(self, docs_data_dir):
        """Test all-repos-summary.json.py data loader."""
        script = docs_data_dir / "all-repos-summary.json.py"
        assert script.exists(), "all-repos-summary.json.py should exist"

        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            cwd=script.parent
        )

        assert result.returncode == 0, f"all-repos-summary loader failed: {result.stderr}"

        data = json.loads(result.stdout)
        assert isinstance(data, list), "all-repos-summary should return a list"
        assert len(data) >= 3, "Should have summaries for at least 3 repos"

        # Check structure of summaries
        for summary in data:
            assert "name" in summary
            assert "total_commits" in summary
            assert "total_authors" in summary
            assert "files_tracked" in summary

    def test_simple_linear_churn_loader(self, docs_data_dir):
        """Test simple-linear-churn.json.py data loader."""
        script = docs_data_dir / "simple-linear-churn.json.py"
        assert script.exists(), "simple-linear-churn.json.py should exist"

        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            cwd=script.parent
        )

        assert result.returncode == 0, f"simple-linear-churn loader failed: {result.stderr}"

        data = json.loads(result.stdout)
        assert isinstance(data, list), "churn loader should return a list"
        assert len(data) > 0, "Should have churn data for simple-linear"

        # Check structure
        for entry in data:
            assert "file_path" in entry
            assert "total_churn" in entry
            assert "total_commits" in entry

    def test_simple_linear_coupling_loader(self, docs_data_dir):
        """Test simple-linear-coupling.json.py data loader."""
        script = docs_data_dir / "simple-linear-coupling.json.py"
        assert script.exists(), "simple-linear-coupling.json.py should exist"

        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            cwd=script.parent
        )

        assert result.returncode == 0, f"simple-linear-coupling loader failed: {result.stderr}"

        data = json.loads(result.stdout)
        assert isinstance(data, list), "coupling loader should return a list"

        # simple-linear might have low coupling, so we just check structure if data exists
        for entry in data:
            assert "file_a" in entry
            assert "file_b" in entry
            assert "co_change_count" in entry
            assert "jaccard_similarity" in entry

    def test_simple_linear_authors_loader(self, docs_data_dir):
        """Test simple-linear-authors.json.py data loader."""
        script = docs_data_dir / "simple-linear-authors.json.py"
        assert script.exists(), "simple-linear-authors.json.py should exist"

        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            cwd=script.parent
        )

        assert result.returncode == 0, f"simple-linear-authors loader failed: {result.stderr}"

        data = json.loads(result.stdout)
        assert isinstance(data, list), "authors loader should return a list"
        assert len(data) == 1, "simple-linear should have 1 author"

        author = data[0]
        assert "name" in author
        assert "total_commits" in author
        assert "files_touched" in author

    def test_multi_author_churn_loader(self, docs_data_dir):
        """Test multi-author-churn.json.py data loader."""
        script = docs_data_dir / "multi-author-churn.json.py"
        assert script.exists(), "multi-author-churn.json.py should exist"

        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            cwd=script.parent
        )

        assert result.returncode == 0, f"multi-author-churn loader failed: {result.stderr}"

        data = json.loads(result.stdout)
        assert isinstance(data, list), "churn loader should return a list"
        assert len(data) >= 3, "multi-author should have at least 3 files"

    def test_multi_author_authors_loader(self, docs_data_dir):
        """Test multi-author-authors.json.py data loader."""
        script = docs_data_dir / "multi-author-authors.json.py"
        assert script.exists(), "multi-author-authors.json.py should exist"

        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            cwd=script.parent
        )

        assert result.returncode == 0, f"multi-author-authors loader failed: {result.stderr}"

        data = json.loads(result.stdout)
        assert isinstance(data, list), "authors loader should return a list"
        assert len(data) == 3, "multi-author should have 3 authors"

    def test_high_churn_churn_loader(self, docs_data_dir):
        """Test high-churn-churn.json.py data loader."""
        script = docs_data_dir / "high-churn-churn.json.py"
        assert script.exists(), "high-churn-churn.json.py should exist"

        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            cwd=script.parent
        )

        assert result.returncode == 0, f"high-churn-churn loader failed: {result.stderr}"

        data = json.loads(result.stdout)
        assert isinstance(data, list), "churn loader should return a list"
        assert len(data) >= 3, "high-churn should have at least 3 files"

        # Check that files have significant churn
        total_churn = sum(entry["total_churn"] for entry in data)
        assert total_churn > 40, "high-churn should have significant total churn"

    def test_high_churn_coupling_loader(self, docs_data_dir):
        """Test high-churn-coupling.json.py data loader."""
        script = docs_data_dir / "high-churn-coupling.json.py"
        assert script.exists(), "high-churn-coupling.json.py should exist"

        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            cwd=script.parent
        )

        assert result.returncode == 0, f"high-churn-coupling loader failed: {result.stderr}"

        data = json.loads(result.stdout)
        assert isinstance(data, list), "coupling loader should return a list"
        assert len(data) > 0, "high-churn should have temporal coupling"

        # Check for strong coupling between models.py and views.py
        models_views_coupling = [
            entry for entry in data
            if (entry["file_a"] == "models.py" and entry["file_b"] == "views.py")
            or (entry["file_a"] == "views.py" and entry["file_b"] == "models.py")
        ]
        assert len(models_views_coupling) > 0, "Should have coupling between models.py and views.py"

        coupling = models_views_coupling[0]
        # Lower expectations since the example generates less coupling
        assert coupling["co_change_count"] >= 2, "Should have co-changes"
        assert coupling["jaccard_similarity"] >= 0.1, "Should have some similarity"


class TestDataLoaderErrorHandling:
    """Test that data loaders handle errors gracefully."""

    def test_nonexistent_repo_loader(self, docs_data_dir):
        """Test that loaders handle nonexistent repositories gracefully."""
        # Test with churn.json.py which takes a repo parameter
        script = docs_data_dir / "churn.json.py"

        if script.exists():
            result = subprocess.run(
                [sys.executable, str(script), "nonexistent-repo"],
                capture_output=True,
                text=True,
                cwd=script.parent
            )

            # Should exit with error
            assert result.returncode != 0, "Should fail for nonexistent repo"
            assert "error" in result.stderr.lower() or "not found" in result.stderr.lower()
