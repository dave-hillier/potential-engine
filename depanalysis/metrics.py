"""
Metrics and analysis queries for depanalysis.

Provides Python API for querying structure.db and history.db,
including single-repo and cross-repo analysis capabilities.
"""
import sqlite3
from pathlib import Path
from typing import Optional, List, Set, Tuple, Dict
import pandas as pd

from depanalysis.db_manager import DatabaseManager


class MetricsAnalyzer:
    """Query and analyze metrics from depanalysis databases."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize metrics analyzer.

        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager

    def get_churn_metrics(self, repo_name: str) -> pd.DataFrame:
        """
        Get file churn metrics for a repository.

        Args:
            repo_name: Name of the repository

        Returns:
            DataFrame with churn metrics per file
        """
        conn = self.db_manager.get_connection(repo_name, "history")
        df = pd.read_sql_query("SELECT * FROM churn_metrics ORDER BY total_churn DESC", conn)
        conn.close()
        return df

    def get_temporal_coupling(
        self, repo_name: str, min_co_changes: int = 2, min_similarity: float = 0.0
    ) -> pd.DataFrame:
        """
        Get temporal coupling metrics for a repository.

        Args:
            repo_name: Name of the repository
            min_co_changes: Minimum co-change count threshold
            min_similarity: Minimum Jaccard similarity threshold

        Returns:
            DataFrame with temporal coupling data
        """
        conn = self.db_manager.get_connection(repo_name, "history")
        query = """
            SELECT * FROM temporal_coupling
            WHERE co_change_count >= ? AND jaccard_similarity >= ?
            ORDER BY jaccard_similarity DESC, co_change_count DESC
        """
        df = pd.read_sql_query(query, conn, params=(min_co_changes, min_similarity))
        conn.close()
        return df

    def get_author_stats(self, repo_name: str) -> pd.DataFrame:
        """
        Get author statistics for a repository.

        Args:
            repo_name: Name of the repository

        Returns:
            DataFrame with author statistics
        """
        conn = self.db_manager.get_connection(repo_name, "history")
        df = pd.read_sql_query(
            "SELECT * FROM author_stats ORDER BY total_commits DESC", conn
        )
        conn.close()
        return df

    def get_author_ownership(self, repo_name: str, file_path: Optional[str] = None) -> pd.DataFrame:
        """
        Get author ownership data for a repository.

        Args:
            repo_name: Name of the repository
            file_path: Optional file path to filter by

        Returns:
            DataFrame with author ownership data
        """
        conn = self.db_manager.get_connection(repo_name, "history")

        if file_path:
            query = """
                SELECT ao.*, a.name, a.email
                FROM author_ownership ao
                JOIN authors a ON ao.author_id = a.id
                WHERE ao.file_path = ?
                ORDER BY ao.commit_count DESC
            """
            df = pd.read_sql_query(query, conn, params=(file_path,))
        else:
            query = """
                SELECT ao.*, a.name, a.email
                FROM author_ownership ao
                JOIN authors a ON ao.author_id = a.id
                ORDER BY ao.commit_count DESC
            """
            df = pd.read_sql_query(query, conn)

        conn.close()
        return df

    def get_code_age(self, repo_name: str) -> pd.DataFrame:
        """
        Get code age metrics for a repository.

        Args:
            repo_name: Name of the repository

        Returns:
            DataFrame with code age data
        """
        conn = self.db_manager.get_connection(repo_name, "history")
        df = pd.read_sql_query(
            "SELECT * FROM code_age ORDER BY days_since_last_change DESC", conn
        )
        conn.close()
        return df

    def get_high_temporal_coupling(self, repo_name: str) -> pd.DataFrame:
        """
        Get high temporal coupling pairs (co_change >= 3, similarity >= 0.3).

        Args:
            repo_name: Name of the repository

        Returns:
            DataFrame with high temporal coupling data
        """
        conn = self.db_manager.get_connection(repo_name, "history")
        df = pd.read_sql_query("SELECT * FROM high_temporal_coupling", conn)
        conn.close()
        return df

    def compare_author_stats_across_repos(self, repo_names: list[str]) -> pd.DataFrame:
        """
        Compare author statistics across multiple repositories.

        Args:
            repo_names: List of repository names

        Returns:
            DataFrame with combined author stats from all repos
        """
        all_stats = []

        for repo_name in repo_names:
            try:
                df = self.get_author_stats(repo_name)
                df["repository"] = repo_name
                all_stats.append(df)
            except FileNotFoundError:
                continue

        if not all_stats:
            return pd.DataFrame()

        return pd.concat(all_stats, ignore_index=True)

    def compare_churn_across_repos(self, repo_names: list[str]) -> pd.DataFrame:
        """
        Compare churn metrics across multiple repositories.

        Args:
            repo_names: List of repository names

        Returns:
            DataFrame with combined churn metrics from all repos
        """
        all_churn = []

        for repo_name in repo_names:
            try:
                df = self.get_churn_metrics(repo_name)
                df["repository"] = repo_name
                all_churn.append(df)
            except FileNotFoundError:
                continue

        if not all_churn:
            return pd.DataFrame()

        return pd.concat(all_churn, ignore_index=True)

    def export_to_csv(self, df: pd.DataFrame, output_path: Path) -> None:
        """
        Export DataFrame to CSV file.

        Args:
            df: DataFrame to export
            output_path: Path to output CSV file
        """
        df.to_csv(output_path, index=False)

    def export_to_json(self, df: pd.DataFrame, output_path: Path) -> None:
        """
        Export DataFrame to JSON file.

        Args:
            df: DataFrame to export
            output_path: Path to output JSON file
        """
        df.to_json(output_path, orient="records", indent=2)

    def get_summary_stats(self, repo_name: str) -> dict:
        """
        Get summary statistics for a repository.

        Args:
            repo_name: Name of the repository

        Returns:
            Dictionary with summary statistics
        """
        conn = self.db_manager.get_connection(repo_name, "history")
        cursor = conn.cursor()

        stats = {}
        stats["total_commits"] = cursor.execute("SELECT COUNT(*) FROM commits").fetchone()[0]
        stats["total_authors"] = cursor.execute("SELECT COUNT(*) FROM authors").fetchone()[0]
        stats["files_tracked"] = cursor.execute(
            "SELECT COUNT(DISTINCT file_path) FROM file_changes WHERE change_type != 'D'"
        ).fetchone()[0]
        stats["temporal_couplings"] = cursor.execute(
            "SELECT COUNT(*) FROM temporal_coupling"
        ).fetchone()[0]

        # Get date range
        date_range = cursor.execute(
            "SELECT MIN(timestamp), MAX(timestamp) FROM commits"
        ).fetchone()
        stats["first_commit"] = date_range[0]
        stats["last_commit"] = date_range[1]

        conn.close()
        return stats

    # =========================================================================
    # Structural Metrics (from structure.db)
    # =========================================================================

    def get_module_complexity(self, repo_name: str) -> pd.DataFrame:
        """
        Get module complexity metrics for a repository.

        Args:
            repo_name: Name of the repository

        Returns:
            DataFrame with module complexity metrics
        """
        conn = self.db_manager.get_connection(repo_name, "structure")
        df = pd.read_sql_query(
            "SELECT * FROM module_complexity ORDER BY total_complexity DESC", conn
        )
        conn.close()
        return df

    def get_instability_metrics(self, repo_name: str) -> pd.DataFrame:
        """
        Get instability metrics (Ce / (Ca + Ce)) for all modules.

        Args:
            repo_name: Name of the repository

        Returns:
            DataFrame with instability metrics
        """
        conn = self.db_manager.get_connection(repo_name, "structure")
        df = pd.read_sql_query(
            "SELECT * FROM instability ORDER BY instability DESC", conn
        )
        conn.close()
        return df

    def detect_circular_dependencies(self, repo_name: str) -> List[List[str]]:
        """
        Detect circular dependencies between modules using Tarjan's algorithm.

        Args:
            repo_name: Name of the repository

        Returns:
            List of cycles, where each cycle is a list of module paths
        """
        conn = self.db_manager.get_connection(repo_name, "structure")
        cursor = conn.cursor()

        # Build dependency graph from imports
        graph: Dict[str, Set[str]] = {}

        # Get all modules
        modules = cursor.execute("SELECT path FROM modules").fetchall()
        for (module_path,) in modules:
            graph[module_path] = set()

        # Get all imports and build edges
        imports = cursor.execute("""
            SELECT m1.path, i.to_module
            FROM imports i
            JOIN modules m1 ON i.from_module_id = m1.id
        """).fetchall()

        for from_module, to_module in imports:
            # Try to match to_module with actual module paths
            # Handle both module names and paths
            matched = False
            for (module_path,) in modules:
                # Check if to_module matches the module name or path
                module_name = Path(module_path).stem
                if to_module == module_name or to_module == module_path:
                    graph[from_module].add(module_path)
                    matched = True
                    break
                # Also check without .py extension
                if to_module.endswith('.py'):
                    if to_module == module_path:
                        graph[from_module].add(module_path)
                        matched = True
                        break

        conn.close()

        # Find strongly connected components (cycles) using Tarjan's algorithm
        cycles = self._find_cycles_tarjan(graph)

        # Filter out single-node "cycles" (not actual cycles)
        return [cycle for cycle in cycles if len(cycle) > 1]

    def _find_cycles_tarjan(self, graph: Dict[str, Set[str]]) -> List[List[str]]:
        """
        Find strongly connected components using Tarjan's algorithm.

        Args:
            graph: Adjacency list representation of the graph

        Returns:
            List of strongly connected components (each is a list of nodes)
        """
        index_counter = [0]
        stack = []
        lowlink = {}
        index = {}
        on_stack = {}
        sccs = []

        def strongconnect(node: str):
            index[node] = index_counter[0]
            lowlink[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)
            on_stack[node] = True

            # Consider successors
            if node in graph:
                for successor in graph[node]:
                    if successor not in index:
                        # Successor has not yet been visited
                        strongconnect(successor)
                        lowlink[node] = min(lowlink[node], lowlink[successor])
                    elif on_stack.get(successor, False):
                        # Successor is in stack and hence in the current SCC
                        lowlink[node] = min(lowlink[node], index[successor])

            # If node is a root node, pop the stack and generate an SCC
            if lowlink[node] == index[node]:
                scc = []
                while True:
                    successor = stack.pop()
                    on_stack[successor] = False
                    scc.append(successor)
                    if successor == node:
                        break
                sccs.append(scc)

        for node in graph:
            if node not in index:
                strongconnect(node)

        return sccs

    def get_circular_dependencies_with_metadata(self, repo_name: str) -> pd.DataFrame:
        """
        Get circular dependencies with additional metadata.

        Args:
            repo_name: Name of the repository

        Returns:
            DataFrame with cycle information including length and files involved
        """
        cycles = self.detect_circular_dependencies(repo_name)

        if not cycles:
            return pd.DataFrame(columns=["cycle_id", "cycle_length", "files"])

        rows = []
        for i, cycle in enumerate(cycles):
            rows.append({
                "cycle_id": i,
                "cycle_length": len(cycle),
                "files": " -> ".join(cycle + [cycle[0]])  # Close the cycle
            })

        return pd.DataFrame(rows)

    # =========================================================================
    # Combined Metrics (structure.db + history.db)
    # =========================================================================

    def get_hotspots(
        self,
        repo_name: str,
        min_complexity: int = 5,
        min_churn: int = 3,
        min_coupling: float = 0.3
    ) -> pd.DataFrame:
        """
        Identify hotspots by combining complexity, churn, and coupling metrics.

        Hotspots are files that are:
        - Structurally complex (high cyclomatic complexity)
        - Frequently changed (high churn)
        - Highly coupled to other files

        Args:
            repo_name: Name of the repository
            min_complexity: Minimum complexity threshold
            min_churn: Minimum churn threshold
            min_coupling: Minimum coupling threshold

        Returns:
            DataFrame with hotspot metrics
        """
        structure_conn = self.db_manager.get_connection(repo_name, "structure")
        history_conn = self.db_manager.get_connection(repo_name, "history")

        # Get structural metrics
        query = """
            SELECT
                mc.module_path AS file_path,
                mc.total_complexity,
                mc.function_count,
                mc.avg_complexity,
                i.ce AS efferent_coupling,
                i.ca AS afferent_coupling,
                i.instability
            FROM module_complexity mc
            JOIN instability i ON mc.module_id = i.module_id
            WHERE mc.total_complexity >= ?
        """

        structure_df = pd.read_sql_query(query, structure_conn, params=(min_complexity,))
        structure_conn.close()

        if structure_df.empty:
            return pd.DataFrame()

        # Get churn metrics
        churn_df = pd.read_sql_query(
            "SELECT file_path, total_churn, change_count FROM churn_metrics WHERE total_churn >= ?",
            history_conn,
            params=(min_churn,)
        )
        history_conn.close()

        # Merge structural and temporal metrics
        hotspots = pd.merge(structure_df, churn_df, on="file_path", how="inner")

        if hotspots.empty:
            return hotspots

        # Calculate hotspot score: complexity * churn * (coupling + 1)
        hotspots["hotspot_score"] = (
            hotspots["total_complexity"] *
            hotspots["total_churn"] *
            (hotspots["efferent_coupling"] + hotspots["afferent_coupling"] + 1)
        )

        return hotspots.sort_values("hotspot_score", ascending=False)

    def get_hidden_dependencies(
        self,
        repo_name: str,
        min_temporal_coupling: float = 0.3,
        min_co_changes: int = 2
    ) -> pd.DataFrame:
        """
        Identify hidden dependencies: files with high temporal coupling but no structural coupling.

        These represent files that change together frequently but don't import each other,
        suggesting missing abstractions or feature entanglement.

        Args:
            repo_name: Name of the repository
            min_temporal_coupling: Minimum Jaccard similarity threshold
            min_co_changes: Minimum co-change count threshold

        Returns:
            DataFrame with hidden dependency pairs
        """
        structure_conn = self.db_manager.get_connection(repo_name, "structure")
        history_conn = self.db_manager.get_connection(repo_name, "history")

        # Get temporal coupling
        temporal_query = """
            SELECT file1, file2, jaccard_similarity, co_change_count
            FROM temporal_coupling
            WHERE jaccard_similarity >= ? AND co_change_count >= ?
        """
        temporal_df = pd.read_sql_query(
            temporal_query,
            history_conn,
            params=(min_temporal_coupling, min_co_changes)
        )
        history_conn.close()

        if temporal_df.empty:
            return temporal_df

        # Get structural coupling (imports)
        imports_query = """
            SELECT
                m1.path AS file1,
                m2.path AS file2
            FROM imports i
            JOIN modules m1 ON i.from_module_id = m1.id
            JOIN modules m2 ON i.to_module = m2.name OR i.to_module = m2.path
        """
        imports_df = pd.read_sql_query(imports_query, structure_conn)

        # Also check reverse direction
        imports_reverse = imports_df.rename(columns={"file1": "file2", "file2": "file1"})
        all_imports = pd.concat([imports_df, imports_reverse], ignore_index=True)

        structure_conn.close()

        # Mark pairs with structural coupling
        temporal_df["has_import"] = temporal_df.apply(
            lambda row: any(
                (all_imports["file1"] == row["file1"]) & (all_imports["file2"] == row["file2"])
            ),
            axis=1
        )

        # Filter to only pairs without structural coupling
        hidden = temporal_df[~temporal_df["has_import"]].drop(columns=["has_import"])

        return hidden.sort_values("jaccard_similarity", ascending=False)
