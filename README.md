# depanalysis

Multi-language dependency and Git history analyzer combining static structural analysis (AST parsing) with temporal behavioral analysis to identify architectural issues, coupling problems, and maintenance hotspots.

## Features

### Core Analysis
- **Multi-Language Support**: Python, TypeScript, JavaScript, C#, Java, Rust, C++, and Go via tree-sitter parsers
- **Structural Analysis**: Afferent/efferent coupling, instability, cyclomatic complexity
- **Git History Analysis**: Commits, file changes, temporal coupling, and churn metrics
- **Temporal Coupling**: Identify files that frequently change together using Jaccard similarity
- **Author Analytics**: Track contributor patterns and code ownership
- **Cross-Language Features**: API boundary detection, shared type definitions, ecosystem analysis

### Visualization & Export
- **Interactive Dashboards**: Observable Framework web-based visualizations
- **Multi-Repository Comparison**: Analyze multiple repositories with cross-repo comparisons
- **Data Export**: CSV and JSON export for external analysis

## Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package
pip install -e .
```

## Quick Start

```bash
# Generate example repositories (first-time setup)
depanalysis regenerate-examples

# Analyze a directory containing Git repositories
depanalysis analyze-dir examples/repos

# Analyze a single repository
depanalysis analyze-repo /path/to/repo

# View metrics for a repository
depanalysis show-metrics high-churn

# Compare multiple repositories
depanalysis compare-repos high-churn multi-author simple-linear

