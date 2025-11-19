#!/usr/bin/env python3
"""
Data loader for instability metrics (afferent/efferent coupling).

Provides NDepend-style coupling and instability analysis.
"""
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from depanalysis.db_manager import DatabaseManager


def get_instability_metrics(repo_name: str) -> dict:
    """Get instability metrics for a repository."""
    # Point to data directory in repo root (not docs/)
    data_dir = Path(__file__).parent.parent.parent.parent / "data"
    db_manager = DatabaseManager(data_dir=data_dir)

    if not db_manager.repo_exists(repo_name):
        return {"error": f"Repository '{repo_name}' not found"}

    try:
        conn = db_manager.get_connection(repo_name, "structure")
        cursor = conn.cursor()

        # Get instability metrics from view
        instability_data = cursor.execute("""
            SELECT
                module_path,
                ca,
                ce,
                instability,
                CASE
                    WHEN instability > 0.8 AND ca > 5 THEN 'high_risk'
                    WHEN instability < 0.2 AND ce > 5 THEN 'rigid'
                    ELSE 'normal'
                END AS classification
            FROM instability
            ORDER BY instability DESC
        """).fetchall()

        # Get coupling distribution stats
        coupling_stats = cursor.execute("""
            SELECT
                AVG(ca) AS avg_ca,
                MAX(ca) AS max_ca,
                AVG(ce) AS avg_ce,
                MAX(ce) AS max_ce,
                AVG(instability) AS avg_instability
            FROM instability
        """).fetchone()

        conn.close()

        return {
            "repository": repo_name,
            "modules": [
                {
                    "path": row[0],
                    "ca": row[1],
                    "ce": row[2],
                    "instability": round(row[3], 3),
                    "classification": row[4]
                }
                for row in instability_data
            ],
            "statistics": {
                "avg_ca": round(coupling_stats[0] or 0, 2),
                "max_ca": coupling_stats[1] or 0,
                "avg_ce": round(coupling_stats[2] or 0, 2),
                "max_ce": coupling_stats[3] or 0,
                "avg_instability": round(coupling_stats[4] or 0, 3)
            }
        }

    except Exception as e:
        return {"error": str(e)}


def main():
    """Main entry point for data loader."""
    repo_name = sys.argv[1] if len(sys.argv) > 1 else None

    if not repo_name:
        # Point to data directory in repo root (not docs/)
        data_dir = Path(__file__).parent.parent.parent.parent / "data"
        db_manager = DatabaseManager(data_dir=data_dir)
        repos = db_manager.list_analyzed_repos()
        if repos:
            repo_name = repos[0]
        else:
            print(json.dumps({"error": "No repositories found"}))
            return

    data = get_instability_metrics(repo_name)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
