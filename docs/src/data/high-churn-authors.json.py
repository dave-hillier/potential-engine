#!/usr/bin/env python3
"""Data loader: Author metrics for high-churn repository."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from depanalysis.db_manager import DatabaseManager
from depanalysis.metrics import MetricsAnalyzer

def main():
    repo_name = "high-churn"
    # Point to data directory in repo root (not docs/)
    data_dir = Path(__file__).parent.parent.parent.parent / "data"
    db_manager = DatabaseManager(data_dir=data_dir)
    metrics = MetricsAnalyzer(db_manager)

    try:
        df = metrics.get_author_stats(repo_name)
        data = df.to_dict(orient="records")
        print(json.dumps(data, indent=2))
    except FileNotFoundError:
        print(json.dumps({"error": f"Repository '{repo_name}' not found"}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
