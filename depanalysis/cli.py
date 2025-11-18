"""
Command-line interface for depanalysis.

Provides commands for analyzing repositories, viewing metrics, and exporting data.
"""
from pathlib import Path
import click

from depanalysis.db_manager import DatabaseManager, get_repo_name_from_path
from depanalysis.git_analyzer import GitAnalyzer, discover_repositories
from depanalysis.metrics import MetricsAnalyzer
from depanalysis.structure_analyzer import StructureAnalyzer
from depanalysis.advanced_analytics import (
    AdvancedAnalyticsAPI,
    ChangeImpactAnalyzer,
    ArchitecturalPatternDetector,
    CodeQualityTrendsAnalyzer,
    DeveloperProductivityAnalyzer
)
import json


@click.group()
def main():
    """depanalysis - Python dependency and Git history analyzer."""
    pass


@main.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
def analyze_dir(directory: Path):
    """
    Analyze all Git repositories in a directory.

    Discovers all Git repositories in the specified directory and analyzes
    their Git history, populating history.db for each repository.
    """
    click.echo(f"Discovering repositories in {directory}...")
    repos = discover_repositories(directory)

    if not repos:
        click.echo("No Git repositories found.")
        return

    click.echo(f"Found {len(repos)} repositories:")
    for repo in repos:
        click.echo(f"  - {repo.name}")

    db_manager = DatabaseManager()

    for repo_path in repos:
        repo_name = get_repo_name_from_path(repo_path)
        click.echo(f"\nAnalyzing {repo_name}...")

        try:
            # Initialize database
            _, history_db = db_manager.initialize_repo_databases(repo_name)
            conn = db_manager.get_connection(repo_name, "history")

            # Analyze Git history
            analyzer = GitAnalyzer(repo_path, conn)
            stats = analyzer.analyze()

            click.echo(f"  ✓ Processed {stats['commits_processed']} commits")
            click.echo(f"  ✓ Found {stats['authors_found']} authors")
            click.echo(f"  ✓ Tracked {stats['files_tracked']} files")
            click.echo(f"  ✓ Calculated {stats['temporal_couplings']} temporal couplings")

            conn.close()

        except Exception as e:
            click.echo(f"  ✗ Error: {e}", err=True)

    click.echo(f"\nAnalysis complete! Data stored in ./data/")


