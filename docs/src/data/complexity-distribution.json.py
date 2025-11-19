#!/usr/bin/env python3
"""Data loader for complexity distribution metrics."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from depanalysis.db_manager import DatabaseManager


def get_complexity_distribution(repo_name: str) -> dict:
    """Get complexity distribution for a repository."""
    # Point to data directory in repo root (not docs/)
    data_dir = Path(__file__).parent.parent.parent.parent / "data"
    db_manager = DatabaseManager(data_dir=data_dir)

    if not db_manager.repo_exists(repo_name):
        return {"error": f"Repository '{repo_name}' not found"}

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

        # Module complexity summary
        modules = cursor.execute("""
            SELECT
                module_path,
                function_count,
                avg_complexity,
                total_complexity
            FROM module_complexity
            ORDER BY total_complexity DESC
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
            "modules": [
                {"path": row[0], "function_count": row[1], "avg_complexity": round(row[2], 2), "total_complexity": row[3]}
                for row in modules
            ],
            "statistics": {
                "total_functions": stats[0] or 0,
                "avg_complexity": round(stats[1] or 0, 2),
                "max_complexity": stats[2] or 0,
                "high_complexity_count": stats[3] or 0
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
    if repo_name:
        print(json.dumps(get_complexity_distribution(repo_name), indent=2))
    else:
        print(json.dumps({"error": "No repositories found"}))
