#!/usr/bin/env python3
"""Data loader for decorator usage analysis."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from depanalysis.db_manager import DatabaseManager

def get_decorator_usage(repo_name: str) -> dict:
    """Get decorator usage patterns."""
    # Point to data directory in repo root (not docs/)
    data_dir = Path(__file__).parent.parent.parent.parent / "data"
    db_manager = DatabaseManager(data_dir=data_dir)
    if not db_manager.repo_exists(repo_name):
        return {"error": f"Repository '{repo_name}' not found"}

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
    print(json.dumps(get_decorator_usage(repo_name or ""), indent=2) if repo_name else json.dumps({"error": "No repos"}))
