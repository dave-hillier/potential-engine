#!/usr/bin/env python3
"""Data loader: Change impact analysis for a specific module.

Usage: python impact.json.py <repo_name> <module_path>
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from depanalysis.db_manager import DatabaseManager
from depanalysis.advanced_analytics import ChangeImpactAnalyzer

def main():
    if len(sys.argv) < 3:
        print("Usage: python impact.json.py <repo_name> <module_path>", file=sys.stderr)
        sys.exit(1)

    repo_name = sys.argv[1]
    module_path = sys.argv[2]

    db_manager = DatabaseManager()
    analyzer = ChangeImpactAnalyzer(db_manager)

    try:
        blast_radius = analyzer.get_blast_radius(repo_name, module_path)
        print(json.dumps(blast_radius, indent=2))
    except FileNotFoundError:
        print(f"Error: Repository '{repo_name}' not found", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
