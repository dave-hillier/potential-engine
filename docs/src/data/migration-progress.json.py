#!/usr/bin/env python3
"""
Data loader for migration progress visualization.

Usage: migration-progress.json.py <repo_name> <migration_id>
"""
import json
import sqlite3
import sys
from pathlib import Path


def get_migration_progress(repo_name: str, migration_id: str) -> dict:
    """Get migration progress data for Observable visualization."""
    db_path = Path(f"../../data/{repo_name}/history.db")

    if not db_path.exists():
        return {
            "error": f"Database not found for repository: {repo_name}",
            "migration_id": migration_id,
        }

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get migration project info
    project = cursor.execute(
        """
        SELECT id, name, description, target_date, tags
        FROM migration_projects
        WHERE id = ?
    """,
        (migration_id,),
    ).fetchone()

    if not project:
        conn.close()
        return {
            "error": f"Migration project not found: {migration_id}",
            "repo_name": repo_name,
        }

    # Get pattern statistics
    patterns = cursor.execute(
        """
        SELECT
            mp.id,
            mp.name,
            mp.description,
            mp.severity,
            mp.category,
            COUNT(DISTINCT mo.id) as occurrence_count,
            COUNT(DISTINCT mo.file_path) as affected_files
        FROM migration_patterns mp
        LEFT JOIN migration_occurrences mo ON mp.id = mo.pattern_id
        WHERE mp.migration_id = ?
        GROUP BY mp.id, mp.name, mp.description, mp.severity, mp.category
        ORDER BY occurrence_count DESC
    """,
        (migration_id,),
    ).fetchall()

    pattern_data = []
    for pattern in patterns:
        pattern_data.append(
            {
                "id": pattern[0],
                "name": pattern[1],
                "description": pattern[2],
                "severity": pattern[3],
                "category": pattern[4],
                "occurrences": pattern[5],
                "affectedFiles": pattern[6],
            }
        )

    # Get file-level breakdown
    files = cursor.execute(
        """
        SELECT
            mo.file_path,
            mp.severity,
            COUNT(mo.id) as occurrence_count,
            GROUP_CONCAT(DISTINCT mp.name) as patterns
        FROM migration_occurrences mo
        JOIN migration_patterns mp ON mo.pattern_id = mp.id
        WHERE mp.migration_id = ?
        GROUP BY mo.file_path, mp.severity
        ORDER BY occurrence_count DESC
        LIMIT 100
    """,
        (migration_id,),
    ).fetchall()

    file_data = []
    for file_info in files:
        file_data.append(
            {
                "path": file_info[0],
                "severity": file_info[1],
                "occurrences": file_info[2],
                "patterns": file_info[3].split(",") if file_info[3] else [],
            }
        )

    # Get severity breakdown
    severity_counts = {}
    total_occurrences = 0
    for pattern in pattern_data:
        severity = pattern["severity"]
        count = pattern["occurrences"]
        severity_counts[severity] = severity_counts.get(severity, 0) + count
        total_occurrences += count

    # Get timeline data (if multiple scans)
    timeline = cursor.execute(
        """
        SELECT
            DATE(scanned_at) as scan_date,
            COUNT(DISTINCT id) as occurrence_count
        FROM migration_occurrences mo
        JOIN migration_patterns mp ON mo.pattern_id = mp.id
        WHERE mp.migration_id = ?
        GROUP BY DATE(scanned_at)
        ORDER BY scan_date
    """,
        (migration_id,),
    ).fetchall()

    timeline_data = [{"date": t[0], "occurrences": t[1]} for t in timeline]

    conn.close()

    return {
        "repo_name": repo_name,
        "migration": {
            "id": project[0],
            "name": project[1],
            "description": project[2],
            "targetDate": project[3],
            "tags": project[4].split(",") if project[4] else [],
        },
        "summary": {
            "totalOccurrences": total_occurrences,
            "affectedFiles": len(set(f["path"] for f in file_data)),
            "patterns": len(pattern_data),
            "bySeverity": severity_counts,
        },
        "patterns": pattern_data,
        "files": file_data,
        "timeline": timeline_data,
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        # Default to empty data
        result = {"error": "Usage: migration-progress.json.py <repo_name> <migration_id>"}
    else:
        repo_name = sys.argv[1]
        migration_id = sys.argv[2]
        result = get_migration_progress(repo_name, migration_id)

    print(json.dumps(result, indent=2))
