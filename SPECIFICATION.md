# Multi-Language Dependency Analysis Tool Specification

## 1. Overview

A comprehensive codebase analysis tool that combines static structural analysis with temporal/behavioral analysis from version control history. The tool identifies architectural issues, coupling problems, and maintenance hotspots by analyzing both how code is structured and how it changes over time.

**Multi-Language Support**: The tool is designed with a language-agnostic core architecture supporting Python, TypeScript, JavaScript, C#, Java, Rust, C++, and Go. The initial MVP implementation focuses on Python parsing, but the database schema and analysis engine support multiple languages.

### 1.1 Inspiration

The design is inspired by NDepend for .NET, adapting its core concepts for multiple programming languages while maintaining a unified analysis framework for polyglot repositories.

### 1.2 Key Differentiators

- Dual analysis approach: static structure (AST) and temporal behavior (Git)
- SQLite as primary data store for all analysis
- Direct SQL queries for metrics and exploration
- Interactive exploration via Observable notebooks
- Focus on actionable metrics for release risk assessment

### 1.3 MVP Scope

**Implementation Approach:**
- Language-agnostic SQLite schema supporting multiple languages
- Python parser as initial implementation (AST-based)
- Git history analysis (language-agnostic)
- SQLite as primary data store (not a cache - it's the source of truth)
- Metrics and analysis via SQL queries and views
- Load subsets into memory only when needed for complex algorithms
- Observable notebooks for visualization and exploration

**Rationale:**
SQLite is performant enough to be the primary data store. The entire dependency graph fits in memory, so SQLite with proper indexing provides fast queries. This eliminates the complexity of maintaining separate in-memory and persistent representations.

**Multi-Language Architecture:**
- Language-agnostic core schema (modules, classes, functions, dependencies)
- Language-specific extension tables for unique features (e.g., Python decorators, Rust lifetimes)
- Parser abstraction layer allows adding new language support without schema changes
- Initial implementation: Python parser only
- Future expansion: TypeScript, C#, Java, Rust, C++, Go parsers

**Out of Scope (for initial release):**
- CI/CD integration and automated workflows
- Non-Python parser implementations (schema supports them, but parsers not implemented)

## 2. Architecture

### 2.1 Core Components

#### 2.1.1 Parser Component
- Language detection via file extension and content heuristics
- Pluggable parser architecture supporting multiple languages
- **Python Parser (MVP)**: Extracts structural information from Python AST
  - Identifies modules, classes, functions, and their relationships
  - Calculates code complexity metrics
  - Handles Python-specific constructs (decorators, metaclasses, dynamic imports)
- **Future Parsers**: TypeScript, C#, Java, Rust, C++, Go
  - Each parser writes to the same language-agnostic core schema
  - Language-specific features captured in extension tables
  - Consistent metrics across all languages (complexity, coupling, etc.)

#### 2.1.2 Git Analyzer Component
- Processes repository history
- Extracts change patterns and frequencies
- Identifies temporal coupling between files
- Tracks code churn and author patterns

#### 2.1.3 Analysis Engine
- SQL queries and views for metrics calculation
- Joins between structure.db and history.db for combined analysis
- Python implementations of graph algorithms (cycle detection, path traversal)
- In-memory processing only for algorithms that require it (e.g., cycle detection)

#### 2.1.4 Storage Layer
- Dual SQLite database architecture (structure.db + history.db)
- SQLite as primary data store (not a cache layer)
- Optimized with indexes for read-heavy analytical queries
- File hash tracking for incremental updates

### 2.2 Data Architecture

#### 2.2.1 Separation of Concerns
- **structure.db**: Static code analysis results
- **history.db**: Version control analysis results
- Independent schemas allow for separate updates and queries
- Combined analysis via SQL joins or Python when needed

#### 2.2.2 Storage Strategy
- Parse directly into SQLite (structure.db and history.db)
- Incremental updates via file hash tracking (only reparse changed files)
- Analysis via SQL queries and materialized views
- Load into Python data structures only when SQL is insufficient

## 3. Feature Set

### 3.1 Structural Analysis

#### 3.1.1 Dependency Metrics
- Afferent coupling (incoming dependencies)
- Efferent coupling (outgoing dependencies)
- Instability metric (Ce / (Ca + Ce))
- Abstractness (ratio of abstract to concrete classes)
- Distance from main sequence
- Transitive dependency depth

#### 3.1.2 Complexity Metrics
- Cyclomatic complexity
- Nesting depth
- Lines of code (LOC, SLOC)
- Number of methods/classes per module
- Method/function length

#### 3.1.3 Architectural Analysis
- Cycle detection in import graphs
- Transitive dependency calculation
- God class/module identification (high complexity + high coupling)
- Module clustering by dependency patterns
- Layering analysis (identify unintended cross-layer dependencies)

### 3.2 Temporal Analysis

#### 3.2.1 Change Metrics
- File change frequency (churn)
- Lines added/deleted over time
- Change burst detection
- Code age analysis

#### 3.2.2 Coupling Analysis
- Temporal coupling (files that change together)
- Hidden dependencies (temporal coupling without structural dependency)
- Author ownership patterns

#### 3.2.3 Hotspot Identification
- High complexity + high churn areas
- Frequently modified + highly coupled modules
- Combined risk scoring (complexity × coupling × churn)

### 3.3 Similarity Analysis

#### 3.3.1 Dependency Pattern Similarity
- Jaccard similarity for import patterns
- Identification of modules with similar dependencies
- Clustering modules into architectural groups

#### 3.3.2 Temporal Pattern Similarity
- Modules with similar change patterns
- Jaccard similarity on commit sets

### 3.4 Query Capabilities

#### 3.4.1 Ad-hoc SQL Queries
- Direct access to underlying SQLite databases
- Custom metric calculations
- Export capabilities

#### 3.4.2 Pre-defined Analyses
- Common anti-pattern detection
- Release risk assessment
- Refactoring candidate identification

### 3.5 Visualization and Exploration

#### 3.5.1 Python API
- Thin wrapper over SQLite queries
- Helper methods for common analyses
- Returns standard Python types (dicts, sets, lists) or Pandas DataFrames
- Integration with Jupyter/Marimo notebooks

#### 3.5.2 Observable Notebooks
- Interactive web-based exploration
- SQLite integration via sql.js
- Custom dependency graph visualizations
- Force-directed layouts for module relationships
- Filtering and drill-down capabilities
- Shareable published dashboards

#### 3.5.3 Export Formats
- JSON for programmatic access
- CSV for spreadsheet analysis
- GraphML for external graph tools
- SQLite databases as portable artifacts

## 4. Data Models

### 4.1 Structural Data Model

#### Core Entities (Language-Agnostic)
- **Languages**: Registry of supported programming languages
- **Modules**: Source files with their paths, language, and metadata
- **Classes**: Type definitions (classes, interfaces, structs, traits, enums) with location and metrics
  - Supports: Python classes, TypeScript interfaces, C# classes/structs, Java interfaces, Rust structs/traits
- **Functions**: Callable units (functions, methods, constructors) with complexity metrics
  - Includes kind differentiation: function, method, constructor, lambda, async_function, etc.
- **Variables**: Data entities (fields, properties, constants, locals) with scope information

#### Relationships (Language-Agnostic)
- **Imports**: Module-to-module dependencies
  - Maps to: Python import, TypeScript import, C# using, Java import, Rust use, C++ include
  - Supports: relative imports, dynamic imports, wildcard imports
- **Calls**: Function-to-function invocations (best effort static analysis)
- **Inheritance**: Type hierarchy relationships
  - Maps to: Python inheritance, TypeScript extends/implements, C# base classes, Java extends/implements, Rust trait implementation
- **Contains**: Structural containment (module→class→function)

#### Language-Specific Features
- **Decorators/Annotations**: Python decorators, TypeScript decorators, C# attributes, Java annotations
- **Type Hints**: Type annotations across languages (Python type hints, TypeScript types, etc.)
- **Generic Parameters**: Parameterized types for TypeScript, C#, Java, C++, Rust
- **Language Metadata**: Flexible key-value storage for unique features (Rust lifetimes, Python metaclasses, etc.)

### 4.2 Temporal Data Model

#### Core Entities
- **Commits**: Repository commits with metadata
- **File Changes**: Files modified in each commit
- **Authors**: Developer information

#### Derived Data
- **Temporal Coupling**: Pairwise co-change frequencies
- **Author Ownership**: Primary contributors per module
- **Churn Metrics**: Aggregated change statistics per file

## 5. Implementation Considerations

### 5.1 Performance Optimizations

#### 5.1.1 Incremental Processing
- File hash tracking to avoid re-parsing unchanged files
- Incremental Git history updates (only process new commits)
- Materialized views for expensive metric calculations

#### 5.1.2 SQLite Optimization
- Appropriate indexes on frequently queried columns
- WAL mode for concurrent reads during updates
- Analyze command to keep query planner statistics current
- Materialized views for complex aggregations

### 5.2 Language-Specific Considerations

#### 5.2.1 Language Detection
- File extension-based detection (.py, .ts, .cs, .java, .rs, .cpp, .go)
- Shebang parsing for extensionless scripts
- Content-based heuristics as fallback
- Configuration overrides for ambiguous cases

#### 5.2.2 Python Challenges
- **Dynamic Nature**: Handling dynamic imports, runtime code generation, conditional imports
- **Import Resolution**: Package vs module imports, relative imports, namespace packages
- **Metaclasses**: Tracking metaclass usage and its impact on class structure
- **Decorators**: Capturing decorator chains and their effects

#### 5.2.3 TypeScript/JavaScript Challenges
- **Module Systems**: ES6 modules, CommonJS, AMD, UMD
- **Type Definitions**: .d.ts declaration files, DefinitelyTyped integration
- **Dynamic Imports**: import() expressions, require() calls
- **Build Artifacts**: Distinguishing source from generated code

#### 5.2.4 C# Challenges
- **Project Structure**: Solution/project file parsing for module boundaries
- **Partial Classes**: Tracking classes split across multiple files
- **LINQ**: Capturing complex query expressions
- **Async Patterns**: Task-based asynchrony tracking

#### 5.2.5 Java Challenges
- **Package Structure**: Aligning file system with package declarations
- **Inner Classes**: Nested and anonymous class relationships
- **Generics**: Type erasure implications for analysis
- **Build Systems**: Maven/Gradle integration for dependency resolution

#### 5.2.6 Rust Challenges
- **Ownership Semantics**: Tracking lifetime annotations and borrow relationships
- **Macros**: Procedural and declarative macro expansion
- **Traits**: Trait implementation and bounds
- **Cargo Integration**: Workspace and crate structure

#### 5.2.7 C++ Challenges
- **Header/Source Split**: Pairing .h/.hpp files with .cpp/.cc files
- **Templates**: Template instantiation and specialization
- **Preprocessor**: Macro expansion and conditional compilation
- **Build Complexity**: CMake/Make integration for include paths

#### 5.2.8 Cross-Language Dependencies
- **API Boundaries**: REST endpoints, gRPC services, GraphQL schemas
- **FFI/Interop**: Python calling C++, C# using native libraries, etc.
- **Build System Integration**: Tracking cross-language build dependencies
- **Shared Types**: Protocol buffers, JSON schemas, OpenAPI definitions

### 5.3 Design for Extension

#### 5.3.1 Modular Architecture
- Clear separation between parsing, storage, and analysis
- Well-defined interfaces for each component
- Extensible relationship types via schema updates

#### 5.3.2 Data Accessibility
- SQLite databases are directly queryable
- Standard export formats for tool integration
- Python API provides programmatic access
- Observable notebooks are customizable

## 6. Use Cases

### 6.1 Release Risk Assessment
- Identify high-risk changes before deployment
- Assess impact radius of modifications
- Predict potential breaking changes
- Track cross-language boundary risks (frontend + backend changes)

### 6.2 Technical Debt Management
- Locate maintenance hotspots across all languages
- Prioritize refactoring efforts based on combined metrics
- Track debt accumulation over time
- Identify language-specific anti-patterns

### 6.3 Architecture Governance
- Enforce dependency rules within and across languages
- Detect architectural drift in polyglot systems
- Validate intended vs actual structure
- Monitor API boundary changes

### 6.4 Code Review Support
- Highlight files that typically change together (even across languages)
- Identify missing test coverage for hotspots
- Suggest additional reviewers based on coupling
- Flag cross-language breaking changes

### 6.5 Onboarding Assistance
- Identify core modules and their relationships
- Show module ownership patterns
- Highlight frequently changing areas
- Provide language-specific codebase statistics

### 6.6 Polyglot Repository Analysis
- **Cross-Language Coupling**: Identify temporal coupling between frontend and backend
- **Language Distribution**: Track codebase composition and growth by language
- **Boundary Analysis**: Analyze API contracts and cross-language dependencies
- **Hotspot Detection**: Find problematic areas regardless of language
- **Unified Metrics**: Compare complexity and coupling across language boundaries

## 7. Non-Functional Requirements

### 7.1 Performance
- Analysis of 10,000 file codebase in under 1 minute
- Incremental updates in seconds
- Interactive query response times

### 7.2 Scalability
- Support for codebases up to 100,000 files
- Efficient memory usage (under 1GB for typical projects)
- Parallel processing where applicable

### 7.3 Usability
- Python API for programmatic access
- Observable notebooks for visual exploration
- Clear, actionable metric outputs
- Exportable results in standard formats

### 7.4 Portability
- Pure Python implementation
- Minimal external dependencies
- Cross-platform compatibility

## 8. Success Criteria

### 8.1 Accuracy
- Correct identification of all import relationships
- Accurate complexity calculations
- Reliable cycle detection

### 8.2 Actionability
- Clear identification of problem areas
- Prioritized issue lists
- Concrete refactoring suggestions

### 8.3 Usability
- Intuitive Python API
- Clear visualization of complex relationships
- Actionable insights from combined metrics

## 9. Glossary

- **Afferent Coupling (Ca)**: Number of modules that depend on a given module
- **Efferent Coupling (Ce)**: Number of modules that a given module depends on
- **Instability**: Ratio of efferent coupling to total coupling (Ce/(Ca+Ce))
- **Temporal Coupling**: Modules that frequently change together in commits
- **Hotspot**: Code area with high complexity, high churn, and high coupling
- **Churn**: Frequency and magnitude of changes to a file
- **Cyclomatic Complexity**: Number of linearly independent paths through code
- **God Class**: Class with excessive responsibilities and dependencies
- **Hidden Dependency**: Temporal coupling without structural dependency
- **Jaccard Similarity**: Measure of set similarity calculated as intersection size divided by union size
- **AST**: Abstract Syntax Tree, a tree representation of source code structure
- **Observable**: JavaScript-based notebook environment for interactive data visualization