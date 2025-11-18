# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A multi-language dependency analysis tool that combines static structural analysis (AST parsing) with temporal behavioral analysis (Git history) to identify architectural issues, coupling problems, and maintenance hotspots. Inspired by NDepend for .NET.

**Language Support**: The tool uses a language-agnostic core architecture supporting Python, TypeScript, JavaScript, C#, Java, Rust, C++, and Go. The initial MVP focuses on Python parser implementation, but the schema and architecture support polyglot repositories from the ground up.

## Current Implementation Status

### ✅ Implemented (MVP)
- **Git History Analyzer**: Full implementation extracting commits, authors, file changes
- **Temporal Coupling**: Jaccard similarity calculation for files that change together
- **Churn Metrics**: File-level change frequency and magnitude tracking
- **Author Analytics**: Contribution patterns and code ownership statistics
- **CLI Tool**: Complete command-line interface for analysis and reporting
- **Multi-Repository Support**: Separate databases per repo with cross-repo comparison
- **Observable Framework Reports**: Interactive web dashboards with visualizations
- **Data Export**: CSV and JSON export capabilities

### 🚧 Planned (Future)
- **AST Parser**: Python structural analysis (modules, classes, functions, imports)
- **Structural Metrics**: Afferent/efferent coupling, instability, complexity
- **Combined Metrics**: Hotspots (structural + temporal analysis)
- **Circular Dependency Detection**: Graph algorithms for cycle detection
- **Additional Languages**: TypeScript, C#, Java parsers
- **GraphML Export**: For external visualization tools

## Architecture

### Dual Database Design

The tool uses two separate SQLite databases as the primary data store:

- **structure.db**: Contains AST-parsed structural relationships across all supported languages
  - Language-agnostic core: modules, classes, functions, imports, calls, inheritance
  - Language-specific extensions: decorators, type hints, generic parameters, metadata
  - Supports: Python, TypeScript, JavaScript, C#, Java, Rust, C++, Go
- **history.db**: Contains Git history analysis (commits, file changes, authors, temporal coupling)
  - 100% language-agnostic - works for any programming language
  - Enables cross-language temporal coupling analysis

These databases are the source of truth, not caches. Analysis is performed via SQL queries, materialized views, and Python only when SQL is insufficient (e.g., cycle detection).

### Core Components

1. **Parser Component**: Language-specific parsers write to language-agnostic schema in structure.db
   - **Language Detection**: File extension-based (.py, .ts, .cs, .java, .rs, .cpp, .go)
   - **Python Parser (MVP)**: Parses Python AST and writes to structure.db
     - Captures all relationships during initial parse (imports, calls, inheritance, decorators, type hints)
     - Uses file hash tracking for incremental updates
     - Only reparses files that have changed
   - **Future Parsers**: TypeScript, C#, Java, Rust, C++, Go
     - Each writes to same core schema (modules, classes, functions, dependencies)
     - Language-specific features stored in extension tables

2. **Git Analyzer Component**: Processes repository history and writes to history.db
   - Extracts temporal coupling (files that change together)
   - Tracks churn, author patterns, code age

3. **Analysis Engine**:
   - Primary analysis via SQL queries and views
   - Joins between structure.db and history.db for combined metrics
   - Python implementations for graph algorithms (cycle detection, path traversal)
   - Loads data into memory only when SQL cannot efficiently solve the problem

### Data Flow

```
Python Source → AST Parser → structure.db
Git History → Git Analyzer → history.db
Both DBs → SQL Queries/Views → Metrics
Both DBs → Python (when needed) → Complex Algorithms
Both DBs → Observable/API → Visualization
```

## Key Design Principles

### Capture Everything During Parse

When parsing AST, capture ALL relationships (imports, calls, inheritance, decorators, type hints, etc.). Parsing is expensive - skipping relationships now would require reparsing later.

### SQLite as Primary Store

SQLite is performant enough to be the primary data store for all analysis. With proper indexing and materialized views, it handles read-heavy analytical queries efficiently. This eliminates complexity of maintaining separate in-memory and persistent representations.

### SQL First, Python When Needed

Most metrics can be calculated via SQL queries and materialized views. Use Python for:
- Graph algorithms that SQL handles poorly (cycle detection, transitive closure)
- Complex algorithms requiring sophisticated data structures
- Integration with external libraries (Pandas for tabular output)

### Separate Structure from Behavior

Structure (how code is organized) and behavior (how it changes) are fundamentally different:
- structure.db updates when files change
- history.db grows with every commit
- Independent updates allow efficient incremental processing
- Combined analysis reveals insights neither provides alone (e.g., hotspots = high complexity + high coupling + high churn)

## Key Metrics

### Structural Metrics
- **Afferent Coupling (Ca)**: Incoming dependencies to a module
- **Efferent Coupling (Ce)**: Outgoing dependencies from a module
- **Instability**: Ce / (Ca + Ce)
- **Cyclomatic Complexity**: Independent paths through code
- **Transitive Dependencies**: Full dependency closure

### Temporal Metrics
- **Churn**: Change frequency and magnitude
- **Temporal Coupling**: Files that change together (calculated via Jaccard similarity on commit sets)
- **Hidden Dependencies**: Temporal coupling without structural dependency

### Combined Metrics
- **Hotspots**: High complexity × high coupling × high churn
- **Risk Score**: Combined metric for release risk assessment

## Similarity Analysis

Use **Jaccard similarity** for comparing sets:
- Import patterns: `|A ∩ B| / |A ∪ B|` where A, B are sets of imports
- Temporal patterns: Similarity based on commit sets
- Module clustering: Group modules with similar dependency patterns