@main.command()
@click.argument("repository", type=click.Path(exists=True, file_okay=False, path_type=Path))
def analyze_repo(repository: Path):
    """
    Analyze a single Git repository.

    Analyzes the specified Git repository's history and populates history.db.
    """
    if not (repository / ".git").exists():
        click.echo(f"Error: {repository} is not a Git repository", err=True)
        return

    repo_name = get_repo_name_from_path(repository)
    click.echo(f"Analyzing {repo_name}...")

    db_manager = DatabaseManager()

    try:
        # Initialize database
        structure_db, history_db = db_manager.initialize_repo_databases(repo_name)
        
        # 1. Analyze Git History
        click.echo("Analyzing Git history...")
        conn_hist = db_manager.get_connection(repo_name, "history")
        git_analyzer = GitAnalyzer(repository, conn_hist)
        stats_hist = git_analyzer.analyze()
        conn_hist.close()

        click.echo(f"  ✓ Processed {stats_hist['commits_processed']} commits")
        click.echo(f"  ✓ Found {stats_hist['authors_found']} authors")
        click.echo(f"  ✓ Tracked {stats_hist['files_tracked']} files")
        click.echo(f"  ✓ Calculated {stats_hist['temporal_couplings']} temporal couplings")

        # 2. Analyze Structure
        click.echo("\nAnalyzing Code Structure...")
        conn_struct = db_manager.get_connection(repo_name, "structure")
        struct_analyzer = StructureAnalyzer(repository, conn_struct)
        stats_struct = struct_analyzer.analyze()
        conn_struct.close()

        click.echo(f"  ✓ Parsed {stats_struct['files_parsed']} Python files")
        click.echo(f"  ✓ Found {stats_struct['classes_found']} classes")
        click.echo(f"  ✓ Found {stats_struct['functions_found']} functions")
        click.echo(f"  ✓ Found {stats_struct['imports_found']} imports")
        if stats_struct['errors'] > 0:
            click.echo(f"  ! Encountered {stats_struct['errors']} parsing errors")

        click.echo(f"\nData stored in:")
        click.echo(f"  - {history_db}")
        click.echo(f"  - {structure_db}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise


@main.command()
@click.argument("repo_name")
@click.option("--churn", is_flag=True, help="Show file churn metrics")
@click.option("--coupling", is_flag=True, help="Show temporal coupling")
@click.option("--authors", is_flag=True, help="Show author statistics")
@click.option("--all", "show_all", is_flag=True, help="Show all metrics")
@click.option("--export-csv", type=click.Path(path_type=Path), help="Export to CSV file")
@click.option("--export-json", type=click.Path(path_type=Path), help="Export to JSON file")
def show_metrics(repo_name, churn, coupling, authors, show_all, export_csv, export_json):
    """
    Display metrics for a repository.

    Shows various metrics for the specified repository including churn,
    temporal coupling, and author statistics.
    """
    db_manager = DatabaseManager()

    if not db_manager.repo_exists(repo_name):
        click.echo(f"Error: Repository '{repo_name}' not found in database", err=True)
        click.echo("Run 'depanalysis list' to see available repositories")
        return

    metrics = MetricsAnalyzer(db_manager)

    # Show summary
    click.echo(f"Repository: {repo_name}")
    click.echo("=" * 50)

    try:
        summary = metrics.get_summary_stats(repo_name)
        click.echo(f"Total Commits: {summary['total_commits']}")
        click.echo(f"Total Authors: {summary['total_authors']}")
        click.echo(f"Files Tracked: {summary['files_tracked']}")
        click.echo(f"Temporal Couplings: {summary['temporal_couplings']}")
        click.echo(f"Date Range: {summary['first_commit']} to {summary['last_commit']}")
        click.echo()
    except Exception as e:
        click.echo(f"Error getting summary: {e}", err=True)
        return

    # Default to showing all if no specific flags
    if not any([churn, coupling, authors]):
        show_all = True

    # Show churn metrics
    if churn or show_all:
        click.echo("File Churn Metrics (Top 10):")
        click.echo("-" * 50)
        df = metrics.get_churn_metrics(repo_name)
        if export_csv:
            metrics.export_to_csv(df, export_csv)
            click.echo(f"Exported to {export_csv}")
        elif export_json:
            metrics.export_to_json(df, export_json)
            click.echo(f"Exported to {export_json}")
        else:
            click.echo(df.head(10).to_string(index=False))
        click.echo()

    # Show temporal coupling
    if coupling or show_all:
        click.echo("High Temporal Coupling:")
        click.echo("-" * 50)
        df = metrics.get_high_temporal_coupling(repo_name)
        if export_csv:
            metrics.export_to_csv(df, export_csv)
        elif export_json:
            metrics.export_to_json(df, export_json)
        else:
            if len(df) > 0:
                click.echo(df.to_string(index=False))
            else:
                click.echo("No high temporal coupling found")
        click.echo()

    # Show author stats
    if authors or show_all:
        click.echo("Author Statistics:")
        click.echo("-" * 50)
        df = metrics.get_author_stats(repo_name)
        if export_csv:
            metrics.export_to_csv(df, export_csv)
        elif export_json:
            metrics.export_to_json(df, export_json)
        else:
            click.echo(df.to_string(index=False))
        click.echo()


@main.command()
@click.argument("repo_names", nargs=-1, required=True)
def compare_repos(repo_names):
    """
    Compare metrics across multiple repositories.

    Compares author statistics and churn metrics across the specified repositories.
    """
    db_manager = DatabaseManager()
    metrics = MetricsAnalyzer(db_manager)

    # Validate repositories
    for repo_name in repo_names:
        if not db_manager.repo_exists(repo_name):
            click.echo(f"Error: Repository '{repo_name}' not found", err=True)
            return

    click.echo(f"Comparing {len(repo_names)} repositories:")
    for repo_name in repo_names:
        click.echo(f"  - {repo_name}")
    click.echo()

    # Compare author stats
    click.echo("Author Statistics Comparison:")
    click.echo("=" * 80)
    author_df = metrics.compare_author_stats_across_repos(list(repo_names))
    click.echo(author_df.to_string(index=False))
    click.echo()

    # Compare churn
    click.echo("Churn Metrics Comparison (Top 10 per repo):")
    click.echo("=" * 80)
    churn_df = metrics.compare_churn_across_repos(list(repo_names))
    for repo in repo_names:
        repo_churn = churn_df[churn_df["repository"] == repo].head(10)
        if len(repo_churn) > 0:
            click.echo(f"\n{repo}:")
            click.echo(repo_churn[["file_path", "total_churn", "total_commits"]].to_string(index=False))


@main.command(name="list")
def list_repos():
    """
    List all analyzed repositories.

    Shows all repositories that have been analyzed and stored in the database.
    """
    db_manager = DatabaseManager()
    repos = db_manager.list_analyzed_repos()

    if not repos:
        click.echo("No repositories have been analyzed yet.")
        click.echo("Use 'depanalysis analyze-repo' or 'depanalysis analyze-dir' to analyze repositories.")
        return

    click.echo(f"Analyzed repositories ({len(repos)}):")
    for repo in repos:
        click.echo(f"  - {repo}")


# =============================================================================
# TIER 3 COMMANDS: Advanced Analytics
# =============================================================================

@main.command()
@click.argument("repo_name")
@click.argument("module_path")
@click.option("--max-depth", type=int, help="Maximum dependency depth to traverse")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def impact(repo_name, module_path, max_depth, json_output):
    """
    Analyze change impact for a module (Feature 7: Change Impact Analysis).

    Shows:
    - Transitive dependencies (files this module depends on)
    - Reverse dependencies (files that depend on this module)
    - Test impact (which tests should run)
    - Blast radius (combined structural + temporal impact)
    """
    db_manager = DatabaseManager()

    if not db_manager.repo_exists(repo_name):
        click.echo(f"Error: Repository '{repo_name}' not found", err=True)
        return

    analyzer = ChangeImpactAnalyzer(db_manager)

    # Get all impact metrics
    deps = analyzer.get_transitive_dependencies(repo_name, module_path, max_depth)
    reverse_deps = analyzer.get_reverse_dependencies(repo_name, module_path, max_depth)
    test_impact = analyzer.get_test_impact(repo_name, module_path)
    blast_radius = analyzer.get_blast_radius(repo_name, module_path)

    if json_output:
        result = {
            "module": module_path,
            "dependencies": deps,
            "reverse_dependencies": reverse_deps,
            "test_impact": test_impact,
            "blast_radius": blast_radius
        }
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"Change Impact Analysis: {module_path}")
        click.echo("=" * 80)
        click.echo()

        click.echo("DEPENDENCIES (what this module imports):")
        click.echo(f"  Total: {deps['total_dependencies']} modules, Max Depth: {deps['max_depth']}")
        for depth, modules in deps.get('by_depth', {}).items():
            click.echo(f"  Depth {depth}: {len(modules)} modules")
            if len(modules) <= 5:
                for mod in modules:
                    click.echo(f"    - {mod}")
        click.echo()

        click.echo("REVERSE DEPENDENCIES (what imports this module):")
        click.echo(f"  Total: {reverse_deps['total_dependents']} modules")
        for depth, modules in reverse_deps.get('by_depth', {}).items():
            click.echo(f"  Depth {depth}: {len(modules)} modules")
            if len(modules) <= 5:
                for mod in modules:
                    click.echo(f"    - {mod}")
        click.echo()

        click.echo("TEST IMPACT:")
        click.echo(f"  Total test files: {test_impact['total_test_files']}")
        if test_impact['all_tests']:
            for test in test_impact['all_tests'][:10]:
                click.echo(f"    - {test}")
        click.echo()

        click.echo("BLAST RADIUS:")
        click.echo(f"  Total affected files: {blast_radius['total_affected_files']}")
        click.echo(f"  High risk (structural + temporal): {blast_radius['both_structural_and_temporal']}")
        click.echo(f"  Hidden dependencies (temporal only): {blast_radius['temporal_only']}")
        if blast_radius['high_risk_files']:
            click.echo("  High risk files:")
            for file in blast_radius['high_risk_files'][:10]:
                click.echo(f"    - {file}")


