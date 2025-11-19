#!/usr/bin/env python3
"""Data loader: Quality overview for all repositories."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from depanalysis.db_manager import DatabaseManager


def get_quality_overview(repo_name: str, db_manager: DatabaseManager) -> dict:
    """Get combined quality metrics for a repository."""
    if not db_manager.repo_exists(repo_name):
        return None

    try:
        # Get structural metrics
        conn_structure = db_manager.get_connection(repo_name, "structure")
        cursor_structure = conn_structure.cursor()

        # Complexity metrics
        complexity_stats = cursor_structure.execute("""
            SELECT
                AVG(cyclomatic_complexity) AS avg_complexity,
                MAX(cyclomatic_complexity) AS max_complexity,
                SUM(CASE WHEN cyclomatic_complexity > 15 THEN 1 ELSE 0 END) AS high_complexity_count,
                COUNT(*) AS total_functions
            FROM functions
            WHERE cyclomatic_complexity > 0
        """).fetchone()

        # Type safety metrics
        type_stats = cursor_structure.execute("""
            SELECT
                COUNT(DISTINCT f.id) AS total_functions,
                COUNT(DISTINCT CASE WHEN th.id IS NOT NULL THEN f.id END) AS typed_functions
            FROM functions f
            LEFT JOIN type_hints th ON th.function_id = f.id
        """).fetchone()

        conn_structure.close()

        # Calculate quality scores
        total_funcs = complexity_stats[3] or 1
        typed_funcs = type_stats[1] or 0
        high_complexity = complexity_stats[2] or 0

        complexity_score = max(0, 100 - (complexity_stats[0] or 0) * 5)
        type_safety_score = (typed_funcs / total_funcs) * 100 if total_funcs > 0 else 0

        overall_score = (complexity_score * 0.5 + type_safety_score * 0.5)

        return {
            "repository": repo_name,
            "scores": {
                "overall": round(overall_score, 1),
                "complexity": round(complexity_score, 1),
                "type_safety": round(type_safety_score, 1)
            },
            "complexity_metrics": {
                "avg_complexity": round(complexity_stats[0] or 0, 2),
                "max_complexity": complexity_stats[1] or 0,
                "high_complexity_count": high_complexity,
                "total_functions": total_funcs
            },
            "type_metrics": {
                "typed_functions": typed_funcs,
                "total_functions": total_funcs,
                "coverage_percent": round((typed_funcs / total_funcs * 100) if total_funcs > 0 else 0, 1)
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
        data = get_quality_overview(repo_name, db_manager)
        if data:
            all_data[repo_name] = data

    print(json.dumps(all_data, indent=2))


if __name__ == "__main__":
    main()
