#!/usr/bin/env python3
"""Data loader: List all analyzed repositories."""

import sys
import json
from pathlib import Path

# Add parent directory to path to import depanalysis
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from depanalysis.db_manager import DatabaseManager

def main():
    # Point to data directory in repo root (not docs/)
    data_dir = Path(__file__).parent.parent.parent.parent / "data"
    db_manager = DatabaseManager(data_dir=data_dir)
    repos = db_manager.list_analyzed_repos()

    # Output JSON
    print(json.dumps(repos, indent=2))

if __name__ == "__main__":
    main()
