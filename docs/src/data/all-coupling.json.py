#!/usr/bin/env python3
"""Data loader: Temporal coupling for all repositories.

Returns coupling data for all repositories with repo_name field.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from depanalysis.db_manager import DatabaseManager
from depanalysis.metrics import MetricsAnalyzer

def main():
    # Point to data directory in repo root (not docs/)
    data_dir = Path(__file__).parent.parent.parent.parent / "data"
    db_manager = DatabaseManager(data_dir=data_dir)
    metrics = MetricsAnalyzer(db_manager)

    all_coupling = []

    # Get all repositories
    repos = db_manager.list_analyzed_repos()

    for repo_name in repos:
        try:
            df = metrics.get_temporal_coupling(repo_name, min_co_changes=1)
            # Add repo_name to each row
            for _, row in df.iterrows():
                all_coupling.append({
                    "repo_name": repo_name,
                    "file_a": row["file_a"],
                    "file_b": row["file_b"],
                    "co_change_count": int(row["co_change_count"]),
                    "jaccard_similarity": float(row["jaccard_similarity"])
                })
        except FileNotFoundError:
            continue

    print(json.dumps(all_coupling, indent=2))

if __name__ == "__main__":
    main()
