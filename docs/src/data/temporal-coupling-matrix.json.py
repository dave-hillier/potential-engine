#!/usr/bin/env python3
"""Data loader: Temporal coupling matrix for a specific repository.

Builds a coupling matrix from temporal_coupling table in history.db.
Returns hierarchical data grouped by directory.

Usage: python temporal-coupling-matrix.json.py <repo_name>
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


def build_temporal_matrix(repo_name: str, min_similarity: float = 0.1):
    """Build temporal coupling matrix from history.db."""
    db_manager = DatabaseManager()

    try:
        conn = db_manager.get_connection(repo_name, "history")
    except FileNotFoundError:
        print(f"Error: History database for '{repo_name}' not found", file=sys.stderr)
        sys.exit(1)

    cursor = conn.cursor()

    # Get all files that have been changed
    files_query = """
        SELECT DISTINCT file_path
        FROM file_changes
        WHERE change_type != 'D'
        ORDER BY file_path
    """
    files = cursor.execute(files_query).fetchall()

    if not files:
        conn.close()
        return {
            "files": [],
            "matrix": [],
            "directories": {}
        }

    # Build file list with indices
    file_paths = [f[0] for f in files]
    file_index = {path: idx for idx, path in enumerate(file_paths)}

    # Get temporal coupling data
    coupling_query = """
        SELECT
            file_a,
            file_b,
            jaccard_similarity,
            co_change_count
        FROM temporal_coupling
        WHERE jaccard_similarity >= ?
        ORDER BY jaccard_similarity DESC
    """
    couplings = cursor.execute(coupling_query, (min_similarity,)).fetchall()

    # Build coupling matrix (symmetric)
    coupling_matrix = defaultdict(lambda: defaultdict(float))

    for file_a, file_b, similarity, co_changes in couplings:
        if file_a in file_index and file_b in file_index:
            coupling_matrix[file_a][file_b] = similarity
            coupling_matrix[file_b][file_a] = similarity  # Symmetric

    # Group files by directory (top-level)
    dir_groups = defaultdict(list)
    for file_path in file_paths:
        dir_path = get_directory_path(file_path, depth=1)
        dir_groups[dir_path].append(file_path)

    # Sort directories
    sorted_dirs = sorted(dir_groups.keys())

    # Build ordered list of files grouped by directory
    ordered_files = []
    dir_ranges = {}

    for dir_name in sorted_dirs:
        start_idx = len(ordered_files)

        # Sort files within directory alphabetically
        dir_files = sorted(dir_groups[dir_name])

        for file_path in dir_files:
            ordered_files.append({
                "path": file_path,
                "directory": dir_name
            })

        end_idx = len(ordered_files)
        dir_ranges[dir_name] = {"start": start_idx, "end": end_idx, "count": end_idx - start_idx}

    # Build matrix in ordered form
    matrix = []
    for i, source_file in enumerate(ordered_files):
        row = []
        source_path = source_file["path"]

        for j, target_file in enumerate(ordered_files):
            if i == j:
                continue  # Skip diagonal
            target_path = target_file["path"]
            similarity = coupling_matrix[source_path].get(target_path, 0.0)

            if similarity > 0:
                row.append({"col": j, "value": similarity})

        if row:  # Only include rows with coupling
            matrix.append({"row": i, "cells": row})

    conn.close()

    return {
        "files": ordered_files,
        "matrix": matrix,
        "directories": dir_ranges
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python temporal-coupling-matrix.json.py <repo_name>", file=sys.stderr)
        sys.exit(1)

    repo_name = sys.argv[1]
    data = build_temporal_matrix(repo_name)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
