"""
Diff Analysis for Pull Request Enrichment.

Compares architectural metrics between two Git refs (branches, commits, tags)
to show the impact of code changes on architecture quality.
"""
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from depanalysis.db_manager import DatabaseManager
from depanalysis.git_analyzer import GitAnalyzer
from depanalysis.structure_analyzer import StructureAnalyzer


@dataclass
class MetricDiff:
    """Represents the difference in a metric between two states."""

    metric_name: str
    before_value: float
    after_value: float
    absolute_change: float
    percent_change: Optional[float]
    impact: str  # 'improved', 'degraded', 'unchanged'

    @classmethod
    def calculate(cls, metric_name: str, before: float, after: float, threshold: float = 0.01):
        """
        Calculate metric difference.

        Args:
            metric_name: Name of the metric
            before: Value before changes
            after: Value after changes
            threshold: Minimum change to consider significant

        Returns:
            MetricDiff instance
        """
        absolute_change = after - before
        percent_change = ((after - before) / before * 100) if before != 0 else None

        # Determine impact (lower is usually better for coupling/complexity/churn)
        if abs(absolute_change) < threshold:
            impact = "unchanged"
        elif absolute_change < 0:
            impact = "improved"  # Decreased
        else:
            impact = "degraded"  # Increased

        return cls(
            metric_name=metric_name,
            before_value=before,
            after_value=after,
            absolute_change=absolute_change,
            percent_change=percent_change,
            impact=impact,
        )


@dataclass
class ArchitecturalDiff:
    """Complete architectural diff between two states."""

    base_ref: str
    head_ref: str
    files_changed: list[str]
    metrics: list[MetricDiff]
    new_violations: list[dict[str, Any]]
    resolved_violations: list[dict[str, Any]]
    summary: dict[str, Any]


