#!/usr/bin/env python3
"""Data loader: Commit patterns for all repositories."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from depanalysis.db_manager import DatabaseManager


def get_commit_patterns(repo_name: str, db_manager: DatabaseManager) -> dict:
    """Get commit pattern data for a repository."""
    if not db_manager.repo_exists(repo_name):
        return None

    try:
        conn = db_manager.get_connection(repo_name, "history")
        cursor = conn.cursor()

        # Commits by day of week and hour
        commits_by_time = cursor.execute("""
            SELECT
                strftime('%w', timestamp) AS day_of_week,
                strftime('%H', timestamp) AS hour,
                COUNT(*) AS commit_count
            FROM commits
            GROUP BY day_of_week, hour
            ORDER BY commit_count DESC
        """).fetchall()

        # Active development areas (files with recent commits)
        active_areas = cursor.execute("""
            SELECT
                fc.file_path,
                COUNT(DISTINCT c.commit_hash) AS recent_commits,
                MAX(c.timestamp) AS last_commit
            FROM file_changes fc
            JOIN commits c ON fc.commit_hash = c.commit_hash
            WHERE c.timestamp >= datetime('now', '-30 days')
            GROUP BY fc.file_path
            ORDER BY recent_commits DESC
            LIMIT 20
        """).fetchall()

        # Overall commit stats
        stats = cursor.execute("""
            SELECT
                COUNT(*) AS total_commits,
                COUNT(DISTINCT author_name) AS total_authors,
                MIN(timestamp) AS first_commit,
                MAX(timestamp) AS last_commit
            FROM commits
        """).fetchone()

        # Commits per week trend
        weekly_trend = cursor.execute("""
            SELECT
                strftime('%Y-%W', timestamp) AS week,
                COUNT(*) AS commit_count
            FROM commits
            GROUP BY week
            ORDER BY week DESC
            LIMIT 52
        """).fetchall()

        conn.close()

        return {
            "repository": repo_name,
            "commits_by_time": [
                {"day": int(row[0]), "hour": int(row[1]), "count": row[2]}
                for row in commits_by_time
            ],
            "active_areas": [
                {"file": row[0], "recent_commits": row[1], "last_commit": row[2]}
                for row in active_areas
            ],
            "weekly_trend": [
                {"week": row[0], "count": row[1]}
                for row in weekly_trend
            ],
            "statistics": {
                "total_commits": stats[0] or 0,
                "total_authors": stats[1] or 0,
                "first_commit": stats[2],
                "last_commit": stats[3]
            }
        }
    except Exception:
        return None


def main():
    data_dir = Path(__file__).parent.parent.parent.parent / "data"
    db_manager = DatabaseManager(data_dir=data_dir)

    all_data = {}
    repos = db_manager.list_analyzed_repos()

    for repo_name in repos:
        data = get_commit_patterns(repo_name, db_manager)
        if data:
            all_data[repo_name] = data

    print(json.dumps(all_data, indent=2))


if __name__ == "__main__":
    main()
