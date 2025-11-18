#!/usr/bin/env python3
"""Data loader: Developer productivity insights for a repository.

Usage: python productivity.json.py <repo_name>
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from depanalysis.db_manager import DatabaseManager
from depanalysis.advanced_analytics import DeveloperProductivityAnalyzer

def main():
    if len(sys.argv) < 2:
        print("Usage: python productivity.json.py <repo_name>", file=sys.stderr)
        sys.exit(1)

    repo_name = sys.argv[1]
    db_manager = DatabaseManager()
    analyzer = DeveloperProductivityAnalyzer(db_manager)

    try:
        # Get all productivity metrics
        onboarding = analyzer.get_onboarding_metrics(repo_name)
        collaboration = analyzer.get_collaboration_patterns(repo_name)
        cognitive_load = analyzer.get_cognitive_load_metrics(repo_name)
        ownership = analyzer.get_code_ownership_evolution(repo_name)

        data = {
            "onboarding": onboarding.to_dict('records') if len(onboarding) > 0 else [],
            "collaboration": collaboration,
            "cognitive_load": cognitive_load.to_dict('records') if len(cognitive_load) > 0 else [],
            "ownership_evolution": ownership
        }

        print(json.dumps(data, indent=2))
    except FileNotFoundError:
        print(f"Error: Repository '{repo_name}' not found", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
