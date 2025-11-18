# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python dependency analysis tool that combines static structural analysis (AST parsing) with temporal behavioral analysis (Git history) to identify architectural issues, coupling problems, and maintenance hotspots. Inspired by NDepend for .NET.

## Architecture

### Dual Database Design

The tool uses two separate SQLite databases as the primary data store:

- **structure.db**: Contains AST-parsed structural relationships (modules, classes, functions, imports, calls, inheritance, decorators, type hints)
- **history.db**: Contains Git history analysis (commits, file changes, authors, temporal coupling)

These databases are the source of truth, not caches. Analysis is performed via SQL queries, materialized views, and Python only when SQL is insufficient (e.g., cycle detection).

### Core Components

1. **Parser Component**: Parses Python AST and writes directly to structure.db
   - Captures all relationships during initial parse (imports, calls, inheritance, decorators, type hints)
   - Uses file hash tracking for incremental updates
   - Only reparses files that have changed

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

## Python-Specific Challenges

### Import Resolution
Handle Python's dynamic import mechanisms:
- Dynamic imports (`importlib`, `__import__`)
- Conditional imports
- Relative imports
- Package vs module imports
- Namespace packages

Best effort tracking - capture what's statically analyzable, flag dynamic imports for manual review.

## Export and Visualization

### Export Formats
- **JSON**: Programmatic access for tools
- **CSV**: Spreadsheet analysis
- **GraphML**: External graph visualization tools
- **SQLite**: Portable database files

### Visualization
- **Python API**: Thin wrapper over SQLite, returns dicts/sets/lists or Pandas DataFrames
- **Observable Notebooks**: Interactive web-based exploration via sql.js
- **Jupyter/Marimo**: Integration via Python API

## Data Models

### structure.db Schema

Core entities: modules, classes, functions, variables

Relationships: imports, calls, inheritance, contains, decorates, type_hints

All relationship tables should have appropriate foreign keys and indexes.

### history.db Schema

Core entities: commits, file_changes, authors

Derived data: temporal_coupling (pairwise co-change frequencies), author_ownership, churn_metrics

## Out of Scope (MVP)

- Advanced graph libraries (NetworkX) - implement algorithms directly
- Type inference beyond AST (use libraries like astroid if needed later)
- CI/CD integration
- Real-time monitoring