class DiffAnalyzer:
    """Analyzes architectural differences between Git refs."""

    def __init__(self, repo_path: Path, db_manager: DatabaseManager):
        """
        Initialize diff analyzer.

        Args:
            repo_path: Path to Git repository
            db_manager: DatabaseManager instance
        """
        self.repo_path = repo_path
        self.db_manager = db_manager

    def analyze_diff(self, base_ref: str, head_ref: str = "HEAD") -> ArchitecturalDiff:
        """
        Analyze architectural diff between two Git refs.

        Args:
            base_ref: Base reference (e.g., 'main', commit SHA)
            head_ref: Head reference (default: 'HEAD')

        Returns:
            ArchitecturalDiff object with comparison results
        """
        # Get list of changed files
        files_changed = self._get_changed_files(base_ref, head_ref)

        # Create temporary databases for both refs
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Analyze base ref
            base_metrics = self._analyze_ref(base_ref, tmppath / "base")

            # Analyze head ref (current state)
            head_metrics = self._analyze_ref(head_ref, tmppath / "head")

        # Calculate metric diffs
        metric_diffs = self._calculate_metric_diffs(base_metrics, head_metrics)

        # Generate summary
        summary = self._generate_summary(files_changed, metric_diffs)

        return ArchitecturalDiff(
            base_ref=base_ref,
            head_ref=head_ref,
            files_changed=files_changed,
            metrics=metric_diffs,
            new_violations=[],  # Would be populated by rule validation
            resolved_violations=[],
            summary=summary,
        )

    def _get_changed_files(self, base_ref: str, head_ref: str) -> list[str]:
        """Get list of files changed between two refs."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", base_ref, head_ref],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return [f for f in result.stdout.strip().split("\n") if f]
        except subprocess.CalledProcessError:
            return []

    def _analyze_ref(self, ref: str, output_path: Path) -> dict[str, Any]:
        """
        Analyze a specific Git ref.

        Creates a temporary checkout and analyzes it.
        """
        output_path.mkdir(parents=True, exist_ok=True)

        # Create worktree for the ref
        worktree_path = output_path / "worktree"
        try:
            subprocess.run(
                ["git", "worktree", "add", "--detach", str(worktree_path), ref],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
            )

            # Create temporary database
            db_path = output_path / "temp.db"
            temp_conn = sqlite3.connect(db_path)

            # Initialize structure schema
            from depanalysis.db import get_structure_schema

            temp_conn.executescript(get_structure_schema())

            # Analyze structure
            struct_analyzer = StructureAnalyzer(worktree_path, temp_conn)
            stats = struct_analyzer.analyze()

            # Calculate metrics
            metrics = self._extract_metrics(temp_conn)

            temp_conn.close()

            return metrics

        finally:
            # Clean up worktree
            try:
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(worktree_path)],
                    cwd=self.repo_path,
                    capture_output=True,
                )
            except Exception:
                pass

    def _extract_metrics(self, conn: sqlite3.Connection) -> dict[str, Any]:
        """Extract key metrics from database."""
        cursor = conn.cursor()

        metrics = {}

        # Total counts
        metrics["total_modules"] = cursor.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
        metrics["total_classes"] = cursor.execute("SELECT COUNT(*) FROM classes").fetchone()[0]
        metrics["total_functions"] = cursor.execute("SELECT COUNT(*) FROM functions").fetchone()[0]
        metrics["total_imports"] = cursor.execute("SELECT COUNT(*) FROM imports").fetchone()[0]

        # Coupling metrics
        # Average efferent coupling (outgoing dependencies per module)
        avg_efferent = cursor.execute(
            """
            SELECT AVG(coupling) FROM (
                SELECT COUNT(DISTINCT target_module_id) as coupling
                FROM imports
                GROUP BY source_module_id
            )
        """
        ).fetchone()[0]
        metrics["avg_efferent_coupling"] = avg_efferent or 0.0

        # Average afferent coupling (incoming dependencies per module)
        avg_afferent = cursor.execute(
            """
            SELECT AVG(coupling) FROM (
                SELECT COUNT(DISTINCT source_module_id) as coupling
                FROM imports
                GROUP BY target_module_id
            )
        """
        ).fetchone()[0]
        metrics["avg_afferent_coupling"] = avg_afferent or 0.0

        # Complexity metrics
        avg_complexity = cursor.execute(
            "SELECT AVG(cyclomatic_complexity) FROM functions WHERE cyclomatic_complexity > 0"
        ).fetchone()[0]
        metrics["avg_cyclomatic_complexity"] = avg_complexity or 0.0

        max_complexity = cursor.execute("SELECT MAX(cyclomatic_complexity) FROM functions").fetchone()[0]
        metrics["max_cyclomatic_complexity"] = max_complexity or 0

        # Module with highest coupling
        max_coupling = cursor.execute(
            """
            SELECT MAX(coupling) FROM (
                SELECT COUNT(DISTINCT target_module_id) as coupling
                FROM imports
                GROUP BY source_module_id
            )
        """
        ).fetchone()[0]
        metrics["max_efferent_coupling"] = max_coupling or 0

        return metrics

    def _calculate_metric_diffs(
        self, base_metrics: dict[str, Any], head_metrics: dict[str, Any]
    ) -> list[MetricDiff]:
        """Calculate diffs for all metrics."""
        diffs = []

        for metric_name in base_metrics.keys():
            if metric_name not in head_metrics:
                continue

            base_value = float(base_metrics[metric_name])
            head_value = float(head_metrics[metric_name])

            diff = MetricDiff.calculate(metric_name, base_value, head_value)
            diffs.append(diff)

        return diffs

    def _generate_summary(self, files_changed: list[str], metric_diffs: list[MetricDiff]) -> dict[str, Any]:
        """Generate summary of architectural impact."""
        improved = [d for d in metric_diffs if d.impact == "improved"]
        degraded = [d for d in metric_diffs if d.impact == "degraded"]
        unchanged = [d for d in metric_diffs if d.impact == "unchanged"]

        # Overall assessment
        if len(degraded) == 0:
            overall = "positive"
        elif len(degraded) > len(improved):
            overall = "negative"
        else:
            overall = "mixed"

        return {
            "files_changed_count": len(files_changed),
            "metrics_improved": len(improved),
            "metrics_degraded": len(degraded),
            "metrics_unchanged": len(unchanged),
            "overall_impact": overall,
            "key_changes": [
                {"metric": d.metric_name, "change": d.percent_change, "impact": d.impact}
                for d in sorted(metric_diffs, key=lambda x: abs(x.absolute_change), reverse=True)[:5]
            ],
        }

    def format_diff_report(self, diff: ArchitecturalDiff) -> str:
        """
        Format architectural diff as human-readable report.

        Suitable for posting as GitHub PR comment.
        """
        lines = []

        lines.append("## 📊 Architectural Impact Analysis")
        lines.append("")
        lines.append(f"**Comparing:** `{diff.base_ref}` → `{diff.head_ref}`")
        lines.append(f"**Files Changed:** {diff.summary['files_changed_count']}")
        lines.append("")

        # Overall assessment
        impact_emoji = {"positive": "✅", "negative": "⚠️", "mixed": "ℹ️"}
        emoji = impact_emoji.get(diff.summary["overall_impact"], "ℹ️")
        lines.append(f"**Overall Impact:** {emoji} {diff.summary['overall_impact'].upper()}")
        lines.append("")

        # Summary
        lines.append("### Summary")
        lines.append(f"- ✅ Metrics Improved: {diff.summary['metrics_improved']}")
        lines.append(f"- ⚠️  Metrics Degraded: {diff.summary['metrics_degraded']}")
        lines.append(f"- ➖ Metrics Unchanged: {diff.summary['metrics_unchanged']}")
        lines.append("")

        # Key changes
        if diff.summary["key_changes"]:
            lines.append("### Key Changes")
            lines.append("")
            lines.append("| Metric | Change | Impact |")
            lines.append("|--------|--------|--------|")
            for change in diff.summary["key_changes"]:
                impact_icon = "✅" if change["impact"] == "improved" else "⚠️" if change["impact"] == "degraded" else "➖"
                change_str = (
                    f"{change['change']:+.1f}%" if change["change"] is not None else "N/A"
                )
                lines.append(f"| {change['metric']} | {change_str} | {impact_icon} |")
            lines.append("")

        # Detailed metrics
        improved = [d for d in diff.metrics if d.impact == "improved"]
        degraded = [d for d in diff.metrics if d.impact == "degraded"]

        if degraded:
            lines.append("### ⚠️  Degraded Metrics")
            lines.append("")
            for metric in degraded:
                change_str = (
                    f"{metric.percent_change:+.1f}%" if metric.percent_change is not None else f"{metric.absolute_change:+.2f}"
                )
                lines.append(
                    f"- **{metric.metric_name}**: {metric.before_value:.2f} → {metric.after_value:.2f} ({change_str})"
                )
            lines.append("")

        if improved:
            lines.append("### ✅ Improved Metrics")
            lines.append("")
            for metric in improved:
                change_str = (
                    f"{metric.percent_change:+.1f}%" if metric.percent_change is not None else f"{metric.absolute_change:+.2f}"
                )
                lines.append(
                    f"- **{metric.metric_name}**: {metric.before_value:.2f} → {metric.after_value:.2f} ({change_str})"
                )
            lines.append("")

        lines.append("---")
        lines.append("*Generated by depanalysis*")

        return "\n".join(lines)
