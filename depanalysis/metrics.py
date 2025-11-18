"""
Metrics and analysis queries for depanalysis.

Provides Python API for querying structure.db and history.db,
including single-repo and cross-repo analysis capabilities.
"""
import sqlite3
from pathlib import Path
from typing import Optional
import pandas as pd

from depanalysis.db_manager import DatabaseManager


class MetricsAnalyzer:
    """Query and analyze metrics from depanalysis databases."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize metrics analyzer.

        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager

    def get_churn_metrics(self, repo_name: str) -> pd.DataFrame:
        """
        Get file churn metrics for a repository.

        Args:
            repo_name: Name of the repository

        Returns:
            DataFrame with churn metrics per file
        """
        conn = self.db_manager.get_connection(repo_name, "history")
        df = pd.read_sql_query("SELECT * FROM churn_metrics ORDER BY total_churn DESC", conn)
        conn.close()
        return df

    def get_temporal_coupling(
        self, repo_name: str, min_co_changes: int = 2, min_similarity: float = 0.0
    ) -> pd.DataFrame:
        """
        Get temporal coupling metrics for a repository.

        Args:
            repo_name: Name of the repository
            min_co_changes: Minimum co-change count threshold
            min_similarity: Minimum Jaccard similarity threshold

        Returns:
            DataFrame with temporal coupling data
        """
        conn = self.db_manager.get_connection(repo_name, "history")
        query = """
            SELECT * FROM temporal_coupling
            WHERE co_change_count >= ? AND jaccard_similarity >= ?
            ORDER BY jaccard_similarity DESC, co_change_count DESC
        """
        df = pd.read_sql_query(query, conn, params=(min_co_changes, min_similarity))
        conn.close()
        return df

    def get_author_stats(self, repo_name: str) -> pd.DataFrame:
        """
        Get author statistics for a repository.

        Args:
            repo_name: Name of the repository

        Returns:
            DataFrame with author statistics
        """
        conn = self.db_manager.get_connection(repo_name, "history")
        df = pd.read_sql_query(
            "SELECT * FROM author_stats ORDER BY total_commits DESC", conn
        )
        conn.close()
        return df

    def get_author_ownership(self, repo_name: str, file_path: Optional[str] = None) -> pd.DataFrame:
        """
        Get author ownership data for a repository.

        Args:
            repo_name: Name of the repository
            file_path: Optional file path to filter by

        Returns:
            DataFrame with author ownership data
        """
        conn = self.db_manager.get_connection(repo_name, "history")

        if file_path:
            query = """
                SELECT ao.*, a.name, a.email
                FROM author_ownership ao
                JOIN authors a ON ao.author_id = a.id
                WHERE ao.file_path = ?
                ORDER BY ao.commit_count DESC
            """
            df = pd.read_sql_query(query, conn, params=(file_path,))
        else:
            query = """
                SELECT ao.*, a.name, a.email
                FROM author_ownership ao
                JOIN authors a ON ao.author_id = a.id
                ORDER BY ao.commit_count DESC
            """
            df = pd.read_sql_query(query, conn)

        conn.close()
        return df

    def get_code_age(self, repo_name: str) -> pd.DataFrame:
        """
        Get code age metrics for a repository.

        Args:
            repo_name: Name of the repository

        Returns:
            DataFrame with code age data
        """
        conn = self.db_manager.get_connection(repo_name, "history")
        df = pd.read_sql_query(
            "SELECT * FROM code_age ORDER BY days_since_last_change DESC", conn
        )
        conn.close()
        return df

    def get_high_temporal_coupling(self, repo_name: str) -> pd.DataFrame:
        """
        Get high temporal coupling pairs (co_change >= 3, similarity >= 0.3).

        Args:
            repo_name: Name of the repository

        Returns:
            DataFrame with high temporal coupling data
        """
        conn = self.db_manager.get_connection(repo_name, "history")
        df = pd.read_sql_query("SELECT * FROM high_temporal_coupling", conn)
        conn.close()
        return df

    def compare_author_stats_across_repos(self, repo_names: list[str]) -> pd.DataFrame:
        """
        Compare author statistics across multiple repositories.

        Args:
            repo_names: List of repository names

        Returns:
            DataFrame with combined author stats from all repos
        """
        all_stats = []

        for repo_name in repo_names:
            try:
                df = self.get_author_stats(repo_name)
                df["repository"] = repo_name
                all_stats.append(df)
            except FileNotFoundError:
                continue

        if not all_stats:
            return pd.DataFrame()

        return pd.concat(all_stats, ignore_index=True)

    def compare_churn_across_repos(self, repo_names: list[str]) -> pd.DataFrame:
        """
        Compare churn metrics across multiple repositories.

        Args:
            repo_names: List of repository names

        Returns:
            DataFrame with combined churn metrics from all repos
        """
        all_churn = []

        for repo_name in repo_names:
            try:
                df = self.get_churn_metrics(repo_name)
                df["repository"] = repo_name
                all_churn.append(df)
            except FileNotFoundError:
                continue

        if not all_churn:
            return pd.DataFrame()

        return pd.concat(all_churn, ignore_index=True)

    def export_to_csv(self, df: pd.DataFrame, output_path: Path) -> None:
        """
        Export DataFrame to CSV file.

        Args:
            df: DataFrame to export
            output_path: Path to output CSV file
        """
        df.to_csv(output_path, index=False)

    def export_to_json(self, df: pd.DataFrame, output_path: Path) -> None:
        """
        Export DataFrame to JSON file.

        Args:
            df: DataFrame to export
            output_path: Path to output JSON file
        """
        df.to_json(output_path, orient="records", indent=2)

    def get_summary_stats(self, repo_name: str) -> dict:
        """
        Get summary statistics for a repository.

        Args:
            repo_name: Name of the repository

        Returns:
            Dictionary with summary statistics
        """
        conn = self.db_manager.get_connection(repo_name, "history")
        cursor = conn.cursor()

        stats = {}
        stats["total_commits"] = cursor.execute("SELECT COUNT(*) FROM commits").fetchone()[0]
        stats["total_authors"] = cursor.execute("SELECT COUNT(*) FROM authors").fetchone()[0]
        stats["files_tracked"] = cursor.execute(
            "SELECT COUNT(DISTINCT file_path) FROM file_changes WHERE change_type != 'D'"
        ).fetchone()[0]
        stats["temporal_couplings"] = cursor.execute(
            "SELECT COUNT(*) FROM temporal_coupling"
        ).fetchone()[0]

        # Get date range
        date_range = cursor.execute(
            "SELECT MIN(timestamp), MAX(timestamp) FROM commits"
        ).fetchone()
        stats["first_commit"] = date_range[0]
        stats["last_commit"] = date_range[1]

        conn.close()
        return stats
