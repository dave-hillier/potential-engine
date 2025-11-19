#!/usr/bin/env python3
"""Data loader: API boundaries for all repositories."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from depanalysis.db_manager import DatabaseManager
from depanalysis.metrics import MetricsAnalyzer


def get_api_boundaries(repo_name: str, metrics: MetricsAnalyzer) -> dict:
    """Get API boundary coupling data for a repository."""
    try:
        result = metrics.get_api_boundary_matches(repo_name)
        result["repository"] = repo_name
        return result
    except Exception:
        return None


def main():
    data_dir = Path(__file__).parent.parent.parent.parent / "data"
    db_manager = DatabaseManager(data_dir=data_dir)
    metrics = MetricsAnalyzer(db_manager)

    all_data = {}
    repos = db_manager.list_analyzed_repos()

    for repo_name in repos:
        data = get_api_boundaries(repo_name, metrics)
        if data:
            all_data[repo_name] = data

    print(json.dumps(all_data, indent=2))


if __name__ == "__main__":
    main()