@main.command()
@click.argument("repo_name")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def patterns(repo_name, json_output):
    """
    Detect architectural patterns and anti-patterns (Feature 8).

    Shows:
    - Module centrality metrics (hubs, leaves, roots)
    - Layered architecture detection
    - God classes
    - Shotgun surgery anti-pattern
    """
    db_manager = DatabaseManager()

    if not db_manager.repo_exists(repo_name):
        click.echo(f"Error: Repository '{repo_name}' not found", err=True)
        return

    detector = ArchitecturalPatternDetector(db_manager)

    # Get all pattern metrics
    centrality = detector.calculate_centrality_metrics(repo_name)
    layers = detector.detect_layered_architecture(repo_name)
    god_classes = detector.detect_god_classes(repo_name)
    shotgun = detector.detect_shotgun_surgery(repo_name)

    if json_output:
        result = {
            "centrality": centrality.to_dict('records') if len(centrality) > 0 else [],
            "layers": layers,
            "god_classes": god_classes.to_dict('records') if len(god_classes) > 0 else [],
            "shotgun_surgery": shotgun
        }
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"Architectural Pattern Analysis: {repo_name}")
        click.echo("=" * 80)
        click.echo()

        click.echo("MODULE CENTRALITY (Top 10 by PageRank):")
        click.echo("-" * 80)
        if len(centrality) > 0:
            top_central = centrality.head(10)
            for _, row in top_central.iterrows():
                hub_marker = " [HUB]" if row['is_hub'] else ""
                click.echo(f"  {row['module_path']}: in={row['in_degree']}, out={row['out_degree']}, "
                          f"score={row['pagerank_score']:.4f}{hub_marker}")
        else:
            click.echo("  No modules found")
        click.echo()

        click.echo("LAYERED ARCHITECTURE:")
        click.echo("-" * 80)
        click.echo(f"  Total layers detected: {layers['total_layers']}")
        click.echo("  Layers:")
        for layer, count in layers['layers'].items():
            click.echo(f"    {layer}: {count} files")
        if layers['circular_layer_dependencies']:
            click.echo("\n  WARNING: Circular dependencies between layers:")
            for violation in layers['circular_layer_dependencies']:
                click.echo(f"    {violation['layer_a']} <-> {violation['layer_b']}")
        click.echo()

        click.echo("GOD CLASSES (high complexity + many methods):")
        click.echo("-" * 80)
        if len(god_classes) > 0:
            for _, row in god_classes.head(10).iterrows():
                click.echo(f"  {row['name']} ({row['module_path']})")
                click.echo(f"    Methods: {row['method_count']}, Complexity: {row['total_complexity']}, "
                          f"LOC: {row['lines_of_code']}")
        else:
            click.echo("  No God classes detected")
        click.echo()

        click.echo("SHOTGUN SURGERY (commits changing many files):")
        click.echo("-" * 80)
        if shotgun:
            for commit in shotgun[:10]:
                click.echo(f"  {commit['hash'][:8]} by {commit['author_name']}")
                click.echo(f"    Files: {commit['files_changed']}, Churn: {commit['total_churn']}")
                click.echo(f"    {commit['message'][:60]}...")
        else:
            click.echo("  No shotgun surgery pattern detected")


