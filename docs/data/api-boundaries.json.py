#!/usr/bin/env python3
"""
Data loader for API boundary analysis.

Provides API endpoint and call mapping for Observable Framework visualizations.
"""
import json
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from depanalysis.db_manager import DatabaseManager


def get_api_boundaries(repo_name: str) -> dict:
    """Get API boundary coupling data for a repository."""
    db_manager = DatabaseManager()

    if not db_manager.repo_exists(repo_name):
        return {"error": f"Repository '{repo_name}' not found"}

    try:
        conn = db_manager.get_connection(repo_name, "structure")
        cursor = conn.cursor()

        # Get all API endpoints with module info
        endpoints = cursor.execute("""
            SELECT
                e.id,
                e.endpoint_type,
                e.method,
                e.path,
                e.line_number,
                m.path AS module_path,
                l.name AS language
            FROM api_endpoints e
            JOIN modules m ON e.module_id = m.id
            JOIN languages l ON m.language_id = l.id
            ORDER BY e.path
        """).fetchall()

        # Get all API calls with module info
        calls = cursor.execute("""
            SELECT
                c.id,
                c.call_type,
                c.method,
                c.url_pattern,
                c.line_number,
                m.path AS module_path,
                l.name AS language
            FROM api_calls c
            JOIN modules m ON c.from_module_id = m.id
            JOIN languages l ON m.language_id = l.id
            ORDER BY c.url_pattern
        """).fetchall()

        # Match calls to endpoints (simple pattern matching)
        matched_boundaries = []
        for call in calls:
            call_url = call[3]
            for endpoint in endpoints:
                endpoint_path = endpoint[3]
                # Simple matching - could be enhanced with regex
                if endpoint_path in call_url:
                    matched_boundaries.append({
                        "call_url": call_url,
                        "call_method": call[2],
                        "call_type": call[1],
                        "caller_module": call[5],
                        "caller_language": call[6],
                        "caller_line": call[4],
                        "endpoint_path": endpoint_path,
                        "endpoint_method": endpoint[2],
                        "endpoint_type": endpoint[1],
                        "endpoint_module": endpoint[5],
                        "endpoint_language": endpoint[6],
                        "endpoint_line": endpoint[4]
                    })

        # Unmatched calls (potential external APIs or missing endpoints)
        matched_urls = {m["call_url"] for m in matched_boundaries}
        unmatched_calls = [
            {
                "url": call[3],
                "method": call[2],
                "type": call[1],
                "module": call[5],
                "language": call[6],
                "line": call[4]
            }
            for call in calls
            if call[3] not in matched_urls
        ]

        # Unmatched endpoints (not called internally)
        matched_paths = {m["endpoint_path"] for m in matched_boundaries}
        unmatched_endpoints = [
            {
                "path": endpoint[3],
                "method": endpoint[2],
                "type": endpoint[1],
                "module": endpoint[5],
                "language": endpoint[6],
                "line": endpoint[4]
            }
            for endpoint in endpoints
            if endpoint[3] not in matched_paths
        ]

        conn.close()

        return {
            "repository": repo_name,
            "matched_boundaries": matched_boundaries,
            "unmatched_calls": unmatched_calls,
            "unmatched_endpoints": unmatched_endpoints,
            "summary": {
                "total_endpoints": len(endpoints),
                "total_calls": len(calls),
                "matched_count": len(matched_boundaries),
                "unmatched_calls_count": len(unmatched_calls),
                "unmatched_endpoints_count": len(unmatched_endpoints)
            }
        }

    except Exception as e:
        return {"error": str(e)}


def main():
    """Main entry point for data loader."""
    repo_name = sys.argv[1] if len(sys.argv) > 1 else None

    if not repo_name:
        db_manager = DatabaseManager()
        repos = db_manager.list_analyzed_repos()
        if repos:
            repo_name = repos[0]
        else:
            print(json.dumps({"error": "No repositories found"}))
            return

    data = get_api_boundaries(repo_name)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
