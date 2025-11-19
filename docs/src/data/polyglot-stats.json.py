#!/usr/bin/env python3
"""
Data loader for polyglot repository statistics.

Provides language distribution and cross-language metrics for Observable Framework.
"""
import json
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from depanalysis.db_manager import DatabaseManager


def get_polyglot_stats(repo_name: str) -> dict:
    """Get polyglot statistics for a repository."""
    # Point to data directory in repo root (not docs/)
    data_dir = Path(__file__).parent.parent.parent.parent / "data"
    db_manager = DatabaseManager(data_dir=data_dir)

    if not db_manager.repo_exists(repo_name):
        return {"error": f"Repository '{repo_name}' not found"}

    try:
        conn = db_manager.get_connection(repo_name, "structure")
        cursor = conn.cursor()

        # Language distribution
        language_dist = cursor.execute("""
            SELECT
                l.name AS language,
                COUNT(DISTINCT m.id) AS file_count,
                SUM(COALESCE(mc.function_count, 0)) AS total_functions,
                SUM(COALESCE(mc.total_complexity, 0)) AS total_complexity
            FROM languages l
            LEFT JOIN modules m ON m.language_id = l.id
            LEFT JOIN module_complexity mc ON mc.module_id = m.id
            GROUP BY l.name
            HAVING file_count > 0
            ORDER BY file_count DESC
        """).fetchall()

        # Cross-language imports (if modules in different languages import each other)
        cross_lang_imports = cursor.execute("""
            SELECT
                l1.name AS from_language,
                l2.name AS to_language,
                COUNT(*) AS import_count
            FROM imports i
            JOIN modules m1 ON i.from_module_id = m1.id
            JOIN languages l1 ON m1.language_id = l1.id
            LEFT JOIN modules m2 ON i.to_module = m2.path OR i.to_module = m2.name
            LEFT JOIN languages l2 ON m2.language_id = l2.id
            WHERE l2.name IS NOT NULL AND l1.name != l2.name
            GROUP BY l1.name, l2.name
        """).fetchall()

        # API endpoints by language
        api_endpoints = cursor.execute("""
            SELECT
                l.name AS language,
                e.endpoint_type,
                COUNT(*) AS endpoint_count
            FROM api_endpoints e
            JOIN modules m ON e.module_id = m.id
            JOIN languages l ON m.language_id = l.id
            GROUP BY l.name, e.endpoint_type
        """).fetchall()

        # API calls by language
        api_calls = cursor.execute("""
            SELECT
                l.name AS language,
                c.call_type,
                COUNT(*) AS call_count
            FROM api_calls c
            JOIN modules m ON c.from_module_id = m.id
            JOIN languages l ON m.language_id = l.id
            GROUP BY l.name, c.call_type
        """).fetchall()

        # Shared types
        shared_types = cursor.execute("""
            SELECT
                type_system,
                COUNT(*) AS type_count
            FROM shared_types
            GROUP BY type_system
        """).fetchall()

        # External dependencies by ecosystem
        external_deps = cursor.execute("""
            SELECT
                pm.ecosystem,
                pm.name AS package_manager,
                COUNT(DISTINCT ed.package_name) AS unique_packages,
                SUM(CASE WHEN ed.is_dev_dependency THEN 0 ELSE 1 END) AS prod_packages,
                SUM(CASE WHEN ed.is_dev_dependency THEN 1 ELSE 0 END) AS dev_packages
            FROM package_managers pm
            LEFT JOIN external_dependencies ed ON pm.id = ed.package_manager_id
            GROUP BY pm.ecosystem, pm.name
            HAVING unique_packages > 0
        """).fetchall()

        # Version conflicts
        version_conflicts = cursor.execute("""
            SELECT
                package_name,
                version1,
                version2,
                conflict_type
            FROM dependency_conflicts
            ORDER BY conflict_type DESC
        """).fetchall()

        conn.close()

        return {
            "repository": repo_name,
            "languages": [
                {
                    "name": row[0],
                    "files": row[1],
                    "functions": row[2],
                    "complexity": row[3]
                }
                for row in language_dist
            ],
            "cross_language_imports": [
                {
                    "from": row[0],
                    "to": row[1],
                    "count": row[2]
                }
                for row in cross_lang_imports
            ],
            "api_endpoints": [
                {
                    "language": row[0],
                    "type": row[1],
                    "count": row[2]
                }
                for row in api_endpoints
            ],
            "api_calls": [
                {
                    "language": row[0],
                    "type": row[1],
                    "count": row[2]
                }
                for row in api_calls
            ],
            "shared_types": [
                {
                    "type_system": row[0],
                    "count": row[1]
                }
                for row in shared_types
            ],
            "external_dependencies": [
                {
                    "ecosystem": row[0],
                    "package_manager": row[1],
                    "unique_packages": row[2],
                    "prod_packages": row[3],
                    "dev_packages": row[4]
                }
                for row in external_deps
            ],
            "version_conflicts": [
                {
                    "package": row[0],
                    "version1": row[1],
                    "version2": row[2],
                    "conflict_type": row[3]
                }
                for row in version_conflicts
            ]
        }

    except Exception as e:
        return {"error": str(e)}


def main():
    """Main entry point for data loader."""
    # Get repository name from command line or use default
    repo_name = sys.argv[1] if len(sys.argv) > 1 else None

    if not repo_name:
        # Get list of all repos
        # Point to data directory in repo root (not docs/)
        data_dir = Path(__file__).parent.parent.parent.parent / "data"
        db_manager = DatabaseManager(data_dir=data_dir)
        repos = db_manager.list_analyzed_repos()
        if repos:
            repo_name = repos[0]  # Use first repo as default
        else:
            print(json.dumps({"error": "No repositories found"}))
            return

    stats = get_polyglot_stats(repo_name)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
