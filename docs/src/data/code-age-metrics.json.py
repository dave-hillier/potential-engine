#!/usr/bin/env python3
"""Data loader for code age and churn metrics."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from depanalysis.db_manager import DatabaseManager

def get_code_age_metrics(repo_name: str) -> dict:
    """Get code age and churn metrics."""
    db_manager = DatabaseManager()
    if not db_manager.repo_exists(repo_name):
        return {"error": f"Repository '{repo_name}' not found"}

    try:
        # Get churn metrics from history.db
        conn_history = db_manager.get_connection(repo_name, "history")
        cursor = conn_history.cursor()

        # Code age data
        age_data = cursor.execute("""
            SELECT
                file_path,
                days_since_last_change,
                last_commit_date
            FROM code_age
            ORDER BY days_since_last_change DESC
        """).fetchall()

        # Churn metrics
        churn_data = cursor.execute("""
            SELECT
                file_path,
                change_count,
                total_lines_added,
                total_lines_deleted,
                change_count + total_lines_added + total_lines_deleted AS churn_score
            FROM churn_metrics
            ORDER BY churn_score DESC
        """).fetchall()

        conn_history.close()

        return {
            "repository": repo_name,
            "age_data": [
                {"file": row[0], "days_old": row[1], "last_modified": row[2]}
                for row in age_data
            ],
            "churn_data": [
                {
                    "file": row[0],
                    "changes": row[1],
                    "lines_added": row[2],
                    "lines_deleted": row[3],
                    "churn_score": row[4]
                }
                for row in churn_data
            ]
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    repo_name = sys.argv[1] if len(sys.argv) > 1 else None
    if not repo_name:
        db_manager = DatabaseManager()
        repos = db_manager.list_analyzed_repos()
        repo_name = repos[0] if repos else None
    print(json.dumps(get_code_age_metrics(repo_name or ""), indent=2) if repo_name else json.dumps({"error": "No repos"}))
