#!/usr/bin/env python3
"""Data loader: Module centrality metrics for a repository.

Usage: python centrality.json.py <repo_name>
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from depanalysis.db_manager import DatabaseManager
from depanalysis.advanced_analytics import ArchitecturalPatternDetector

def main():
    if len(sys.argv) < 2:
        print("Usage: python centrality.json.py <repo_name>", file=sys.stderr)
        sys.exit(1)

    repo_name = sys.argv[1]
    db_manager = DatabaseManager()
    detector = ArchitecturalPatternDetector(db_manager)

    try:
        centrality = detector.calculate_centrality_metrics(repo_name)
        data = centrality.to_dict('records') if len(centrality) > 0 else []
        print(json.dumps(data, indent=2))
    except FileNotFoundError:
        print(f"Error: Repository '{repo_name}' not found", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