@main.command()
@click.argument("repo_name")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def productivity(repo_name, json_output):
    """
    Analyze developer productivity insights (Feature 10).

    Shows:
    - Onboarding metrics
    - Collaboration patterns
    - Cognitive load per developer
    - Code ownership evolution
    """
    db_manager = DatabaseManager()

    if not db_manager.repo_exists(repo_name):
        click.echo(f"Error: Repository '{repo_name}' not found", err=True)
        return

    analyzer = DeveloperProductivityAnalyzer(db_manager)

    # Get all productivity metrics
    onboarding = analyzer.get_onboarding_metrics(repo_name)
    collaboration = analyzer.get_collaboration_patterns(repo_name)
    cognitive_load = analyzer.get_cognitive_load_metrics(repo_name)
    ownership = analyzer.get_code_ownership_evolution(repo_name)

    if json_output:
        result = {
            "onboarding": onboarding.to_dict('records') if len(onboarding) > 0 else [],
            "collaboration": collaboration,
            "cognitive_load": cognitive_load.to_dict('records') if len(cognitive_load) > 0 else [],
            "ownership_evolution": ownership
        }
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"Developer Productivity Insights: {repo_name}")
        click.echo("=" * 80)
        click.echo()

        click.echo("ONBOARDING METRICS:")
        click.echo("-" * 80)
        if len(onboarding) > 0:
            for _, row in onboarding.head(10).iterrows():
                click.echo(f"  {row['name']} ({row['email']})")
                click.echo(f"    First commit: {row['first_commit']}")
                click.echo(f"    Total commits: {row['total_commits']}, Files: {row['files_touched']}, "
                          f"Active: {row['days_active']:.0f} days")
        else:
            click.echo("  No data available")
        click.echo()

        click.echo("TOP COLLABORATIONS (shared file ownership):")
        click.echo("-" * 80)
        if collaboration['top_collaborations']:
            for collab in collaboration['top_collaborations'][:10]:
                click.echo(f"  {collab['authors'][0]} & {collab['authors'][1]}: "
                          f"{collab['shared_files']} shared files")
        else:
            click.echo("  No collaboration patterns detected")
        click.echo()

        click.echo("COGNITIVE LOAD (Top 10 developers):")
        click.echo("-" * 80)
        if len(cognitive_load) > 0:
            for _, row in cognitive_load.head(10).iterrows():
                click.echo(f"  {row['name']}")
                click.echo(f"    Files: {row['files_owned']}, Complexity: {row['total_complexity']:.0f}, "
                          f"Coupling: {row['total_coupling']:.0f}")
                click.echo(f"    Cognitive Load Score: {row['cognitive_load_score']:.2f}")
        else:
            click.echo("  No data available")
        click.echo()

        click.echo("CODE OWNERSHIP EVOLUTION (Top 10 shared files):")
        click.echo("-" * 80)
        if ownership:
            for item in ownership[:10]:
                click.echo(f"  {item['file_path']}")
                click.echo(f"    Primary: {item['primary_owner']} ({item['primary_percentage']*100:.1f}%)")
                click.echo(f"    Secondary: {item['secondary_owner']} ({item['secondary_percentage']*100:.1f}%)")
        else:
            click.echo("  No shared ownership detected")


@main.command()
@click.argument("repo_name")
@click.argument("output_dir", type=click.Path(path_type=Path))
def export_tier3(repo_name, output_dir):
    """
    Export all Tier 3 analytics to JSON files.

    Exports all advanced analytics metrics to separate JSON files
    for use with Observable Framework or other tools.
    """
    db_manager = DatabaseManager()

    if not db_manager.repo_exists(repo_name):
        click.echo(f"Error: Repository '{repo_name}' not found", err=True)
        return

    click.echo(f"Exporting Tier 3 analytics for {repo_name}...")

    api = AdvancedAnalyticsAPI(db_manager)
    exported = api.export_all_metrics(repo_name, output_dir)

    click.echo(f"\nExported {len(exported)} metric files:")
    for metric_name, file_path in exported.items():
        click.echo(f"  ✓ {metric_name}: {file_path}")

    click.echo(f"\nAll files written to: {output_dir}")


if __name__ == "__main__":
    main()
