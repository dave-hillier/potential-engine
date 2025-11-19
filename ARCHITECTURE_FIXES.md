# Architecture Fixes - Clean Phase Separation

## Problem

The codebase violated the intended **Parse → DB → Metrics → Visualization** flow described in CLAUDE.md. Features were disconnected and blurred across phases:

### Violations Identified

1. **cross_language_analyzer.py** (CRITICAL)
   - Reading source files with regex during "analysis" phase
   - Should capture API endpoints/calls during parse phase
   - Located at CLI lines 233-246 (wrong phase)

2. **ecosystem_analyzer.py** (MEDIUM)
   - Parsing manifest files during "analysis" phase
   - Should run during parse phase alongside source code parsers
   - Located at CLI lines 248-271 (wrong phase)

3. **docs/data/api-boundaries.json.py** (MINOR)
   - Business logic (pattern matching) in Observable data loader
   - Should be in MetricsAnalyzer with thin data loader

## Solution

### 1. Renamed & Clarified Components

#### cross_language_analyzer.py → APIBoundaryParser
- **Class**: `CrossLanguageAnalyzer` → `APIBoundaryParser` (alias kept for compatibility)
- **Method**: `analyze()` → `parse()` (analyze() deprecated but kept)
- **Phase**: Now explicitly PARSE PHASE component
- **Purpose**: Extracts API endpoints, calls, and shared types → writes to structure.db
- **Documentation**: Clear docstrings marking it as a parser, not analyzer

#### ecosystem_analyzer.py → ManifestParser
- **Class**: `EcosystemAnalyzer` → `ManifestParser` (alias kept for compatibility)
- **Method**: `analyze()` → `parse()` (analyze() deprecated but kept)
- **Phase**: Now explicitly PARSE PHASE component
- **Purpose**: Extracts dependencies from manifest files → writes to structure.db
- **Documentation**: Clear docstrings marking it as a parser

### 2. Extracted Business Logic from Visualization Layer

#### MetricsAnalyzer.get_api_boundary_matches()
- **Location**: `depanalysis/metrics.py` (new method)
- **Purpose**: Pattern matching between API calls and endpoints
- **Returns**: Dictionary with matched/unmatched boundaries and summary

#### docs/data/api-boundaries.json.py
- **Before**: 100+ lines with SQL queries + pattern matching logic
- **After**: 40 lines - thin wrapper around MetricsAnalyzer
- **Change**: Delegates all business logic to metrics layer

### 3. Updated CLI with Clear Phase Separation

#### CLI Flow (depanalysis/cli.py)
```
PARSE PHASE: Extract data → Write to DBs
├── 1. Parse Git History → history.db
└── 2. Parse Source Code → structure.db
    ├── 2a. Python Parser (tree-sitter)
    ├── 2b. TypeScript Parser (tree-sitter)
    ├── 2c. JavaScript Parser (tree-sitter)
    ├── 2d. C# Parser (tree-sitter)
    ├── 2e. Java Parser (tree-sitter)
    ├── 2f. Rust Parser (tree-sitter)
    ├── 2g. C++ Parser (tree-sitter)
    ├── 2h. Go Parser (tree-sitter)
    ├── 2i. API Boundary Parser  ← MOVED HERE
    └── 2j. Manifest Parser      ← MOVED HERE

METRICS PHASE: Query DBs → Calculate metrics
├── MetricsAnalyzer methods
└── SQL views and queries

VISUALIZATION PHASE: Export JSON → Observable
├── Thin data loaders in docs/data/
└── Observable pages in docs/
```

## Architecture Compliance

### Clean Separation of Concerns

| Component | Phase | Responsibility |
|-----------|-------|----------------|
| **Parsers** | Parse | Read files → Extract data → Write to DB |
| **MetricsAnalyzer** | Metrics | Query DB → Calculate metrics → Return results |
| **Data Loaders** | Viz | Call MetricsAnalyzer → Export JSON |
| **Observable** | Viz | Load JSON → Render visualizations |

### Data Flow

```
Source Files + Git History
    ↓ (parsers extract)
SQLite Databases (structure.db, history.db)
    ↓ (MetricsAnalyzer queries)
Metrics (DataFrame, Dict, etc.)
    ↓ (data loaders export)
JSON Files
    ↓ (Observable renders)
Web Visualizations
```

## Benefits

1. **Single Responsibility**: Each component has one clear job
2. **Testability**: Can test parsers, metrics, and viz independently
3. **Performance**: Parse once, query many times
4. **Maintainability**: Clear boundaries make debugging easier
5. **Scalability**: Can optimize each phase separately

## Backward Compatibility

- All old class names kept as aliases (`CrossLanguageAnalyzer`, `EcosystemAnalyzer`)
- All old methods kept as deprecated wrappers (`analyze()` calls `parse()`)
- Existing code continues to work without changes
- Deprecation warnings in docstrings guide future refactoring

## Files Modified

1. `depanalysis/cross_language_analyzer.py` - Renamed class, added parse() method
2. `depanalysis/ecosystem_analyzer.py` - Renamed class, added parse() method
3. `depanalysis/metrics.py` - Added get_api_boundary_matches() method
4. `docs/data/api-boundaries.json.py` - Simplified to thin data loader
5. `depanalysis/cli.py` - Reorganized with clear phase comments

## Testing

The changes maintain backward compatibility, so existing functionality should work unchanged.
To test the architectural improvements:

```bash
# Parse a repository (should work as before)
depanalysis analyze-repo /path/to/repo

# Query metrics (now uses clean MetricsAnalyzer)
depanalysis show-metrics <repo>

# View visualizations (data loaders now use MetricsAnalyzer)
cd docs && npm run dev
```

## Future Improvements

1. **Tree-sitter Integration**: Move API endpoint/call detection into Python/TypeScript parsers
2. **Remove Regex Parsing**: Replace regex-based parsing with proper AST analysis
3. **SQL Views**: Consider pre-computing API boundary matches in SQL views
4. **Deprecation Cleanup**: Remove deprecated `analyze()` methods and old class names in next major version
