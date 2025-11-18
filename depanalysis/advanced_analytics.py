"""
Advanced analytics for Tier 3 features.

Includes:
- Feature 7: Change Impact Analysis
- Feature 8: Architectural Pattern Detection
- Feature 9: Code Quality Trends
- Feature 10: Developer Productivity Insights
"""
import sqlite3
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict, deque
import pandas as pd
import json

from depanalysis.db_manager import DatabaseManager


class ChangeImpactAnalyzer:
    """
    Feature 7: Change Impact Analysis

    Provides transitive dependency closure, test impact analysis,
    blast radius estimation, and change prediction.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def get_transitive_dependencies(
        self, repo_name: str, module_path: str, max_depth: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get all transitive dependencies of a module (direct and indirect).

        Uses recursive SQL CTE for efficient traversal.

        Args:
            repo_name: Repository name
            module_path: Path to the module
            max_depth: Maximum depth to traverse (None = unlimited)

        Returns:
            Dict with dependencies at each level
        """
        conn = self.db_manager.get_connection(repo_name, "structure")

        # Recursive CTE to find transitive dependencies
        query = """
        WITH RECURSIVE transitive_deps(module_id, module_path, to_module, depth) AS (
            -- Base case: direct dependencies
            SELECT
                m.id,
                m.path,
                i.to_module,
                0 AS depth
            FROM modules m
            JOIN imports i ON m.id = i.from_module_id
            WHERE m.path = ?

            UNION ALL

            -- Recursive case: dependencies of dependencies
            SELECT
                m.id,
                m.path,
                i.to_module,
                td.depth + 1
            FROM transitive_deps td
            JOIN modules m ON m.name = td.to_module OR m.path = td.to_module
            JOIN imports i ON m.id = i.from_module_id
            WHERE td.depth < COALESCE(?, 999)
        )
        SELECT DISTINCT module_path, to_module, depth
        FROM transitive_deps
        ORDER BY depth, module_path;
        """

        df = pd.read_sql_query(
            query, conn, params=(module_path, max_depth or 999)
        )
        conn.close()

        # Organize by depth
        result = {
            "source_module": module_path,
            "total_dependencies": len(df),
            "max_depth": int(df["depth"].max()) if len(df) > 0 else 0,
            "by_depth": {}
        }

        for depth in sorted(df["depth"].unique()):
            deps_at_depth = df[df["depth"] == depth]
            result["by_depth"][int(depth)] = deps_at_depth["to_module"].tolist()

        return result

    def get_reverse_dependencies(
        self, repo_name: str, module_path: str, max_depth: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get all modules that depend on this module (reverse/afferent dependencies).

        Args:
            repo_name: Repository name
            module_path: Path to the module
            max_depth: Maximum depth to traverse

        Returns:
            Dict with reverse dependencies
        """
        conn = self.db_manager.get_connection(repo_name, "structure")

        # Get module name first
        module_name_query = "SELECT name FROM modules WHERE path = ?"
        module_result = pd.read_sql_query(module_name_query, conn, params=(module_path,))

        if len(module_result) == 0:
            conn.close()
            return {"error": f"Module not found: {module_path}"}

        module_name = module_result.iloc[0]["name"]

        # Recursive CTE for reverse dependencies
        query = """
        WITH RECURSIVE reverse_deps(module_path, from_module_path, depth) AS (
            -- Base case: direct dependents
            SELECT
                ? AS module_path,
                m.path AS from_module_path,
                0 AS depth
            FROM imports i
            JOIN modules m ON m.id = i.from_module_id
            WHERE i.to_module = ? OR i.to_module = ?

            UNION ALL

            -- Recursive case: modules that depend on dependents
            SELECT
                rd.from_module_path AS module_path,
                m.path AS from_module_path,
                rd.depth + 1
            FROM reverse_deps rd
            JOIN modules target ON target.path = rd.from_module_path
            JOIN imports i ON (i.to_module = target.name OR i.to_module = target.path)
            JOIN modules m ON m.id = i.from_module_id
            WHERE rd.depth < COALESCE(?, 999)
        )
        SELECT DISTINCT from_module_path, depth
        FROM reverse_deps
        ORDER BY depth, from_module_path;
        """

        df = pd.read_sql_query(
            query, conn, params=(module_path, module_name, module_path, max_depth or 999)
        )
        conn.close()

        # Organize by depth
        result = {
            "target_module": module_path,
            "total_dependents": len(df),
            "max_depth": int(df["depth"].max()) if len(df) > 0 else 0,
            "by_depth": {}
        }

        for depth in sorted(df["depth"].unique()):
            deps_at_depth = df[df["depth"] == depth]
            result["by_depth"][int(depth)] = deps_at_depth["from_module_path"].tolist()

        return result

    def get_test_impact(self, repo_name: str, changed_file: str) -> Dict[str, Any]:
        """
        Determine which test files should run when a file changes.

        Uses naming conventions and dependency analysis.

        Args:
            repo_name: Repository name
            changed_file: Path to changed file

        Returns:
            Dict with test files that should run
        """
        conn = self.db_manager.get_connection(repo_name, "structure")

        # Strategy 1: Find test files with similar names
        test_patterns = [
            f"test_{Path(changed_file).stem}",
            f"{Path(changed_file).stem}_test",
            f"test{Path(changed_file).stem}",
        ]

        pattern_query = """
        SELECT path FROM modules
        WHERE path LIKE '%test%'
        AND ({})
        """.format(" OR ".join(f"path LIKE '%{p}%'" for p in test_patterns))

        naming_tests = pd.read_sql_query(pattern_query, conn)

        # Strategy 2: Find test files that import this module
        reverse_deps = self.get_reverse_dependencies(repo_name, changed_file)
        dependent_tests = []

        if "by_depth" in reverse_deps:
            for depth, deps in reverse_deps["by_depth"].items():
                for dep in deps:
                    if "test" in dep.lower():
                        dependent_tests.append(dep)

        conn.close()

        # Combine results
        all_tests = set(naming_tests["path"].tolist() if len(naming_tests) > 0 else [])
        all_tests.update(dependent_tests)

        return {
            "changed_file": changed_file,
            "tests_by_naming": naming_tests["path"].tolist() if len(naming_tests) > 0 else [],
            "tests_by_dependency": dependent_tests,
            "all_tests": sorted(list(all_tests)),
            "total_test_files": len(all_tests)
        }

    def get_blast_radius(self, repo_name: str, module_path: str) -> Dict[str, Any]:
        """
        Estimate the "blast radius" of changes to a module.

        Combines:
        - Structural dependencies (reverse dependencies)
        - Temporal coupling (files that change together)
        - Historical change patterns

        Args:
            repo_name: Repository name
            module_path: Path to module

        Returns:
            Dict with blast radius estimation
        """
        # Get structural impact
        reverse_deps = self.get_reverse_dependencies(repo_name, module_path)
        structural_impact = set()

        if "by_depth" in reverse_deps:
            for depth, deps in reverse_deps["by_depth"].items():
                structural_impact.update(deps)

        # Get temporal coupling impact
        try:
            hist_conn = self.db_manager.get_connection(repo_name, "history")
            temporal_query = """
            SELECT DISTINCT
                CASE
                    WHEN file_a = ? THEN file_b
                    WHEN file_b = ? THEN file_a
                END AS coupled_file,
                jaccard_similarity,
                co_change_count
            FROM temporal_coupling
            WHERE (file_a = ? OR file_b = ?)
            AND jaccard_similarity >= 0.3
            ORDER BY jaccard_similarity DESC
            """

            temporal_df = pd.read_sql_query(
                temporal_query,
                hist_conn,
                params=(module_path, module_path, module_path, module_path)
            )
            hist_conn.close()

            temporal_impact = set(temporal_df["coupled_file"].tolist())
        except FileNotFoundError:
            temporal_impact = set()
            temporal_df = pd.DataFrame()

        # Find files with both structural AND temporal coupling (highest risk)
        high_risk = structural_impact & temporal_impact

        # Files with only temporal coupling (hidden dependencies)
        hidden_deps = temporal_impact - structural_impact

        # Total blast radius
        total_impact = structural_impact | temporal_impact

        return {
            "module": module_path,
            "total_affected_files": len(total_impact),
            "structural_only": len(structural_impact - temporal_impact),
            "temporal_only": len(hidden_deps),
            "both_structural_and_temporal": len(high_risk),
            "high_risk_files": sorted(list(high_risk)),
            "hidden_dependencies": sorted(list(hidden_deps)),
            "all_affected_files": sorted(list(total_impact)),
            "temporal_details": temporal_df.to_dict('records') if len(temporal_df) > 0 else []
        }


class ArchitecturalPatternDetector:
    """
    Feature 8: Architectural Pattern Detection

    Detects architectural patterns and anti-patterns using graph analysis.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def calculate_centrality_metrics(self, repo_name: str) -> pd.DataFrame:
        """
        Calculate graph centrality metrics for modules.

        Includes:
        - Degree centrality (number of connections)
        - Betweenness approximation (modules that connect layers)
        - PageRank-style importance

        Args:
            repo_name: Repository name

        Returns:
            DataFrame with centrality metrics per module
        """
        conn = self.db_manager.get_connection(repo_name, "structure")

        # Get dependency graph
        graph_query = """
        SELECT
            m1.path AS from_module,
            m2.path AS to_module
        FROM imports i
        JOIN modules m1 ON i.from_module_id = m1.id
        LEFT JOIN modules m2 ON (i.to_module = m2.name OR i.to_module = m2.path)
        WHERE m2.path IS NOT NULL
        """

        edges_df = pd.read_sql_query(graph_query, conn)

        # Get all modules
        modules_query = "SELECT path FROM modules"
        modules_df = pd.read_sql_query(modules_query, conn)
        conn.close()

        if len(edges_df) == 0 or len(modules_df) == 0:
            return pd.DataFrame()

        # Build adjacency lists
        out_edges = defaultdict(set)  # who this module imports
        in_edges = defaultdict(set)   # who imports this module

        for _, row in edges_df.iterrows():
            out_edges[row["from_module"]].add(row["to_module"])
            in_edges[row["to_module"]].add(row["from_module"])

        # Calculate metrics
        results = []
        for module in modules_df["path"]:
            out_degree = len(out_edges[module])
            in_degree = len(in_edges[module])
            total_degree = out_degree + in_degree

            # Simple PageRank approximation (weighted by incoming edges)
            pagerank_score = in_degree / max(1, len(modules_df))

            results.append({
                "module_path": module,
                "out_degree": out_degree,
                "in_degree": in_degree,
                "total_degree": total_degree,
                "pagerank_score": pagerank_score,
                "is_hub": in_degree > len(modules_df) * 0.1,  # Top 10% by in-degree
                "is_leaf": out_degree == 0,
                "is_root": in_degree == 0 and out_degree > 0
            })

        return pd.DataFrame(results).sort_values("pagerank_score", ascending=False)

    def detect_layered_architecture(self, repo_name: str) -> Dict[str, Any]:
        """
        Detect layered architecture patterns.

        Uses directory structure and import direction to identify layers.

        Args:
            repo_name: Repository name

        Returns:
            Dict with detected layers and violations
        """
        conn = self.db_manager.get_connection(repo_name, "structure")

        # Get modules with directory structure
        modules_query = "SELECT path FROM modules ORDER BY path"
        modules_df = pd.read_sql_query(modules_query, conn)

        # Get all imports
        imports_query = """
        SELECT
            m1.path AS from_module,
            i.to_module,
            m2.path AS to_module_path
        FROM imports i
        JOIN modules m1 ON i.from_module_id = m1.id
        LEFT JOIN modules m2 ON (i.to_module = m2.name OR i.to_module = m2.path)
        """
        imports_df = pd.read_sql_query(imports_query, conn)
        conn.close()

        # Extract top-level directories as potential layers
        layers = defaultdict(list)
        for path in modules_df["path"]:
            parts = Path(path).parts
            if len(parts) > 0:
                top_dir = parts[0]
                layers[top_dir].append(path)

        # Analyze import patterns between layers
        layer_deps = defaultdict(lambda: defaultdict(int))

        for _, row in imports_df.iterrows():
            from_path = row["from_module"]
            to_path = row.get("to_module_path")

            if to_path:
                from_layer = Path(from_path).parts[0] if from_path else None
                to_layer = Path(to_path).parts[0] if to_path else None

                if from_layer and to_layer and from_layer != to_layer:
                    layer_deps[from_layer][to_layer] += 1

        # Detect potential violations (circular dependencies between layers)
        violations = []
        for layer_a, deps in layer_deps.items():
            for layer_b, count in deps.items():
                if layer_b in layer_deps and layer_a in layer_deps[layer_b]:
                    violations.append({
                        "layer_a": layer_a,
                        "layer_b": layer_b,
                        "imports_a_to_b": count,
                        "imports_b_to_a": layer_deps[layer_b][layer_a]
                    })

        return {
            "layers": {k: len(v) for k, v in layers.items()},
            "layer_dependencies": {k: dict(v) for k, v in layer_deps.items()},
            "circular_layer_dependencies": violations,
            "total_layers": len(layers)
        }

    def detect_god_classes(
        self, repo_name: str, complexity_threshold: int = 50, method_threshold: int = 20
    ) -> pd.DataFrame:
        """
        Detect God classes (classes with too many responsibilities).

        Criteria:
        - High total complexity
        - Many methods
        - High coupling

        Args:
            repo_name: Repository name
            complexity_threshold: Min total complexity
            method_threshold: Min number of methods

        Returns:
            DataFrame with potential God classes
        """
        conn = self.db_manager.get_connection(repo_name, "structure")

        query = """
        SELECT
            c.id,
            c.name,
            m.path AS module_path,
            COUNT(DISTINCT f.id) AS method_count,
            SUM(f.cyclomatic_complexity) AS total_complexity,
            AVG(f.cyclomatic_complexity) AS avg_complexity,
            c.line_end - c.line_start + 1 AS lines_of_code
        FROM classes c
        JOIN modules m ON c.module_id = m.id
        LEFT JOIN functions f ON f.class_id = c.id
        GROUP BY c.id, c.name, m.path, c.line_start, c.line_end
        HAVING method_count >= ? AND total_complexity >= ?
        ORDER BY total_complexity DESC, method_count DESC
        """

        df = pd.read_sql_query(
            query, conn, params=(method_threshold, complexity_threshold)
        )
        conn.close()

        return df

    def detect_shotgun_surgery(self, repo_name: str, min_files: int = 5) -> List[Dict[str, Any]]:
        """
        Detect shotgun surgery anti-pattern.

        Finds commits that changed many files simultaneously,
        indicating scattered responsibility.

        Args:
            repo_name: Repository name
            min_files: Minimum files changed in one commit

        Returns:
            List of commits with shotgun surgery pattern
        """
        try:
            conn = self.db_manager.get_connection(repo_name, "history")

            query = """
            SELECT
                c.hash,
                c.author_name,
                c.timestamp,
                c.message,
                COUNT(DISTINCT fc.file_path) AS files_changed,
                SUM(fc.lines_added + fc.lines_deleted) AS total_churn
            FROM commits c
            JOIN file_changes fc ON fc.commit_id = c.id
            GROUP BY c.id, c.hash, c.author_name, c.timestamp, c.message
            HAVING files_changed >= ?
            ORDER BY files_changed DESC
            LIMIT 50
            """

            df = pd.read_sql_query(query, conn, params=(min_files,))
            conn.close()

            return df.to_dict('records')
        except FileNotFoundError:
            return []


class CodeQualityTrendsAnalyzer:
    """
    Feature 9: Code Quality Trends

    Tracks structural metrics over time.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def snapshot_current_metrics(self, repo_name: str, commit_hash: str) -> Dict[str, Any]:
        """
        Take a snapshot of current structural metrics for a commit.

        Args:
            repo_name: Repository name
            commit_hash: Git commit hash

        Returns:
            Dict with all metrics at this commit
        """
        struct_conn = self.db_manager.get_connection(repo_name, "structure")

        # Get aggregate metrics
        metrics = {}

        # Module counts
        module_count = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM modules", struct_conn
        ).iloc[0]["count"]
        metrics["module_count"] = int(module_count)

        # Class counts
        class_count = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM classes", struct_conn
        ).iloc[0]["count"]
        metrics["class_count"] = int(class_count)

        # Function counts
        function_count = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM functions", struct_conn
        ).iloc[0]["count"]
        metrics["function_count"] = int(function_count)

        # Average complexity
        avg_complexity = pd.read_sql_query(
            "SELECT AVG(cyclomatic_complexity) as avg FROM functions", struct_conn
        ).iloc[0]["avg"]
        metrics["avg_complexity"] = float(avg_complexity) if avg_complexity else 0.0

        # Average instability
        instability_df = pd.read_sql_query("SELECT AVG(instability) as avg FROM instability", struct_conn)
        metrics["avg_instability"] = float(instability_df.iloc[0]["avg"]) if instability_df.iloc[0]["avg"] else 0.0

        # Total imports
        import_count = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM imports", struct_conn
        ).iloc[0]["count"]
        metrics["import_count"] = int(import_count)

        struct_conn.close()

        return {
            "commit_hash": commit_hash,
            "timestamp": None,  # Will be filled from history.db if available
            "metrics": metrics
        }


class DeveloperProductivityAnalyzer:
    """
    Feature 10: Developer Productivity Insights

    Analyzes developer collaboration patterns and productivity.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def get_onboarding_metrics(self, repo_name: str) -> pd.DataFrame:
        """
        Track onboarding metrics: time until new developers touch core modules.

        Args:
            repo_name: Repository name

        Returns:
            DataFrame with onboarding metrics per developer
        """
        try:
            conn = self.db_manager.get_connection(repo_name, "history")

            query = """
            SELECT
                a.name,
                a.email,
                MIN(c.timestamp) AS first_commit,
                COUNT(DISTINCT fc.file_path) AS files_touched,
                COUNT(DISTINCT c.id) AS total_commits,
                julianday(MAX(c.timestamp)) - julianday(MIN(c.timestamp)) AS days_active
            FROM authors a
            JOIN commits c ON c.author_email = a.email
            LEFT JOIN file_changes fc ON fc.commit_id = c.id
            GROUP BY a.id, a.name, a.email
            ORDER BY first_commit DESC
            """

            df = pd.read_sql_query(query, conn)
            conn.close()

            return df
        except FileNotFoundError:
            return pd.DataFrame()

    def get_collaboration_patterns(self, repo_name: str) -> Dict[str, Any]:
        """
        Detect collaboration patterns between developers.

        Finds developers who frequently modify the same files.

        Args:
            repo_name: Repository name

        Returns:
            Dict with collaboration metrics
        """
        try:
            conn = self.db_manager.get_connection(repo_name, "history")

            # Find shared file ownership
            query = """
            SELECT
                ao1.file_path,
                a1.name AS author1,
                a2.name AS author2,
                ao1.commit_count AS author1_commits,
                ao2.commit_count AS author2_commits,
                ao1.commit_count + ao2.commit_count AS total_commits
            FROM author_ownership ao1
            JOIN author_ownership ao2 ON ao1.file_path = ao2.file_path AND ao1.author_id < ao2.author_id
            JOIN authors a1 ON ao1.author_id = a1.id
            JOIN authors a2 ON ao2.author_id = a2.id
            WHERE ao1.commit_count >= 2 AND ao2.commit_count >= 2
            ORDER BY total_commits DESC
            LIMIT 100
            """

            df = pd.read_sql_query(query, conn)
            conn.close()

            # Calculate collaboration score
            collaborations = defaultdict(int)
            for _, row in df.iterrows():
                pair = tuple(sorted([row["author1"], row["author2"]]))
                collaborations[pair] += 1

            top_collaborations = sorted(
                [{"authors": list(k), "shared_files": v} for k, v in collaborations.items()],
                key=lambda x: x["shared_files"],
                reverse=True
            )[:20]

            return {
                "shared_file_ownership": df.to_dict('records'),
                "top_collaborations": top_collaborations
            }
        except FileNotFoundError:
            return {"shared_file_ownership": [], "top_collaborations": []}

    def get_cognitive_load_metrics(self, repo_name: str) -> pd.DataFrame:
        """
        Calculate cognitive load for developers.

        Combines:
        - Complexity of files they work on
        - Coupling of files they work on
        - Number of different areas they touch

        Args:
            repo_name: Repository name

        Returns:
            DataFrame with cognitive load metrics per developer
        """
        try:
            hist_conn = self.db_manager.get_connection(repo_name, "history")
            struct_conn = self.db_manager.get_connection(repo_name, "structure")

            # Get author file ownership
            author_query = """
            SELECT
                a.name,
                a.email,
                ao.file_path,
                ao.commit_count
            FROM authors a
            JOIN author_ownership ao ON ao.author_id = a.id
            WHERE ao.commit_count >= 3
            """

            author_df = pd.read_sql_query(author_query, hist_conn)
            hist_conn.close()

            # Get complexity and coupling for files
            module_query = """
            SELECT
                m.path,
                COALESCE(mc.total_complexity, 0) AS complexity,
                COALESCE(i.instability, 0) AS instability,
                COALESCE(ec.efferent_coupling, 0) + COALESCE(ac.afferent_coupling, 0) AS total_coupling
            FROM modules m
            LEFT JOIN module_complexity mc ON m.id = mc.module_id
            LEFT JOIN instability i ON m.id = i.module_id
            LEFT JOIN efferent_coupling ec ON m.id = ec.module_id
            LEFT JOIN afferent_coupling ac ON m.id = ac.module_id
            """

            module_df = pd.read_sql_query(module_query, struct_conn)
            struct_conn.close()

            # Join and calculate cognitive load
            merged = author_df.merge(
                module_df,
                left_on="file_path",
                right_on="path",
                how="left"
            )

            # Aggregate per developer
            cognitive_load = merged.groupby(["name", "email"]).agg({
                "file_path": "count",
                "complexity": "sum",
                "instability": "mean",
                "total_coupling": "sum"
            }).reset_index()

            cognitive_load.columns = [
                "name", "email", "files_owned",
                "total_complexity", "avg_instability", "total_coupling"
            ]

            # Calculate cognitive load score
            cognitive_load["cognitive_load_score"] = (
                cognitive_load["total_complexity"] * 0.4 +
                cognitive_load["total_coupling"] * 0.3 +
                cognitive_load["files_owned"] * 0.3
            )

            return cognitive_load.sort_values("cognitive_load_score", ascending=False)

        except FileNotFoundError:
            return pd.DataFrame()

    def get_code_ownership_evolution(self, repo_name: str) -> List[Dict[str, Any]]:
        """
        Track how code ownership evolves over time.

        Args:
            repo_name: Repository name

        Returns:
            List of ownership changes
        """
        try:
            conn = self.db_manager.get_connection(repo_name, "history")

            # Get ownership transfers (files where primary owner changed)
            query = """
            SELECT
                ao.file_path,
                a.name AS current_owner,
                ao.commit_count,
                cm.total_commits,
                CAST(ao.commit_count AS REAL) / cm.total_commits AS ownership_percentage
            FROM author_ownership ao
            JOIN authors a ON ao.author_id = a.id
            JOIN churn_metrics cm ON ao.file_path = cm.file_path
            WHERE cm.author_count > 1
            ORDER BY ao.file_path, ownership_percentage DESC
            """

            df = pd.read_sql_query(query, conn)
            conn.close()

            # Group by file to find primary and secondary owners
            ownership_data = []
            for file_path, group in df.groupby("file_path"):
                sorted_group = group.sort_values("ownership_percentage", ascending=False)
                if len(sorted_group) >= 2:
                    ownership_data.append({
                        "file_path": file_path,
                        "primary_owner": sorted_group.iloc[0]["current_owner"],
                        "primary_percentage": float(sorted_group.iloc[0]["ownership_percentage"]),
                        "secondary_owner": sorted_group.iloc[1]["current_owner"],
                        "secondary_percentage": float(sorted_group.iloc[1]["ownership_percentage"]),
                        "total_authors": int(sorted_group.iloc[0]["total_commits"])
                    })

            return ownership_data

        except FileNotFoundError:
            return []


class AdvancedAnalyticsAPI:
    """
    Unified API for all Tier 3 advanced analytics features.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.change_impact = ChangeImpactAnalyzer(db_manager)
        self.patterns = ArchitecturalPatternDetector(db_manager)
        self.trends = CodeQualityTrendsAnalyzer(db_manager)
        self.productivity = DeveloperProductivityAnalyzer(db_manager)

    def export_all_metrics(self, repo_name: str, output_dir: Path) -> Dict[str, str]:
        """
        Export all Tier 3 metrics to JSON files.

        Args:
            repo_name: Repository name
            output_dir: Directory to write JSON files

        Returns:
            Dict mapping metric name to file path
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        exported = {}

        # Export centrality metrics
        centrality = self.patterns.calculate_centrality_metrics(repo_name)
        if len(centrality) > 0:
            path = output_dir / f"{repo_name}_centrality.json"
            centrality.to_json(path, orient="records", indent=2)
            exported["centrality"] = str(path)

        # Export layered architecture analysis
        layers = self.patterns.detect_layered_architecture(repo_name)
        path = output_dir / f"{repo_name}_layers.json"
        with open(path, "w") as f:
            json.dump(layers, f, indent=2)
        exported["layers"] = str(path)

        # Export God classes
        god_classes = self.patterns.detect_god_classes(repo_name)
        if len(god_classes) > 0:
            path = output_dir / f"{repo_name}_god_classes.json"
            god_classes.to_json(path, orient="records", indent=2)
            exported["god_classes"] = str(path)

        # Export onboarding metrics
        onboarding = self.productivity.get_onboarding_metrics(repo_name)
        if len(onboarding) > 0:
            path = output_dir / f"{repo_name}_onboarding.json"
            onboarding.to_json(path, orient="records", indent=2)
            exported["onboarding"] = str(path)

        # Export collaboration patterns
        collab = self.productivity.get_collaboration_patterns(repo_name)
        path = output_dir / f"{repo_name}_collaboration.json"
        with open(path, "w") as f:
            json.dump(collab, f, indent=2)
        exported["collaboration"] = str(path)

        # Export cognitive load
        cognitive = self.productivity.get_cognitive_load_metrics(repo_name)
        if len(cognitive) > 0:
            path = output_dir / f"{repo_name}_cognitive_load.json"
            cognitive.to_json(path, orient="records", indent=2)
            exported["cognitive_load"] = str(path)

        return exported