## Performance Optimizations

### Incremental Updates
- Track file hashes to avoid reparsing unchanged files
- Only process new commits for history.db
- Materialized views for expensive calculations

### SQLite Optimization
- Appropriate indexes on frequently queried columns
- WAL mode for concurrent reads during updates
- Run ANALYZE to keep query planner statistics current
- Materialized views for complex aggregations

## Language-Specific Considerations

### Python Challenges
**Import Resolution**: Handle Python's dynamic import mechanisms:
- Dynamic imports (`importlib`, `__import__`)
- Conditional imports
- Relative imports
- Package vs module imports
- Namespace packages

Best effort tracking - capture what's statically analyzable, flag dynamic imports for manual review.

### TypeScript/JavaScript Challenges
- Multiple module systems (ES6, CommonJS, AMD)
- Declaration files (.d.ts)
- Dynamic imports and requires
- Build artifact vs source code distinction

### Other Language Considerations
- **C#**: Partial classes, LINQ expressions, async patterns
- **Java**: Inner classes, generics type erasure, package structure
- **Rust**: Lifetimes, macros, trait implementations
- **C++**: Header/source pairs, templates, preprocessor
- **Go**: Package structure, interface implementation

### Cross-Language Dependencies
- API boundaries (REST, gRPC, GraphQL)
- FFI/Interop calls (Python ↔ C++, C# ↔ native)
- Shared type definitions (Protocol Buffers, JSON schemas)

## Export and Visualization

### Export Formats
- **JSON**: Programmatic access for tools
- **CSV**: Spreadsheet analysis (via `--export-csv` flag)
- **GraphML**: External graph visualization tools (future)
- **SQLite**: Portable database files

### Visualization

**All visualization code lives in the `docs/` directory**. The visualization layer consists of three coupled components:

1. **Database schemas** (`data/<repo>/*.db`) - Source of truth for all metrics
2. **Data loader scripts** (`docs/data/*.py`) - Python scripts that query databases and export JSON
3. **Observable pages** (`docs/*.md`) - Web UI that renders the data

**Important**: Changes to visualizations often require coordinated updates across all three layers. For example, adding a new metric requires:
- Database schema changes (if not already captured)
- New or updated data loader scripts to query and export the metric
- Observable page updates to display the visualization

**Python API**: Thin wrapper over SQLite, returns dicts/sets/lists or Pandas DataFrames

**Observable Framework** (implemented): Interactive web-based dashboards
  - Development: `cd docs && npm run dev` → http://localhost:3000
  - Build: `cd docs && npm run build` → static site in `dist/`
  - Data loaders: Python scripts in `docs/data/` export JSON for Observable pages

**Jupyter/Marimo**: Integration via Python API (future)

### Observable Framework Implementation

**Location**: All visualization code is in the `docs/` directory.

**Commands**:
```bash
cd docs
npm install          # First time setup
npm run dev          # Development server
npm run build        # Build static site
npm run deploy       # Deploy to Observable
```

**Pages** (in `docs/`):
- `/` (`index.md`) - Landing page with repository overview
- `/repo/{name}` - Individual repository dashboards (high-churn, multi-author, simple-linear)
- `/coupling` (`coupling.md`) - Temporal coupling network visualization (D3 force-directed graph)
- `/authors` (`authors.md`) - Author analytics and contribution patterns
- `/compare` (`compare.md`) - Cross-repository comparison

**Data Loaders** (`docs/data/*.py`):
- `repo-list.json.py` - List all analyzed repositories
- `all-repos-summary.json.py` - Summary stats for all repos
- `churn.json.py <repo>` - File churn metrics
- `coupling.json.py <repo>` - Temporal coupling data
- `authors.json.py <repo>` - Author statistics

Data loaders are Python scripts that query SQLite databases (`data/<repo>/*.db`) and output JSON, executed by Observable Framework during page rendering.

**Visualization Update Workflow**:
When adding new visualizations or metrics, coordinate changes across:
1. Database schema (if needed) in `depanalysis/db/schema.sql`
2. Data loader scripts in `docs/data/` to extract and format data
3. Observable pages in `docs/` to display the visualization

## Data Models

### structure.db Schema

**Language-Agnostic Core**:
- **languages**: Registry of supported languages (python, typescript, csharp, java, rust, cpp, go)
- **modules**: Source files with language_id foreign key
- **classes**: Type definitions (classes, interfaces, structs, traits, enums) with kind field
- **functions**: Callable units with kind field (function, method, constructor, lambda, async_function)
- **variables**: Data entities with kind field (field, property, constant, local, parameter)

**Universal Relationships**:
- **imports**: Dependencies with import_kind (import, require, using, include, use)
- **calls**: Function invocations with call_kind
- **inheritance**: Type relationships with relationship_kind (inherits, implements, extends, trait_impl)

**Language-Specific Extensions**:
- **decorators**: Python decorators, TypeScript decorators, C# attributes, Java annotations
- **type_hints**: Type annotations across languages
- **generic_parameters**: Parameterized types (TypeScript, C#, Java, C++, Rust)
- **language_metadata**: Flexible key-value storage (Rust lifetimes, Python metaclasses, etc.)

All relationship tables have appropriate foreign keys and indexes.

### history.db Schema

Core entities: commits, file_changes, authors

Derived data: temporal_coupling (pairwise co-change frequencies), author_ownership, churn_metrics

**Note**: history.db is 100% language-agnostic and unchanged from original design.

## Out of Scope (MVP)

- Advanced graph libraries (NetworkX) - implement algorithms directly
- Type inference beyond AST (use libraries like astroid if needed later)
- CI/CD integration
- Real-time monitoring
