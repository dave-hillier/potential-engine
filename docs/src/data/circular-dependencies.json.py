#!/usr/bin/env python3
"""Data loader: Circular dependency detection.

Usage: python circular-dependencies.json.py <repo_name>
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from depanalysis.db_manager import DatabaseManager
from depanalysis.metrics import MetricsAnalyzer

def main():
    if len(sys.argv) < 2:
        print("Usage: python circular-dependencies.json.py <repo_name>", file=sys.stderr)
        sys.exit(1)

    repo_name = sys.argv[1]
    db_manager = DatabaseManager()
    metrics = MetricsAnalyzer(db_manager)

    try:
        df = metrics.get_circular_dependencies_with_metadata(repo_name)
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
