#!/usr/bin/env python3
"""Data loader: Hotspot analysis combining complexity, churn, and coupling.

Usage: python hotspots.json.py <repo_name> [min_complexity] [min_churn]
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from depanalysis.db_manager import DatabaseManager
from depanalysis.metrics import MetricsAnalyzer

def main():
    if len(sys.argv) < 2:
        print("Usage: python hotspots.json.py <repo_name> [min_complexity] [min_churn]", file=sys.stderr)
        sys.exit(1)

    repo_name = sys.argv[1]
    min_complexity = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    min_churn = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    # Point to data directory in repo root (not docs/)
    data_dir = Path(__file__).parent.parent.parent.parent / "data"
    db_manager = DatabaseManager(data_dir=data_dir)
    metrics = MetricsAnalyzer(db_manager)

    try:
        df = metrics.get_hotspots(repo_name, min_complexity=min_complexity, min_churn=min_churn)
        data = df.to_dict(orient="records")
        print(json.dumps(data, indent=2))
    except FileNotFoundError:
        print(f"Error: Repository '{repo_name}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        # Return empty array on error
        print(json.dumps([]))

if __name__ == "__main__":
    main()
