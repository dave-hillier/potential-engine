#!/usr/bin/env python3
"""Data loader: Complexity distribution for all repositories.

Returns complexity data for all repositories with repo_name field.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from depanalysis.db_manager import DatabaseManager


def get_complexity_distribution(repo_name: str, db_manager: DatabaseManager) -> dict:
    """Get complexity distribution for a repository."""
    if not db_manager.repo_exists(repo_name):
        return None

    try:
        conn = db_manager.get_connection(repo_name, "structure")
        cursor = conn.cursor()

        # Function complexity distribution
        functions = cursor.execute("""
            SELECT
                f.name,
                f.cyclomatic_complexity,
                m.path AS module_path,
                f.start_line
            FROM functions f
            JOIN modules m ON f.module_id = m.id
            WHERE f.cyclomatic_complexity > 0
            ORDER BY f.cyclomatic_complexity DESC
        """).fetchall()

        # Complexity stats
        stats = cursor.execute("""
            SELECT
                COUNT(*) AS total_functions,
                AVG(cyclomatic_complexity) AS avg_complexity,
                MAX(cyclomatic_complexity) AS max_complexity,
                SUM(CASE WHEN cyclomatic_complexity > 15 THEN 1 ELSE 0 END) AS high_complexity_count
            FROM functions
            WHERE cyclomatic_complexity > 0
        """).fetchone()

        conn.close()

        return {
            "repository": repo_name,
            "functions": [
                {"name": row[0], "complexity": row[1], "module": row[2], "line": row[3]}
                for row in functions
            ],
            "statistics": {
                "total_functions": stats[0] or 0,
                "avg_complexity": round(stats[1] or 0, 2),
                "max_complexity": stats[2] or 0,
                "high_complexity_count": stats[3] or 0
            }
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
        data = get_complexity_distribution(repo_name, db_manager)
        if data:
            all_data[repo_name] = data

    print(json.dumps(all_data, indent=2))


if __name__ == "__main__":
    main()
