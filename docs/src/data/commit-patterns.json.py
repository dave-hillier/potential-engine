#!/usr/bin/env python3
"""Data loader for commit pattern analysis."""
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from depanalysis.db_manager import DatabaseManager

def get_commit_patterns(repo_name: str) -> dict:
    """Get commit pattern data."""
    # Point to data directory in repo root (not docs/)
    data_dir = Path(__file__).parent.parent.parent.parent / "data"
    db_manager = DatabaseManager(data_dir=data_dir)
    if not db_manager.repo_exists(repo_name):
        return {"error": f"Repository '{repo_name}' not found"}

    try:
        conn = db_manager.get_connection(repo_name, "history")
        cursor = conn.cursor()

        # Commit frequency over time
        frequency = cursor.execute("""
            SELECT
                file_path,
                week_start,
                commit_count
            FROM commit_frequency
            ORDER BY week_start DESC
        """).fetchall()

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
            "frequency": [
                {"file": row[0], "week": row[1], "count": row[2]}
                for row in frequency[:100]  # Limit to recent data
            ],
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
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    repo_name = sys.argv[1] if len(sys.argv) > 1 else None
    if not repo_name:
        # Point to data directory in repo root (not docs/)
        data_dir = Path(__file__).parent.parent.parent.parent / "data"
        db_manager = DatabaseManager(data_dir=data_dir)
        repos = db_manager.list_analyzed_repos()
        repo_name = repos[0] if repos else None
    print(json.dumps(get_commit_patterns(repo_name or ""), indent=2) if repo_name else json.dumps({"error": "No repos"}))
