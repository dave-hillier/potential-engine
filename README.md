# depanalysis

Python dependency and Git history analyzer combining static structural analysis with temporal behavioral analysis to identify architectural issues, coupling problems, and maintenance hotspots.

## Features

- **Git History Analysis**: Extract commits, file changes, and temporal coupling metrics
- **Temporal Coupling Detection**: Identify files that frequently change together using Jaccard similarity
- **Author Analytics**: Track contributor patterns and code ownership
- **Churn Metrics**: Measure frequency and magnitude of changes
- **Interactive Reports**: Observable Framework dashboards with visualizations
- **Multi-Repository Support**: Analyze multiple repositories with cross-repo comparisons

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

View analysis results in an interactive web dashboard using Observable Framework:

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

## Data Storage

Analysis data is stored in SQLite databases:

```
data/
├── <repo_name>/
│   ├── structure.db  # AST-parsed structural relationships (future)
│   └── history.db    # Git history and temporal coupling
```

Each repository has its own separate databases, enabling:
- Independent analysis per repository
- Cross-repository comparisons via in-memory joins
- Efficient incremental updates

## Key Metrics

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

- **structure.db**: AST-parsed structural relationships (future)
- **history.db**: Git history analysis (implemented)

### Data Flow

```
Git History → Git Analyzer → history.db → Python API → CLI/Reports
                                        ↓
                                   Observable Framework
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

The `docs/` directory contains an Observable Framework project for interactive reports.

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

**Data Loaders**: Python scripts that query SQLite databases and export JSON for Observable to consume.

## License

ISC

## Contributing

Contributions welcome! This is an early-stage project focused on Git history analysis. Future additions include:
- AST parser for Python structural analysis
- Additional language support (TypeScript, C#, Java, etc.)
- Combined structural + temporal metrics (hotspots)
- Circular dependency detection
- More visualization options
