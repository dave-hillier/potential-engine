#!/usr/bin/env python3
"""Data loader for dependency ecosystem analysis."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from depanalysis.db_manager import DatabaseManager

def get_dependency_ecosystem(repo_name: str) -> dict:
    """Get dependency ecosystem data."""
    db_manager = DatabaseManager()
    if not db_manager.repo_exists(repo_name):
        return {"error": f"Repository '{repo_name}' not found"}

    try:
        conn = db_manager.get_connection(repo_name, "structure")
        cursor = conn.cursor()

        # External dependencies by ecosystem
        deps = cursor.execute("""
            SELECT
                pm.ecosystem,
                pm.name AS package_manager,
                ed.package_name,
                ed.version,
                ed.is_dev_dependency,
                ed.is_transitive
            FROM external_dependencies ed
            JOIN package_managers pm ON ed.package_manager_id = pm.id
            ORDER BY pm.ecosystem, ed.package_name
        """).fetchall()

        # Version conflicts
        conflicts = cursor.execute("""
            SELECT package_name, version1, version2, conflict_type
            FROM dependency_conflicts
            ORDER BY conflict_type DESC
        """).fetchall()

        conn.close()

        return {
            "repository": repo_name,
            "dependencies": [
                {"ecosystem": r[0], "package_manager": r[1], "package": r[2],
                 "version": r[3], "is_dev": bool(r[4]), "is_transitive": bool(r[5])}
                for r in deps
            ],
            "conflicts": [
                {"package": r[0], "version1": r[1], "version2": r[2], "type": r[3]}
                for r in conflicts
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
    print(json.dumps(get_dependency_ecosystem(repo_name or ""), indent=2) if repo_name else json.dumps({"error": "No repos"}))
