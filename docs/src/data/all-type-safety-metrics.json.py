#!/usr/bin/env python3
"""Data loader: Type safety metrics for all repositories."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from depanalysis.db_manager import DatabaseManager


def get_type_safety_metrics(repo_name: str, db_manager: DatabaseManager) -> dict:
    """Get type safety metrics for a repository."""
    if not db_manager.repo_exists(repo_name):
        return None

    try:
        conn = db_manager.get_connection(repo_name, "structure")
        cursor = conn.cursor()

        # Type hint coverage by module
        modules = cursor.execute("""
            SELECT
                m.path,
                COUNT(DISTINCT f.id) AS total_functions,
                COUNT(DISTINCT CASE WHEN th.id IS NOT NULL THEN f.id END) AS typed_functions
            FROM modules m
            LEFT JOIN functions f ON f.module_id = m.id
            LEFT JOIN type_hints th ON th.function_id = f.id
            GROUP BY m.path
            HAVING total_functions > 0
        """).fetchall()

        # Generic parameters usage
        generics = cursor.execute("""
            SELECT
                gp.parameter_name,
                COUNT(*) AS usage_count
            FROM generic_parameters gp
            GROUP BY gp.parameter_name
            ORDER BY usage_count DESC
        """).fetchall()

        # Overall stats
        stats = cursor.execute("""
            SELECT
                COUNT(DISTINCT f.id) AS total_functions,
                COUNT(DISTINCT CASE WHEN th.id IS NOT NULL THEN f.id END) AS typed_functions
            FROM functions f
            LEFT JOIN type_hints th ON th.function_id = f.id
        """).fetchone()

        conn.close()

        total = stats[0] or 0
        typed = stats[1] or 0
        coverage = (typed / total * 100) if total > 0 else 0

        return {
            "repository": repo_name,
            "modules": [
                {
                    "path": row[0],
                    "total_functions": row[1],
                    "typed_functions": row[2],
                    "coverage": round((row[2] / row[1] * 100) if row[1] > 0 else 0, 1)
                }
                for row in modules
            ],
            "generics": [{"name": row[0], "count": row[1]} for row in generics],
            "statistics": {
                "total_functions": total,
                "typed_functions": typed,
                "coverage_percent": round(coverage, 1)
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
        data = get_type_safety_metrics(repo_name, db_manager)
        if data:
            all_data[repo_name] = data

    print(json.dumps(all_data, indent=2))


if __name__ == "__main__":
    main()
