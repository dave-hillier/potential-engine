#!/usr/bin/env python3
"""Data loader: Temporal coupling for a specific repository.

Usage: python coupling.json.py <repo_name>
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from depanalysis.db_manager import DatabaseManager
from depanalysis.metrics import MetricsAnalyzer

def main():
    if len(sys.argv) < 2:
        print("Usage: python coupling.json.py <repo_name>", file=sys.stderr)
        sys.exit(1)

    repo_name = sys.argv[1]
    # Point to data directory in repo root (not docs/)
    data_dir = Path(__file__).parent.parent.parent.parent / "data"
    db_manager = DatabaseManager(data_dir=data_dir)
    metrics = MetricsAnalyzer(db_manager)

    try:
        df = metrics.get_temporal_coupling(repo_name, min_co_changes=1)
        data = df.to_dict(orient="records")
        print(json.dumps(data, indent=2))
    except FileNotFoundError:
        print(f"Error: Repository '{repo_name}' not found", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
