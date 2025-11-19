#!/usr/bin/env python3
"""Data loader for inheritance hierarchy analysis."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from depanalysis.db_manager import DatabaseManager

def get_inheritance_tree(repo_name: str) -> dict:
    """Get class inheritance hierarchy data."""
    db_manager = DatabaseManager()
    if not db_manager.repo_exists(repo_name):
        return {"error": f"Repository '{repo_name}' not found"}

    try:
        conn = db_manager.get_connection(repo_name, "structure")
        cursor = conn.cursor()

        # Get all inheritance relationships
        inheritance = cursor.execute("""
            SELECT
                c1.name AS child_class,
                c2.name AS parent_class,
                m1.path AS child_module,
                m2.path AS parent_module,
                i.relationship_kind
            FROM inheritance i
            JOIN classes c1 ON i.from_class_id = c1.id
            LEFT JOIN classes c2 ON i.to_class_id = c2.id
            JOIN modules m1 ON c1.module_id = m1.id
            LEFT JOIN modules m2 ON c2.module_id = m2.id
            WHERE c2.name IS NOT NULL
        """).fetchall()

        # Calculate inheritance depth (simplified - just count levels)
        depth_analysis = cursor.execute("""
            SELECT
                c.name,
                m.path AS module,
                COUNT(*) AS parent_count
            FROM inheritance i
            JOIN classes c ON i.from_class_id = c.id
            JOIN modules m ON c.module_id = m.id
            GROUP BY c.id, c.name, m.path
            ORDER BY parent_count DESC
        """).fetchall()

        # Most extended classes (base classes)
        most_extended = cursor.execute("""
            SELECT
                c.name,
                m.path AS module,
                COUNT(*) AS child_count
            FROM inheritance i
            JOIN classes c ON i.to_class_id = c.id
            JOIN modules m ON c.module_id = m.id
            GROUP BY c.id, c.name, m.path
            ORDER BY child_count DESC
            LIMIT 20
        """).fetchall()

        # Classes by kind
        class_kinds = cursor.execute("""
            SELECT
                class_kind,
                COUNT(*) AS count
            FROM classes
            GROUP BY class_kind
        """).fetchall()

        conn.close()

        return {
            "repository": repo_name,
            "relationships": [
                {
                    "child": row[0],
                    "parent": row[1],
                    "child_module": row[2],
                    "parent_module": row[3],
                    "kind": row[4]
                }
                for row in inheritance
            ],
            "depth_analysis": [
                {"class": row[0], "module": row[1], "parent_count": row[2]}
                for row in depth_analysis
            ],
            "most_extended": [
                {"class": row[0], "module": row[1], "child_count": row[2]}
                for row in most_extended
            ],
            "class_kinds": [
                {"kind": row[0], "count": row[1]}
                for row in class_kinds
            ],
            "statistics": {
                "total_relationships": len(inheritance),
                "unique_children": len(set(r[0] for r in inheritance)),
                "unique_parents": len(set(r[1] for r in inheritance if r[1]))
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
    print(json.dumps(get_inheritance_tree(repo_name or ""), indent=2) if repo_name else json.dumps({"error": "No repos"}))
