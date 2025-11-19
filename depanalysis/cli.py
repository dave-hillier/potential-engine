"""
Command-line interface for depanalysis.

Provides commands for analyzing repositories, viewing metrics, and exporting data.
"""
from pathlib import Path
import click

from depanalysis.db_manager import DatabaseManager, get_repo_name_from_path
from depanalysis.git_analyzer import GitAnalyzer, discover_repositories
from depanalysis.metrics import MetricsAnalyzer
from depanalysis.tree_sitter_python import TreeSitterPythonParser
from depanalysis.tree_sitter_typescript import TreeSitterTypeScriptParser, TreeSitterJavaScriptParser
from depanalysis.tree_sitter_csharp import TreeSitterCSharpParser
from depanalysis.tree_sitter_multi_lang import (
    TreeSitterJavaParser,
    TreeSitterRustParser,
    TreeSitterCppParser,
    TreeSitterGoParser
)
from depanalysis.cross_language_analyzer import CrossLanguageAnalyzer
from depanalysis.ecosystem_analyzer import EcosystemAnalyzer


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

        # =====================================================================
        # PARSE PHASE: Extract data from Git and source files → Write to DBs
        # =====================================================================

        # 1. Parse Git History → history.db
        click.echo("Parsing Git history...")
        conn_hist = db_manager.get_connection(repo_name, "history")
        git_analyzer = GitAnalyzer(repository, conn_hist)
        stats_hist = git_analyzer.analyze()
        conn_hist.close()

        click.echo(f"  ✓ Processed {stats_hist['commits_processed']} commits")
        click.echo(f"  ✓ Found {stats_hist['authors_found']} authors")
        click.echo(f"  ✓ Tracked {stats_hist['files_tracked']} files")
        click.echo(f"  ✓ Calculated {stats_hist['temporal_couplings']} temporal couplings")

        # 2. Parse Source Code Structure → structure.db
        click.echo("\n" + "="*70)
        click.echo("PARSE PHASE: Extracting structure from source files...")
        click.echo("="*70)

        conn_struct = db_manager.get_connection(repo_name, "structure")

        # 2a. Python Parser (tree-sitter)
        click.echo("\nParsing Python Code (tree-sitter)...")
        python_parser = TreeSitterPythonParser(repository, conn_struct)
        stats_python = python_parser.analyze()

        if stats_python['files_parsed'] > 0:
            click.echo(f"  ✓ Parsed {stats_python['files_parsed']} Python files")
            click.echo(f"  ✓ Found {stats_python['classes_found']} classes")
            click.echo(f"  ✓ Found {stats_python['functions_found']} functions")
            click.echo(f"  ✓ Found {stats_python['imports_found']} imports")
            if stats_python['errors'] > 0:
                click.echo(f"  ! Encountered {stats_python['errors']} parsing errors")
        else:
            click.echo("  - No Python files found")

        # 2b. TypeScript Parser (tree-sitter)
        click.echo("\nParsing TypeScript Code (tree-sitter)...")
        ts_parser = TreeSitterTypeScriptParser(repository, conn_struct)
        stats_ts = ts_parser.analyze()

        if stats_ts['files_parsed'] > 0:
            click.echo(f"  ✓ Parsed {stats_ts['files_parsed']} TypeScript files")
            click.echo(f"  ✓ Found {stats_ts['classes_found']} classes")
            click.echo(f"  ✓ Found {stats_ts['functions_found']} functions")
            click.echo(f"  ✓ Found {stats_ts['imports_found']} imports")
            if stats_ts['errors'] > 0:
                click.echo(f"  ! Encountered {stats_ts['errors']} parsing errors")
        else:
            click.echo("  - No TypeScript files found")

        # 2c. JavaScript Parser (tree-sitter)
        click.echo("\nParsing JavaScript Code (tree-sitter)...")
        js_parser = TreeSitterJavaScriptParser(repository, conn_struct)
        stats_js = js_parser.analyze()

        if stats_js['files_parsed'] > 0:
            click.echo(f"  ✓ Parsed {stats_js['files_parsed']} JavaScript files")
            click.echo(f"  ✓ Found {stats_js['classes_found']} classes")
            click.echo(f"  ✓ Found {stats_js['functions_found']} functions")
            click.echo(f"  ✓ Found {stats_js['imports_found']} imports")
            if stats_js['errors'] > 0:
                click.echo(f"  ! Encountered {stats_js['errors']} parsing errors")
        else:
            click.echo("  - No JavaScript files found")

        # 2d. C# Parser (tree-sitter)
        click.echo("\nParsing C# Code (tree-sitter)...")
        cs_parser = TreeSitterCSharpParser(repository, conn_struct)
        stats_cs = cs_parser.analyze()

        if stats_cs['files_parsed'] > 0:
            click.echo(f"  ✓ Parsed {stats_cs['files_parsed']} C# files")
            click.echo(f"  ✓ Found {stats_cs['classes_found']} classes")
            click.echo(f"  ✓ Found {stats_cs['functions_found']} methods")
            click.echo(f"  ✓ Found {stats_cs['variables_found']} properties/fields")
            click.echo(f"  ✓ Found {stats_cs['imports_found']} using statements")
            if stats_cs['errors'] > 0:
                click.echo(f"  ! Encountered {stats_cs['errors']} parsing errors")
        else:
            click.echo("  - No C# files found")

        # 2e. Java Parser (tree-sitter)
        click.echo("\nParsing Java Code (tree-sitter)...")
        java_parser = TreeSitterJavaParser(repository, conn_struct)
        stats_java = java_parser.analyze()

        if stats_java['files_parsed'] > 0:
            click.echo(f"  ✓ Parsed {stats_java['files_parsed']} Java files")
            click.echo(f"  ✓ Found {stats_java['classes_found']} classes")
            click.echo(f"  ✓ Found {stats_java['functions_found']} methods")
            click.echo(f"  ✓ Found {stats_java['imports_found']} imports")
            if stats_java['errors'] > 0:
                click.echo(f"  ! Encountered {stats_java['errors']} parsing errors")
        else:
            click.echo("  - No Java files found")

        # 2f. Rust Parser (tree-sitter)
        click.echo("\nParsing Rust Code (tree-sitter)...")
        rust_parser = TreeSitterRustParser(repository, conn_struct)
        stats_rust = rust_parser.analyze()

        if stats_rust['files_parsed'] > 0:
            click.echo(f"  ✓ Parsed {stats_rust['files_parsed']} Rust files")
            click.echo(f"  ✓ Found {stats_rust['classes_found']} structs/traits")
            click.echo(f"  ✓ Found {stats_rust['functions_found']} functions")
            click.echo(f"  ✓ Found {stats_rust['imports_found']} use statements")
            if stats_rust['errors'] > 0:
                click.echo(f"  ! Encountered {stats_rust['errors']} parsing errors")
        else:
            click.echo("  - No Rust files found")

        # 2g. C++ Parser (tree-sitter)
        click.echo("\nParsing C++ Code (tree-sitter)...")
        cpp_parser = TreeSitterCppParser(repository, conn_struct)
        stats_cpp = cpp_parser.analyze()

        if stats_cpp['files_parsed'] > 0:
            click.echo(f"  ✓ Parsed {stats_cpp['files_parsed']} C++ files")
            click.echo(f"  ✓ Found {stats_cpp['classes_found']} classes/structs")
            click.echo(f"  ✓ Found {stats_cpp['functions_found']} functions")
            click.echo(f"  ✓ Found {stats_cpp['imports_found']} includes")
            if stats_cpp['errors'] > 0:
                click.echo(f"  ! Encountered {stats_cpp['errors']} parsing errors")
        else:
            click.echo("  - No C++ files found")

        # 2h. Go Parser (tree-sitter)
        click.echo("\nParsing Go Code (tree-sitter)...")
        go_parser = TreeSitterGoParser(repository, conn_struct)
        stats_go = go_parser.analyze()

        if stats_go['files_parsed'] > 0:
            click.echo(f"  ✓ Parsed {stats_go['files_parsed']} Go files")
            click.echo(f"  ✓ Found {stats_go['classes_found']} types")
            click.echo(f"  ✓ Found {stats_go['functions_found']} functions/methods")
            click.echo(f"  ✓ Found {stats_go['imports_found']} imports")
            if stats_go['errors'] > 0:
                click.echo(f"  ! Encountered {stats_go['errors']} parsing errors")
        else:
            click.echo("  - No Go files found")

        # 2i. API Boundary Parser (REST, GraphQL, Protocol Buffers)
        click.echo("\nParsing API Boundaries (endpoints, calls, shared types)...")
        cross_lang_analyzer = CrossLanguageAnalyzer(repository, conn_struct, None)
        stats_cross = cross_lang_analyzer.parse()

        if stats_cross['api_endpoints_found'] > 0 or stats_cross['api_calls_found'] > 0:
            click.echo(f"  ✓ Found {stats_cross['api_endpoints_found']} API endpoints")
            click.echo(f"  ✓ Found {stats_cross['api_calls_found']} API calls")
            click.echo(f"  ✓ Found {stats_cross['shared_types_found']} shared type definitions")
            click.echo(f"    - {stats_cross['proto_files']} Protocol Buffer files")
            click.echo(f"    - {stats_cross['graphql_files']} GraphQL files")
            click.echo(f"    - {stats_cross['openapi_files']} OpenAPI specifications")
        else:
            click.echo("  - No cross-language dependencies detected")

        # 2j. Manifest Parser (package.json, requirements.txt, Cargo.toml, etc.)
        click.echo("\nParsing Package Manifest Files...")
        ecosystem_analyzer = EcosystemAnalyzer(repository, conn_struct)
        stats_ecosystem = ecosystem_analyzer.parse()

        if stats_ecosystem['dependencies_found'] > 0:
            click.echo(f"  ✓ Analyzed {stats_ecosystem['manifest_files']} package manifest files")
            click.echo(f"  ✓ Found {stats_ecosystem['dependencies_found']} external dependencies")
            if stats_ecosystem['python_deps'] > 0:
                click.echo(f"    - {stats_ecosystem['python_deps']} Python packages")
            if stats_ecosystem['javascript_deps'] > 0:
                click.echo(f"    - {stats_ecosystem['javascript_deps']} JavaScript/TypeScript packages")
            if stats_ecosystem['rust_deps'] > 0:
                click.echo(f"    - {stats_ecosystem['rust_deps']} Rust crates")
            if stats_ecosystem['java_deps'] > 0:
                click.echo(f"    - {stats_ecosystem['java_deps']} Java packages")
            if stats_ecosystem['go_deps'] > 0:
                click.echo(f"    - {stats_ecosystem['go_deps']} Go modules")
            if stats_ecosystem['cpp_deps'] > 0:
                click.echo(f"    - {stats_ecosystem['cpp_deps']} C++ libraries")
            if stats_ecosystem['conflicts_found'] > 0:
                click.echo(f"  ⚠ Detected {stats_ecosystem['conflicts_found']} version conflicts")
        else:
            click.echo("  - No package manifest files found")

        conn_struct.close()

        click.echo("\n" + "="*70)
        click.echo("PARSE PHASE COMPLETE")
        click.echo("="*70)
        click.echo(f"\nAll data persisted to databases:")
        click.echo(f"  - {history_db}")
        click.echo(f"  - {structure_db}")
        click.echo("\nNext steps:")
        click.echo("  - Query metrics: depanalysis show-metrics <repo>")
        click.echo("  - View visualizations: cd docs && npm run dev")

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


if __name__ == "__main__":
    main()
