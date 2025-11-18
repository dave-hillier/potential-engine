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
from depanalysis.architectural_rules import ArchitecturalRules, ArchitectureValidator
from depanalysis.migration_planning import MigrationConfig, MigrationScanner, MigrationTracker
from depanalysis.diff_analysis import DiffAnalyzer


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


@main.command(name="validate")
@click.argument("repo_name")
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    default=".depanalysis.yml",
    help="Path to architectural rules configuration file",
)
@click.option(
    "--fail-on-error/--no-fail-on-error",
    default=True,
    help="Exit with non-zero code if errors found",
)
@click.option(
    "--fail-on-warning/--no-fail-on-warning",
    default=False,
    help="Exit with non-zero code if warnings found",
)
def validate(repo_name, config, fail_on_error, fail_on_warning):
    """
    Validate repository against architectural rules.

    Checks the repository against rules defined in .depanalysis.yml
    and reports violations. Designed for CI/CD integration.

    Exit codes:
      0 - All rules passed
      1 - Errors found (if --fail-on-error)
      2 - Warnings found (if --fail-on-warning)
    """
    db_manager = DatabaseManager()

    if not db_manager.repo_exists(repo_name):
        click.echo(f"Error: Repository '{repo_name}' not found in database", err=True)
        click.echo("Run 'depanalysis list' to see available repositories")
        return 1

    # Load configuration
    if not config.exists():
        click.echo(f"Error: Configuration file not found: {config}", err=True)
        click.echo("Create .depanalysis.yml (see .depanalysis.example.yml)")
        return 1

    try:
        rules = ArchitecturalRules.from_yaml(config)
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        return 1

    # Validate
    click.echo(f"Validating {repo_name} against architectural rules...")
    click.echo(f"Configuration: {config}")
    click.echo("=" * 70)

    validator = ArchitectureValidator(db_manager, rules)
    violations = validator.validate(repo_name)

    if not violations:
        click.echo("✓ All architectural rules passed!")
        return 0

    # Group violations by severity
    errors = [v for v in violations if v.severity == "error"]
    warnings = [v for v in violations if v.severity == "warning"]

    # Display violations
    if errors:
        click.echo(f"\n❌ ERRORS ({len(errors)}):")
        click.echo("-" * 70)
        for v in errors:
            click.echo(f"  {v.message}")

    if warnings:
        click.echo(f"\n⚠️  WARNINGS ({len(warnings)}):")
        click.echo("-" * 70)
        for v in warnings:
            click.echo(f"  {v.message}")

    # Summary
    click.echo("\n" + "=" * 70)
    click.echo(f"Summary: {len(errors)} errors, {len(warnings)} warnings")

    # Exit code logic
    if errors and fail_on_error:
        click.echo("\n❌ Validation failed (errors found)")
        return 1
    elif warnings and fail_on_warning:
        click.echo("\n⚠️  Validation failed (warnings found)")
        return 2
    else:
        click.echo("\n✓ Validation passed")
        return 0


@main.group(name="migration")
def migration_group():
    """
    Migration planning and pattern tracking commands.

    Track large refactoring efforts like Python 2→3, framework migrations,
    deprecation tracking, and architectural transformations.
    """
    pass


@migration_group.command(name="scan")
@click.argument("repository", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to migration configuration YAML file",
)
@click.option(
    "--save/--no-save",
    default=True,
    help="Save results to database",
)
def migration_scan(repository, config, save):
    """
    Scan repository for migration patterns.

    Scans the repository for patterns defined in the migration config
    and reports occurrences. Useful for tracking migration progress.
    """
    repo_name = get_repo_name_from_path(repository)

    # Load migration configuration
    try:
        migration_config = MigrationConfig.from_yaml(config)
    except Exception as e:
        click.echo(f"Error loading migration config: {e}", err=True)
        return 1

    click.echo(f"Migration: {migration_config.name}")
    click.echo(f"Description: {migration_config.description}")
    click.echo(f"Patterns: {len(migration_config.patterns)}")
    click.echo("=" * 70)

    # Initialize scanner
    scanner = MigrationScanner(repository)
    all_occurrences = []

    # Scan each pattern
    for pattern in migration_config.patterns:
        click.echo(f"\nScanning: {pattern.name} ({pattern.severity})...")
        occurrences = scanner.scan_pattern(pattern)

        click.echo(f"  Found: {len(occurrences)} occurrences")

        if occurrences:
            all_occurrences.extend(occurrences)

            # Show first 5 occurrences
            for occ in occurrences[:5]:
                click.echo(f"    {occ.file_path}:{occ.line_number} - {occ.matched_text}")

            if len(occurrences) > 5:
                click.echo(f"    ... and {len(occurrences) - 5} more")

    # Save to database if requested
    if save:
        db_manager = DatabaseManager()
        tracker = MigrationTracker(db_manager)

        click.echo("\nSaving to database...")
        tracker.save_migration_project(repo_name, migration_config)
        tracker.save_scan_results(repo_name, all_occurrences)
        click.echo("✓ Results saved")

    # Summary
    click.echo("\n" + "=" * 70)
    click.echo(f"Total occurrences: {len(all_occurrences)}")
    click.echo(f"Affected files: {len(set(occ.file_path for occ in all_occurrences))}")


@migration_group.command(name="progress")
@click.argument("repo_name")
@click.argument("migration_id")
def migration_progress(repo_name, migration_id):
    """
    Show migration progress for a repository.

    Displays statistics about migration pattern occurrences
    and affected files.
    """
    db_manager = DatabaseManager()

    if not db_manager.repo_exists(repo_name):
        click.echo(f"Error: Repository '{repo_name}' not found", err=True)
        return 1

    tracker = MigrationTracker(db_manager)

    try:
        progress = tracker.get_migration_progress(repo_name, migration_id)
    except Exception as e:
        click.echo(f"Error getting migration progress: {e}", err=True)
        return 1

    click.echo(f"Migration: {migration_id}")
    click.echo("=" * 70)
    click.echo(f"Total occurrences: {progress['total_occurrences']}")
    click.echo(f"Affected files: {progress['affected_files']}")
    click.echo("\nBy severity:")
    for severity, count in progress["by_severity"].items():
        click.echo(f"  {severity}: {count}")


@main.command()
@click.argument("repository", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("base_ref")
@click.option("--head-ref", default="HEAD", help="Head reference to compare (default: HEAD)")
@click.option("--output", type=click.Path(path_type=Path), help="Save report to file")
def diff(repository, base_ref, head_ref, output):
    """
    Analyze architectural diff between two Git refs.

    Compares metrics between BASE_REF and HEAD_REF (default: HEAD)
    and reports the impact of changes on architecture quality.

    Examples:
      depanalysis diff . main
      depanalysis diff . main --head-ref feature-branch
      depanalysis diff . abc123 --output diff-report.md
    """
    db_manager = DatabaseManager()

    click.echo(f"Analyzing architectural diff: {base_ref} → {head_ref}")
    click.echo("=" * 70)

    try:
        analyzer = DiffAnalyzer(repository, db_manager)
        diff_result = analyzer.analyze_diff(base_ref, head_ref)

        # Format report
        report = analyzer.format_diff_report(diff_result)

        # Output
        if output:
            output.write_text(report)
            click.echo(f"\n✓ Report saved to {output}")
        else:
            click.echo(report)

    except Exception as e:
        click.echo(f"Error analyzing diff: {e}", err=True)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    main()
