#!/usr/bin/env python3
"""Data loader: Polyglot statistics for all repositories."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from depanalysis.db_manager import DatabaseManager


def get_polyglot_stats(repo_name: str, db_manager: DatabaseManager) -> dict:
    """Get polyglot statistics for a repository."""
    if not db_manager.repo_exists(repo_name):
        return None

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

        # Cross-language imports
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

        conn.close()

        return {
            "repository": repo_name,
            "languages": [
                {"name": row[0], "files": row[1], "functions": row[2], "complexity": row[3]}
                for row in language_dist
            ],
            "cross_language_imports": [
                {"from": row[0], "to": row[1], "count": row[2]}
                for row in cross_lang_imports
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
            ]
        }
    except Exception:
        return None


def main():
    data_dir = Path(__file__).parent.parent.parent.parent / "data"
    db_manager = DatabaseManager(data_dir=data_dir)

    all_data = {}
    repos = db_manager.list_analyzed_repos()

    for repo_name in repos:
        data = get_polyglot_stats(repo_name, db_manager)
        if data:
            all_data[repo_name] = data

    print(json.dumps(all_data, indent=2))


if __name__ == "__main__":
    main()
