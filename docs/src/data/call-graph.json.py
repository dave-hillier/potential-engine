#!/usr/bin/env python3
"""Data loader for call graph analysis."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from depanalysis.db_manager import DatabaseManager

def get_call_graph(repo_name: str) -> dict:
    """Get function call graph data."""
    db_manager = DatabaseManager()
    if not db_manager.repo_exists(repo_name):
        return {"error": f"Repository '{repo_name}' not found"}

    try:
        conn = db_manager.get_connection(repo_name, "structure")
        cursor = conn.cursor()

        # Get all function calls
        calls = cursor.execute("""
            SELECT
                f1.name AS caller,
                f2.name AS callee,
                m1.path AS caller_module,
                m2.path AS callee_module,
                c.call_kind
            FROM calls c
            JOIN functions f1 ON c.from_function_id = f1.id
            LEFT JOIN functions f2 ON c.to_function_id = f2.id
            JOIN modules m1 ON f1.module_id = m1.id
            LEFT JOIN modules m2 ON f2.module_id = m2.id
            WHERE f2.name IS NOT NULL
        """).fetchall()

        # Entry points (functions never called)
        entry_points = cursor.execute("""
            SELECT
                f.name,
                m.path AS module,
                f.cyclomatic_complexity
            FROM functions f
            JOIN modules m ON f.module_id = m.id
            WHERE f.id NOT IN (
                SELECT DISTINCT to_function_id FROM calls WHERE to_function_id IS NOT NULL
            )
            ORDER BY f.cyclomatic_complexity DESC
        """).fetchall()

        # Most called functions
        most_called = cursor.execute("""
            SELECT
                f.name,
                m.path AS module,
                COUNT(*) AS call_count
            FROM calls c
            JOIN functions f ON c.to_function_id = f.id
            JOIN modules m ON f.module_id = m.id
            GROUP BY f.id, f.name, m.path
            ORDER BY call_count DESC
            LIMIT 20
        """).fetchall()

        # Call depth analysis (functions with most outgoing calls)
        call_depth = cursor.execute("""
            SELECT
                f.name,
                m.path AS module,
                COUNT(*) AS outgoing_calls
            FROM calls c
            JOIN functions f ON c.from_function_id = f.id
            JOIN modules m ON f.module_id = m.id
            GROUP BY f.id, f.name, m.path
            ORDER BY outgoing_calls DESC
            LIMIT 20
        """).fetchall()

        conn.close()

        return {
            "repository": repo_name,
            "calls": [
                {
                    "caller": row[0],
                    "callee": row[1],
                    "caller_module": row[2],
                    "callee_module": row[3],
                    "call_kind": row[4]
                }
                for row in calls
            ],
            "entry_points": [
                {"name": row[0], "module": row[1], "complexity": row[2]}
                for row in entry_points
            ],
            "most_called": [
                {"name": row[0], "module": row[1], "call_count": row[2]}
                for row in most_called
            ],
            "call_depth": [
                {"name": row[0], "module": row[1], "outgoing_calls": row[2]}
                for row in call_depth
            ],
            "statistics": {
                "total_calls": len(calls),
                "entry_points": len(entry_points),
                "unique_callers": len(set(c[0] for c in calls)),
                "unique_callees": len(set(c[1] for c in calls if c[1]))
            }
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    repo_name = sys.argv[1] if len(sys.argv) > 1 else None
    if not repo_name:
        db_manager = DatabaseManager()
        repos = db_manager.list_analyzed_repos()
        repo_name = repos[0] if repos else None
    print(json.dumps(get_call_graph(repo_name or ""), indent=2) if repo_name else json.dumps({"error": "No repos"}))
