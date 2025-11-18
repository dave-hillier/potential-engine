#!/usr/bin/env python3
"""Data loader: List all analyzed repositories."""

import sys
import json
from pathlib import Path

# Add parent directory to path to import depanalysis
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from depanalysis.db_manager import DatabaseManager

def main():
    db_manager = DatabaseManager()
    repos = db_manager.list_analyzed_repos()

    # Output JSON
    print(json.dumps(repos, indent=2))

if __name__ == "__main__":
    main()
