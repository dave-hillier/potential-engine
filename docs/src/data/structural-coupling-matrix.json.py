#!/usr/bin/env python3
"""Data loader: Structural coupling matrix for a specific repository.

Builds a dependency matrix from imports in structure.db.
Returns hierarchical data grouped by directory.

Usage: python structural-coupling-matrix.json.py <repo_name>
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from depanalysis.db_manager import DatabaseManager


def get_directory_path(file_path: str, depth: int = 1) -> str:
    """Get directory path at specified depth."""
    parts = Path(file_path).parts
    if len(parts) <= depth:
        return "/".join(parts[:-1]) if len(parts) > 1 else "."
    return "/".join(parts[:depth])


def build_structural_matrix(repo_name: str):
    """Build structural dependency matrix from imports."""
    db_manager = DatabaseManager()

    try:
        conn = db_manager.get_connection(repo_name, "structure")
    except FileNotFoundError:
        print(f"Error: Structure database for '{repo_name}' not found", file=sys.stderr)
        sys.exit(1)

    cursor = conn.cursor()

    # Get all modules
    modules_query = """
        SELECT id, path, name
        FROM modules
        ORDER BY path
    """
    modules = cursor.execute(modules_query).fetchall()

    if not modules:
        conn.close()
        return {
            "files": [],
            "matrix": [],
            "directories": {}
        }

    # Build module lookup
    module_by_id = {m[0]: {"id": m[0], "path": m[1], "name": m[2]} for m in modules}
    module_by_path = {m[1]: m[0] for m in modules}
    module_by_name = {m[2]: m[0] for m in modules}

    # Get all imports with resolved targets
    imports_query = """
        SELECT
            i.from_module_id,
            i.to_module,
            COUNT(*) as import_count
        FROM imports i
        GROUP BY i.from_module_id, i.to_module
    """
    imports = cursor.execute(imports_query).fetchall()

    # Build dependency matrix
    dependencies = defaultdict(lambda: defaultdict(int))

    for from_id, to_module, count in imports:
        # Try to resolve to_module to an actual module ID
        to_id = None

        # Try exact path match first
        if to_module in module_by_path:
            to_id = module_by_path[to_module]
        # Try name match
        elif to_module in module_by_name:
            to_id = module_by_name[to_module]
        # Try fuzzy match (ends with)
        else:
            for path, mid in module_by_path.items():
                if path.endswith(to_module) or path.endswith(f"{to_module}.py"):
                    to_id = mid
                    break

        if to_id and to_id in module_by_id:
            dependencies[from_id][to_id] += count

    # Group files by directory (top-level)
    dir_groups = defaultdict(list)
    for module_id, module in module_by_id.items():
        dir_path = get_directory_path(module["path"], depth=1)
        dir_groups[dir_path].append(module_id)

    # Sort directories and files within them
    sorted_dirs = sorted(dir_groups.keys())

    # Build ordered list of files
    ordered_files = []
    dir_ranges = {}

    for dir_name in sorted_dirs:
        start_idx = len(ordered_files)

        # Sort files within directory alphabetically
        module_ids = sorted(dir_groups[dir_name], key=lambda mid: module_by_id[mid]["path"])

        for module_id in module_ids:
            ordered_files.append({
                "id": module_id,
                "path": module_by_id[module_id]["path"],
                "name": module_by_id[module_id]["name"],
                "directory": dir_name
            })

        end_idx = len(ordered_files)
        dir_ranges[dir_name] = {"start": start_idx, "end": end_idx, "count": end_idx - start_idx}

    # Build matrix (ordered by file index)
    matrix = []
    for i, source_file in enumerate(ordered_files):
        row = []
        for j, target_file in enumerate(ordered_files):
            count = dependencies[source_file["id"]].get(target_file["id"], 0)
            if count > 0:
                row.append({"col": j, "value": count})
        if row:  # Only include rows with dependencies
            matrix.append({"row": i, "cells": row})

    conn.close()

    return {
        "files": ordered_files,
        "matrix": matrix,
        "directories": dir_ranges
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python structural-coupling-matrix.json.py <repo_name>", file=sys.stderr)
        sys.exit(1)

    repo_name = sys.argv[1]
    data = build_structural_matrix(repo_name)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
