#!/usr/bin/env python3
"""Data loader: Code age metrics for all repositories.

Returns age and churn data for all repositories with repo_name field.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from depanalysis.db_manager import DatabaseManager


def get_code_age_metrics(repo_name: str, db_manager: DatabaseManager) -> dict:
    """Get code age and churn metrics for a repository."""
    if not db_manager.repo_exists(repo_name):
        return None

    try:
        conn = db_manager.get_connection(repo_name, "history")
        cursor = conn.cursor()

        # File age data
        age_data = cursor.execute("""
            SELECT
                file_path,
                julianday('now') - julianday(last_modified) as days_old,
                last_modified
            FROM file_changes
            WHERE last_modified IS NOT NULL
            ORDER BY days_old DESC
            LIMIT 50
        """).fetchall()

        # Churn data
        churn_data = cursor.execute("""
            SELECT
                file_path,
                changes,
                lines_added,
                lines_deleted,
                lines_added + lines_deleted as churn_score
            FROM (
                SELECT
                    file_path,
                    COUNT(*) as changes,
                    SUM(lines_added) as lines_added,
                    SUM(lines_deleted) as lines_deleted
                FROM file_changes
                GROUP BY file_path
            )
            ORDER BY churn_score DESC
            LIMIT 50
        """).fetchall()

        conn.close()

        return {
            "repository": repo_name,
            "age_data": [
                {
                    "file": row[0],
                    "days_old": round(row[1], 1),
                    "last_modified": row[2]
                }
                for row in age_data
            ],
            "churn_data": [
                {
                    "file": row[0],
                    "changes": row[1],
                    "lines_added": row[2] or 0,
                    "lines_deleted": row[3] or 0,
                    "churn_score": row[4] or 0
                }
                for row in churn_data
            ]
        }
    except Exception:
        return None


def main():
    # Point to data directory in repo root (not docs/)
    data_dir = Path(__file__).parent.parent.parent.parent / "data"
    db_manager = DatabaseManager(data_dir=data_dir)

    all_data = {}

    # Get all repositories
    repos = db_manager.list_analyzed_repos()

    for repo_name in repos:
        data = get_code_age_metrics(repo_name, db_manager)
        if data:
            all_data[repo_name] = data

    print(json.dumps(all_data, indent=2))


if __name__ == "__main__":
    main()
