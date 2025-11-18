"""
Git history analyzer for depanalysis.

Extracts commits, file changes, and calculates temporal coupling metrics.
Populates history.db with Git repository analysis.
"""
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import sqlite3

import git


class GitAnalyzer:
    """Analyzes Git repository history and populates history.db."""

    def __init__(self, repo_path: Path, db_connection: sqlite3.Connection):
        """
        Initialize Git analyzer.

        Args:
            repo_path: Path to the Git repository
            db_connection: SQLite connection to history.db
        """
        self.repo_path = Path(repo_path)
        self.repo = git.Repo(repo_path)
        self.conn = db_connection

    def analyze(self) -> dict:
        """
        Perform full analysis of the repository.

        Returns:
            Dictionary with analysis statistics
        """
        stats = {
            "commits_processed": 0,
            "authors_found": 0,
            "files_tracked": 0,
            "temporal_couplings": 0,
        }

        # Extract and insert data
        self._extract_commits_and_authors()
        self._extract_file_changes()
        self._calculate_temporal_coupling()
        self._calculate_author_ownership()

        # Gather statistics
        cursor = self.conn.cursor()
        stats["commits_processed"] = cursor.execute("SELECT COUNT(*) FROM commits").fetchone()[0]
        stats["authors_found"] = cursor.execute("SELECT COUNT(*) FROM authors").fetchone()[0]
        stats["files_tracked"] = cursor.execute(
            "SELECT COUNT(DISTINCT file_path) FROM file_changes"
        ).fetchone()[0]
        stats["temporal_couplings"] = cursor.execute(
            "SELECT COUNT(*) FROM temporal_coupling"
        ).fetchone()[0]

        return stats

    def _extract_commits_and_authors(self) -> None:
        """Extract commits and authors from Git history."""
        cursor = self.conn.cursor()

        # Track unique authors
        authors = {}

        # Iterate through all commits
        for commit in self.repo.iter_commits("--all"):
            # Insert or get author
            author_email = commit.author.email
            if author_email not in authors:
                cursor.execute(
                    "INSERT OR IGNORE INTO authors (name, email) VALUES (?, ?)",
                    (commit.author.name, author_email),
                )
                cursor.execute("SELECT id FROM authors WHERE email = ?", (author_email,))
                authors[author_email] = cursor.fetchone()[0]

            # Insert commit
            cursor.execute(
                """
                INSERT OR IGNORE INTO commits (hash, author_name, author_email, timestamp, message)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    commit.hexsha,
                    commit.author.name,
                    author_email,
                    datetime.fromtimestamp(commit.committed_date),
                    commit.message,
                ),
            )

        self.conn.commit()

    def _extract_file_changes(self) -> None:
        """Extract file changes from commits."""
        cursor = self.conn.cursor()

        for commit in self.repo.iter_commits("--all"):
            # Get commit ID from database
            cursor.execute("SELECT id FROM commits WHERE hash = ?", (commit.hexsha,))
            commit_id = cursor.fetchone()[0]

            # Get parent commit for diff
            if commit.parents:
                parent = commit.parents[0]
                diffs = parent.diff(commit, create_patch=True)

                for diff in diffs:
                    # Determine change type
                    if diff.new_file:
                        change_type = "A"  # Added
                    elif diff.deleted_file:
                        change_type = "D"  # Deleted
                    elif diff.renamed_file:
                        change_type = "R"  # Renamed
                    elif diff.copied_file:
                        change_type = "C"  # Copied
                    else:
                        change_type = "M"  # Modified

                    # Get file path
                    file_path = diff.b_path if diff.b_path else diff.a_path
                    old_path = diff.a_path if diff.renamed_file else None

                    # Count line changes
                    lines_added = 0
                    lines_deleted = 0

                    if diff.diff:
                        diff_text = diff.diff.decode("utf-8", errors="ignore")
                        for line in diff_text.split("\n"):
                            if line.startswith("+") and not line.startswith("+++"):
                                lines_added += 1
                            elif line.startswith("-") and not line.startswith("---"):
                                lines_deleted += 1

                    # Insert file change
                    cursor.execute(
                        """
                        INSERT INTO file_changes
                        (commit_id, file_path, lines_added, lines_deleted, change_type, old_path)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (commit_id, file_path, lines_added, lines_deleted, change_type, old_path),
                    )
            else:
                # Initial commit - all files are added
                for item in commit.tree.traverse():
                    if item.type == "blob":  # File
                        try:
                            lines = len(item.data_stream.read().decode("utf-8").split("\n"))
                        except Exception:
                            lines = 0

                        cursor.execute(
                            """
                            INSERT INTO file_changes
                            (commit_id, file_path, lines_added, lines_deleted, change_type, old_path)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (commit_id, item.path, lines, 0, "A", None),
                        )

        self.conn.commit()

    def _calculate_temporal_coupling(self) -> None:
        """Calculate temporal coupling using Jaccard similarity."""
        cursor = self.conn.cursor()

        # Get all file changes per commit
        cursor.execute(
            """
            SELECT commit_id, file_path
            FROM file_changes
            WHERE change_type != 'D'
            ORDER BY commit_id
            """
        )

        # Build commit sets for each file
        file_commits = defaultdict(set)
        for commit_id, file_path in cursor.fetchall():
            file_commits[file_path].add(commit_id)

        # Calculate Jaccard similarity for all file pairs
        files = list(file_commits.keys())
        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                file_a, file_b = files[i], files[j]

                # Ensure ordered pair for consistency
                if file_a > file_b:
                    file_a, file_b = file_b, file_a

                commits_a = file_commits[file_a]
                commits_b = file_commits[file_b]

                # Calculate Jaccard similarity: |A ∩ B| / |A ∪ B|
                intersection = commits_a & commits_b
                union = commits_a | commits_b

                co_change_count = len(intersection)

                if co_change_count > 0:
                    jaccard = len(intersection) / len(union)

                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO temporal_coupling
                        (file_a, file_b, co_change_count, jaccard_similarity)
                        VALUES (?, ?, ?, ?)
                        """,
                        (file_a, file_b, co_change_count, jaccard),
                    )

        self.conn.commit()

    def _calculate_author_ownership(self) -> None:
        """Calculate author ownership statistics."""
        cursor = self.conn.cursor()

        # Aggregate contributions by author and file
        cursor.execute(
            """
            INSERT OR REPLACE INTO author_ownership (author_id, file_path, commit_count, lines_contributed)
            SELECT
                a.id,
                fc.file_path,
                COUNT(DISTINCT c.id) AS commit_count,
                SUM(fc.lines_added) AS lines_contributed
            FROM authors a
            JOIN commits c ON c.author_email = a.email
            JOIN file_changes fc ON fc.commit_id = c.id
            WHERE fc.change_type != 'D'
            GROUP BY a.id, fc.file_path
            """
        )

        self.conn.commit()


def discover_repositories(directory: Path) -> list[Path]:
    """
    Discover all Git repositories in a directory.

    Args:
        directory: Directory to search

    Returns:
        List of paths to Git repositories
    """
    repos = []
    directory = Path(directory)

    if not directory.exists():
        return repos

    # Check if the directory itself is a Git repo
    if (directory / ".git").exists():
        repos.append(directory)

    # Search subdirectories
    for subdir in directory.iterdir():
        if subdir.is_dir() and (subdir / ".git").exists():
            repos.append(subdir)

    return repos
