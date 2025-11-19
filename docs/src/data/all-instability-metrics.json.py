#!/usr/bin/env python3
"""Data loader: Instability metrics for all repositories.

Returns coupling and instability data for all repositories.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from depanalysis.db_manager import DatabaseManager


def get_instability_metrics(repo_name: str, db_manager: DatabaseManager) -> dict:
    """Get instability metrics for a repository."""
    if not db_manager.repo_exists(repo_name):
        return None

    try:
        conn = db_manager.get_connection(repo_name, "structure")
        cursor = conn.cursor()

        # Module instability metrics
        metrics = cursor.execute("""
            SELECT
                module_path,
                afferent_coupling,
                efferent_coupling,
                instability,
                total_functions,
                total_classes
            FROM module_metrics
            ORDER BY instability DESC
        """).fetchall()

        # Summary statistics
        stats = cursor.execute("""
            SELECT
                COUNT(*) as total_modules,
                AVG(instability) as avg_instability,
                AVG(afferent_coupling) as avg_afferent,
                AVG(efferent_coupling) as avg_efferent
            FROM module_metrics
        """).fetchone()

        conn.close()

        return {
            "repository": repo_name,
            "modules": [
                {
                    "path": row[0],
                    "afferent": row[1],
                    "efferent": row[2],
                    "instability": round(row[3], 3) if row[3] is not None else 0,
                    "functions": row[4] or 0,
                    "classes": row[5] or 0
                }
                for row in metrics
            ],
            "statistics": {
                "total_modules": stats[0] or 0,
                "avg_instability": round(stats[1], 3) if stats[1] is not None else 0,
                "avg_afferent": round(stats[2], 2) if stats[2] is not None else 0,
                "avg_efferent": round(stats[3], 2) if stats[3] is not None else 0
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
        data = get_instability_metrics(repo_name, db_manager)
        if data:
            all_data[repo_name] = data

    print(json.dumps(all_data, indent=2))


if __name__ == "__main__":
    main()
