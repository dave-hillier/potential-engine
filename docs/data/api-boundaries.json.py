#!/usr/bin/env python3
"""
Data loader for API boundary analysis.

THIN DATA LOADER: Queries MetricsAnalyzer and exports JSON for Observable.
No business logic - just data retrieval and formatting.
"""
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from depanalysis.db_manager import DatabaseManager
from depanalysis.metrics import MetricsAnalyzer


def get_api_boundaries(repo_name: str) -> dict:
    """
    Get API boundary coupling data for a repository.

    Thin wrapper around MetricsAnalyzer - delegates all logic to metrics layer.
    """
    db_manager = DatabaseManager()

    if not db_manager.repo_exists(repo_name):
        return {"error": f"Repository '{repo_name}' not found"}

    try:
        # Delegate to metrics layer - NO business logic here
        metrics = MetricsAnalyzer(db_manager)
        result = metrics.get_api_boundary_matches(repo_name)

        # Add repository name for context
        result["repository"] = repo_name

        return result

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
