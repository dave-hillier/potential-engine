#!/usr/bin/env python3
"""Data loader: Decorator usage for all repositories."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from depanalysis.db_manager import DatabaseManager


def get_decorator_usage(repo_name: str, db_manager: DatabaseManager) -> dict:
    """Get decorator usage patterns for a repository."""
    if not db_manager.repo_exists(repo_name):
        return None

    try:
        conn = db_manager.get_connection(repo_name, "structure")
        cursor = conn.cursor()

        # Decorator frequency
        decorators = cursor.execute("""
            SELECT
                d.decorator_name,
                COUNT(*) AS usage_count,
                m.path
            FROM decorators d
            JOIN functions f ON d.function_id = f.id
            JOIN modules m ON f.module_id = m.id
            GROUP BY d.decorator_name, m.path
            ORDER BY usage_count DESC
        """).fetchall()

        # Most decorated functions
        functions = cursor.execute("""
            SELECT
                f.name,
                m.path,
                COUNT(d.id) AS decorator_count
            FROM functions f
            JOIN modules m ON f.module_id = m.id
            JOIN decorators d ON d.function_id = f.id
            GROUP BY f.id, f.name, m.path
            ORDER BY decorator_count DESC
            LIMIT 20
        """).fetchall()

        # Stats
        stats = cursor.execute("""
            SELECT
                COUNT(DISTINCT decorator_name) AS unique_decorators,
                COUNT(*) AS total_usage
            FROM decorators
        """).fetchone()

        conn.close()

        return {
            "repository": repo_name,
            "decorators": [
                {"name": row[0], "count": row[1], "module": row[2]}
                for row in decorators
            ],
            "functions": [
                {"name": row[0], "module": row[1], "decorator_count": row[2]}
                for row in functions
            ],
            "statistics": {
                "unique_decorators": stats[0] or 0,
                "total_usage": stats[1] or 0
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
        data = get_decorator_usage(repo_name, db_manager)
        if data:
            all_data[repo_name] = data

    print(json.dumps(all_data, indent=2))


if __name__ == "__main__":
    main()
