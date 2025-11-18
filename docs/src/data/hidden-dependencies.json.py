#!/usr/bin/env python3
"""Data loader: Hidden dependencies (temporal coupling without structural coupling).

Usage: python hidden-dependencies.json.py <repo_name> [min_temporal_coupling] [min_co_changes]
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from depanalysis.db_manager import DatabaseManager
from depanalysis.metrics import MetricsAnalyzer

def main():
    if len(sys.argv) < 2:
        print("Usage: python hidden-dependencies.json.py <repo_name> [min_temporal_coupling] [min_co_changes]", file=sys.stderr)
        sys.exit(1)

    repo_name = sys.argv[1]
    min_temporal_coupling = float(sys.argv[2]) if len(sys.argv) > 2 else 0.3
    min_co_changes = int(sys.argv[3]) if len(sys.argv) > 3 else 2

    db_manager = DatabaseManager()
    metrics = MetricsAnalyzer(db_manager)

    try:
        df = metrics.get_hidden_dependencies(
            repo_name,
            min_temporal_coupling=min_temporal_coupling,
            min_co_changes=min_co_changes
        )
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
