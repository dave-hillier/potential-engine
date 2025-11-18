#!/usr/bin/env python3
"""Data loader: Summary statistics for all repositories."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from depanalysis.db_manager import DatabaseManager
from depanalysis.metrics import MetricsAnalyzer

def main():
    db_manager = DatabaseManager()
    metrics = MetricsAnalyzer(db_manager)
    repos = db_manager.list_analyzed_repos()

    summaries = []
    for repo in repos:
        try:
            summary = metrics.get_summary_stats(repo)
            summary["name"] = repo
            summaries.append(summary)
        except Exception as e:
            print(f"Error getting summary for {repo}: {e}", file=sys.stderr)

    print(json.dumps(summaries, indent=2))

if __name__ == "__main__":
    main()