# List all analyzed repositories
depanalysis list
```

## Interactive Reports

**All visualization lives in the `docs/` directory** using Observable Framework. Changes to visualizations may require updates to:
- Data loader scripts (`docs/data/*.py`)
- Database schemas (`data/<repo>/history.db` or `structure.db`)
- Observable pages (`docs/*.md` and `docs/repo/*.md`)

View analysis results in an interactive web dashboard:

```bash
# Start development server
cd docs
npm install  # First time only
npm run dev

# Open http://localhost:3000 in your browser
```

Build static site for deployment:

```bash
cd docs
npm run build

# Static files generated in dist/ directory
# Deploy to any static hosting (GitHub Pages, Netlify, S3, etc.)
```

### Report Features

- **Repository Overview**: Summary stats and visualizations per repository
- **Temporal Coupling Network**: Interactive D3.js force-directed graph showing files that change together
- **Author Analytics**: Contribution patterns and code ownership breakdowns
- **Cross-Repository Comparison**: Side-by-side metrics across multiple repos
- **Churn Analysis**: Bar charts and tables of file change frequency

## CLI Commands

### Analysis Commands

```bash
# Analyze all repos in a directory
depanalysis analyze-dir <directory>

# Analyze a single repository
depanalysis analyze-repo <repository_path>

# Generate example repositories for testing and documentation
depanalysis regenerate-examples [--clean]
```

### Viewing Metrics

```bash
# Show all metrics for a repository
depanalysis show-metrics <repo_name>

# Show specific metrics
depanalysis show-metrics <repo_name> --churn
depanalysis show-metrics <repo_name> --coupling
depanalysis show-metrics <repo_name> --authors

# Export to CSV or JSON
depanalysis show-metrics <repo_name> --export-csv output.csv
depanalysis show-metrics <repo_name> --export-json output.json
```

### Comparison

```bash
# Compare metrics across repositories
depanalysis compare-repos <repo1> <repo2> [repo3...]

# List all analyzed repositories
depanalysis list
```

## Example Repositories

The project includes three example repositories that demonstrate different patterns:

### simple-linear
- **Purpose**: Single author, linear history, clear dependency chain
- **Commits**: 5 commits over 30 days
- **Files**: 3 Python files (main.py, utils.py, config.py)
- **Pattern**: Progressive feature development with imports

### multi-author
- **Purpose**: Multiple contributors, overlapping changes, temporal coupling
- **Commits**: 7 commits from 3 different authors
- **Files**: 3 Python files (server.py, client.py, protocol.py)
- **Pattern**: Collaborative development with shared protocol

### high-churn
- **Purpose**: Frequent changes, strong temporal coupling, hotspot detection
- **Commits**: 14 commits showing iterative refinement
- **Files**: 3 Python files (models.py, views.py, tests.py)
- **Pattern**: models.py and views.py always change together (strong coupling)

### Regenerating Examples

To regenerate the example repositories and their databases:

```bash
# Generate repos and analyze them (creates both structure.db and history.db)
depanalysis regenerate-examples

# Or with --clean to remove existing databases first
depanalysis regenerate-examples --clean

# Run tests to verify
pytest tests/test_examples.py
```

The `regenerate-examples` command:
1. Creates Git repositories with realistic commit histories in `examples/repos/`
2. Analyzes each repository to generate `structure.db` and `history.db`
3. Stores databases in `data/<repo-name>/`
4. Validates that examples are ready for development and testing

## Data Storage

Analysis data is stored in SQLite databases:

```
data/
├── <repo_name>/
│   ├── structure.db  # AST-parsed structural relationships (all languages)
│   └── history.db    # Git history and temporal coupling
```

Each repository has its own separate databases, enabling:
- Independent analysis per repository
- Cross-repository comparisons
- Efficient incremental updates with file hash tracking
- Language-agnostic schema supporting polyglot repositories

## Key Metrics

### Structural Metrics

- **Afferent Coupling (Ca)**: Incoming dependencies to a module
- **Efferent Coupling (Ce)**: Outgoing dependencies from a module
- **Instability**: Ce / (Ca + Ce)
- **Cyclomatic Complexity**: Independent paths through code
- **Dependencies**: Import relationships, inheritance, function calls

### Temporal Metrics

- **Churn**: Lines added + deleted per file
- **Temporal Coupling**: Jaccard similarity of files that change together
  - 1.0 = files always change together
  - 0.0 = files never change together
- **Co-change Count**: Number of commits where files changed together
- **Code Age**: Days since last modification
- **Commit Frequency**: Commits per month per file

### Author Metrics

- **Total Commits**: Per author and per file
- **Lines Contributed**: Lines added by each author
- **Files Touched**: Unique files modified
- **Author Ownership**: Primary contributors per file

## Example Repositories

The project includes 3 synthetic test repositories:

1. **simple-linear**: Single author, linear history (baseline)
2. **multi-author**: Multiple authors with overlapping changes
3. **high-churn**: Demonstrates temporal coupling (models.py ↔ serializers.py)

## Architecture

### Dual Database Design

- **structure.db**: AST-parsed structural relationships across all supported languages
  - Language-agnostic core schema (modules, classes, functions, imports, calls, inheritance)
  - Language-specific extensions (decorators, type hints, generic parameters)
  - Tree-sitter based parsers for robust, error-tolerant parsing
- **history.db**: Git history analysis (commits, file changes, authors, temporal coupling)
  - 100% language-agnostic
  - Enables cross-language temporal coupling analysis

### Data Flow

```
Source Code (7 languages) → Tree-Sitter Parsers → structure.db
Git History → Git Analyzer → history.db
                ↓
        SQL Queries & Views → Metrics
                ↓
        Python API → CLI/Observable Framework
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests (when available)
pytest

# Code formatting
black depanalysis/
ruff check depanalysis/
```

## Observable Framework

**The `docs/` directory contains all visualization code** as an Observable Framework project.

**Structure**:
```
docs/
├── observablehq.config.js  # Configuration
├── package.json             # Dependencies
├── custom.css               # Styling
├── data/                    # Data loaders (Python scripts)
│   ├── repo-list.json.py
│   ├── churn.json.py
│   ├── coupling.json.py
│   └── authors.json.py
├── index.md                 # Landing page
├── repo/                    # Repository-specific pages
│   ├── high-churn.md
│   ├── multi-author.md
│   └── simple-linear.md
├── coupling.md              # Temporal coupling explorer
├── authors.md               # Author analytics
└── compare.md               # Cross-repo comparison
```

**Data Loaders**: Python scripts in `docs/data/` that query SQLite databases (`data/<repo>/*.db`) and export JSON for Observable pages to consume.

**Important**: Changes to visualizations often require coordinated updates:
1. Database schema changes in `depanalysis/db/` if new data is needed
2. Data loader scripts in `docs/data/` to query and export the data
3. Observable pages in `docs/` to render the visualizations

## License

ISC

## Contributing

Contributions welcome! The project has solid foundations with multi-language support and dual analysis (structural + temporal). Future enhancements include:
- Hotspot analysis (combining structural + temporal metrics)
- Circular dependency detection and visualization
- Enhanced type analysis (generics, macros, advanced features)
- GraphML export for external visualization tools
- Additional visualization dashboards
