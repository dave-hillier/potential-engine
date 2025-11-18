# Feature Roadmap & Architecture Extrapolation

This document outlines the potential evolution of the dependency analysis tool, extrapolating from the current foundation to explore what this architecture enables.

## Current Foundation (Implemented)

The tool has achieved impressive progress in 2-3 weeks:

- **Complete Git History Analysis** (history.db) - Temporal coupling, churn metrics, author analytics
- **Python AST Parser** (structure.db) - Modules, classes, functions, imports, complexity
- **Language-Agnostic Schema** - Ready for polyglot repositories (8 languages supported)
- **Observable Framework Visualizations** - Interactive dependency matrix, coupling graphs, author dashboards
- **Comprehensive Test Suite** - 1,099+ lines of tests with edge cases
- **CLI Tool** - Multi-repository management with CSV/JSON export

**Architecture Strengths:**
- Dual database design (structure + history) enables powerful cross-analysis
- SQLite as primary store (not cache) - fast, portable, SQL-queryable
- Clean separation of concerns with excellent test coverage
- Foundation is enterprise-grade quality

---

## Tier 1: Completing the Foundation
*Natural next steps that leverage existing architecture*

### 1. Full Relationship Graph Extraction

**Current Gap:** Python parser only captures imports, classes, functions - missing calls, inheritance, decorators, type hints, variables.

**Opportunity:**
- Extract function calls → Enable call graph analysis, dead code detection, API usage patterns
- Track inheritance chains → Find God classes, detect Liskov Substitution violations
- Parse decorators → Track framework usage (Flask routes, pytest fixtures), cross-cutting concerns
- Capture type hints → Type coverage metrics, migration tracking (untyped → typed)
- Extract class fields/properties → Data dependency analysis, anemic domain models

**Impact:** Transforms from "what imports what" to "complete code knowledge graph"

**Implementation:** Add AST visitors in `structure_analyzer.py` for:
- `visit_Call()` for function invocations
- `ClassDef.bases` for inheritance
- `FunctionDef.decorator_list` for decorators
- `arg.annotation` and `returns` for type hints
- `AnnAssign` and `Assign` for class fields

### 2. Structural + Temporal Fusion Metrics

**Opportunity:** Combine both databases for powerful insights:

**Hotspot Detection** = High Complexity × High Coupling × High Churn
- Identify top 5 maintenance burden files
- Prioritize refactoring with data-driven approach

**Hidden Dependencies** = Temporal Coupling WITHOUT Structural Coupling
- Files that change together but don't import each other
- Reveals missing abstractions, feature entanglement

**Architectural Drift** = Decreasing Stability Over Time
- Track instability metric changes commit-by-commit
- Detect when modules become less stable

**Ownership Risk** = Single Author × High Churn × Many Dependents
- Find "truck factor" bottlenecks
- Identify knowledge silos

**Impact:** From descriptive metrics → prescriptive recommendations

**Implementation:**
- SQL query joining structure.db and history.db
- New materialized views for combined metrics
- Observable visualization for hotspot dashboard

### 3. Circular Dependency Detection & Analysis

**Opportunity:**
- Find all cycles using Tarjan's algorithm or DFS
- Rank cycles by severity (length, file count, centrality)
- Visualize cycles in dependency matrix (highlight loop-creating cells)
- Suggest breaking points (identify weakest links)

**Impact:** Actionable architectural cleanup roadmap

**Implementation:**
- Python graph algorithm in `metrics.py`
- Load import graph from structure.db into networkx or custom graph
- Return cycle paths with metadata (file paths, cycle length)

---

## Tier 2: Polyglot Repository Support
*Leveraging language-agnostic schema*

### 4. TypeScript/JavaScript Parser

**Opportunity:** Schema already supports 8 languages - prove polyglot architecture with TypeScript:
- Parse `.ts`, `.tsx`, `.js`, `.jsx` files
- Handle ES6 imports, CommonJS requires, dynamic imports
- Extract React component dependencies (props, hooks, context)
- Track build artifacts vs source code (`.d.ts` declarations)

**Impact:** Analyze modern full-stack codebases (Python backend + TypeScript frontend)

**Implementation:**
- New `typescript_analyzer.py` using TypeScript AST parser library
- Write to same structure.db schema with `language_id = 'typescript'`
- Handle module resolution (node_modules, path aliases)

### 5. Cross-Language Dependency Tracking

**Opportunity:** With multiple parsers, detect:
- **API boundaries:** Python Flask routes called by TypeScript `fetch()`
- **Shared types:** Protocol Buffer definitions used in Go + Python
- **Monorepo analysis:** Nx/Turborepo with mixed languages
- **Microservice coupling:** Temporal coupling across service boundaries

**Impact:** Understand polyglot systems as unified architecture

**Implementation:**
- Pattern matching for API calls (URL strings in code)
- Protocol Buffer/GraphQL schema analysis
- Cross-language import detection (e.g., WASM modules)

### 6. Language Ecosystem Analysis

**Opportunity:** Track third-party dependencies:
- Parse `package.json`, `requirements.txt`, `Cargo.toml`, etc.
- Build dependency tree including external libraries
- Detect version conflicts, outdated dependencies
- Find "hidden" dependencies via import analysis
- Track temporal coupling of dependency updates

**Impact:** Supply chain security + upgrade planning

**Implementation:**
- New `ecosystem_analyzer.py` for package manager files
- External dependency table in structure.db
- Integration with vulnerability databases (CVE lookup)

---

## Tier 3: Advanced Analytics
*Leveraging SQLite + graph algorithms*

### 7. Change Impact Analysis

**Opportunity:** "If I modify this file, what breaks?"
- **Transitive dependency closure:** All files depending on X (direct/indirect)
- **Test impact:** Which test files should run for a change
- **Blast radius estimation:** Combine with temporal coupling for feature impact
- **Change prediction:** "Changing X usually requires changing Y based on history"

**Impact:** Faster code reviews, smarter CI/CD (run only affected tests)

**Implementation:**
- Recursive SQL CTE for transitive closure
- Map source files to test files via naming convention
- Machine learning model for change prediction

### 8. Architectural Pattern Detection

**Opportunity:** Use graph topology to detect patterns:
- **Layered architecture:** UI → Service → Data Access layers
- **Hexagonal/Ports & Adapters:** Core domain vs adapters
- **Microkernel pattern:** Plugin architectures
- **Strangler Fig:** Old system gradually replaced
- **Anti-patterns:** God classes, feature envy, shotgun surgery

**Impact:** Automated architecture documentation + conformance checking

**Implementation:**
- Graph centrality metrics (PageRank, betweenness)
- Pattern matching on dependency graph structure
- Heuristics for layer detection (directory structure + import direction)

### 9. Code Quality Trends

**Opportunity:** Time-series analysis of structural metrics:
- Plot instability, coupling, complexity over time (per commit)
- Detect "big ball of mud" emergence early
- Track refactoring effectiveness (did complexity decrease?)
- Compare branches: "Feature branch added 15% more coupling"

**Impact:** Objective code quality measurement in CI/CD

**Implementation:**
- Store historical snapshots of metrics per commit
- Time-series table in history.db
- Observable line charts with trend analysis

### 10. Developer Productivity Insights

**Opportunity:** Combine authorship + structural + temporal data:
- **Onboarding metrics:** Time until new devs touch core modules
- **Code ownership evolution:** Knowledge transfer tracking
- **Collaboration patterns:** Teams with high temporal coupling
- **Cognitive load:** Developers in high-complexity + high-coupling areas
- **Specialization vs generalization:** Who works across boundaries?

**Impact:** Engineering management insights, team health metrics

**Implementation:**
- Author-centric views joining all metrics
- Network graph of developer collaboration
- Dashboard for engineering managers

---

## Tier 4: Integration & Ecosystem
*Making data actionable*

### 11. IDE Integration

**Opportunity:** Real-time feedback while coding (VS Code extension):
- "This file is a hotspot (top 5% churn + complexity)"
- "Adding this import increases coupling by 12%"
- "3 circular dependencies detected in this module"
- "Last modified by Alice 6 months ago (context switch warning)"

**Impact:** Shift-left architecture feedback to development time

**Implementation:**
- VS Code Language Server Protocol extension
- Query SQLite databases from extension
- Inline decorations and hover tooltips

### 12. CI/CD Gates

**Opportunity:** Enforce architectural rules:
- Fail build if circular dependencies introduced
- Warn if PR increases instability beyond threshold
- Require architecture team review for changes to stable modules
- Block imports from "forbidden" layers (UI importing database)

**Impact:** Automated architecture governance

**Implementation:**
- CLI commands for metric thresholds (`--max-instability 0.7`)
- GitHub Actions / GitLab CI integration
- Configuration file for architecture rules (`.depanalysis.yml`)

### 13. Pull Request Enrichment

**Opportunity:** GitHub/GitLab bot comments:
- "This PR touches 3 hotspot files - extra review recommended"
- "High temporal coupling with feature-auth - coordinate changes?"
- "Modified file has 12 dependents - run integration tests"
- Visual dependency graph: "Your changes affect these modules ↓"

**Impact:** Better code review context

**Implementation:**
- GitHub App / GitLab webhook integration
- Diff analysis (before/after metrics)
- Markdown comment generation with embedded images

### 14. Migration Planning

**Opportunity:** Track large refactoring efforts:
- **Python 2→3 migration:** Find all files with old patterns
- **Framework migration:** Track old→new framework API usage over time
- **Monolith→Microservices:** Identify module boundaries with low coupling
- **Deprecation tracking:** Find all usages of deprecated APIs

**Impact:** Data-driven technical debt reduction

**Implementation:**
- Pattern-based searches (regex on AST nodes)
- Migration progress dashboard
- Tagging system for migration waves

---

## Tier 5: Advanced Visualizations
*Beyond Observable Framework*

### 15. Interactive 3D Graph

**Opportunity:** Using Three.js or similar:
- Modules as nodes in 3D space
- Edges for dependencies (structural + temporal)
- Color by churn, size by complexity
- Cluster by directory/layer
- Time-travel slider: Watch architecture evolve over Git history

**Impact:** Understand large codebases spatially

**Implementation:**
- Force-directed graph layout in 3D
- WebGL rendering for performance
- Animation timeline using Git history

### 16. Architectural Fitness Functions Dashboard

**Opportunity:** Real-time monitoring:
- Key metrics: Average instability, circular dependency count, hotspot count
- Trend lines: Improving or degrading?
- Alerts: "Coupling increased 20% this sprint"
- Comparison: Current vs baseline (main branch)

**Impact:** Architecture as measurable, trackable quality attribute

**Implementation:**
- Metrics aggregation per time period (sprint, week, month)
- Alerting system with configurable thresholds
- Integration with monitoring tools (Grafana, Datadog)

### 17. Dependency Diff Visualization

**Opportunity:** Compare two branches/commits:
- "Feature branch added 23 new dependencies"
- "Refactoring removed 8 circular dependencies ✓"
- Side-by-side dependency matrices
- Changed coupling visualization

**Impact:** Visualize architectural impact of changes

**Implementation:**
- Diff algorithm on graph structures
- Visual highlighting of additions/removals/changes
- Observable page for branch comparison

---

## Tier 6: AI-Powered Features
*Leveraging LLMs*

### 18. Automated Refactoring Suggestions

**Opportunity:** Use LLM + dependency graph:
- "Module X has high efferent coupling - suggest extracting interface"
- "Files A, B, C have high temporal coupling - consider merging or abstracting"
- "Circular dependency A→B→A could be broken by introducing interface Z"
- Generate refactoring code using LLM with architectural context

**Impact:** From metrics → actionable plans → actual code

**Implementation:**
- LLM prompts with graph context and code snippets
- Validation of suggestions against architecture rules
- Preview of refactoring impact (metrics before/after)

### 19. Natural Language Queries

**Opportunity:** Chat interface over codebase:
- "Which files change most often with authentication code?"
- "Show me all modules with circular dependencies"
- "What's the complexity trend for our API layer?"
- "Which developers work on the database layer?"

**Impact:** Architecture insights accessible to non-technical stakeholders

**Implementation:**
- LLM translates natural language to SQL queries
- Text-to-SQL with schema context
- Conversational interface with follow-up questions

### 20. Architectural Documentation Generation

**Opportunity:** Auto-generate docs:
- "This codebase follows a layered architecture with..."
- Component diagrams from dependency graph
- Hotspot reports with context from commit messages
- Onboarding guides: "Start by understanding these 5 core modules"

**Impact:** Documentation stays up-to-date automatically

**Implementation:**
- LLM summarization of architectural patterns
- Diagram generation (Mermaid, PlantUML)
- Integration with doc platforms (Notion, Confluence)

---

## Tier 7: Novel Research Directions

### 21. Predictive Maintenance

**Opportunity:** Machine learning models:
- Predict bug likelihood based on complexity + churn + coupling
- Forecast which files will change together in future
- Estimate refactoring effort based on historical patterns
- Predict code review time based on coupling + author experience

### 22. Cross-Repository Learning

**Opportunity:** Analyze thousands of open-source repos:
- What instability thresholds correlate with high bug rates?
- Do circular dependencies actually predict maintenance issues?
- Language-specific patterns (Python vs Rust churn rates?)
- Extract "healthy architecture" patterns from successful projects

### 23. Real-Time Collaboration Awareness

**Opportunity:** Integrate with dev tools:
- "Alice is editing a file with high temporal coupling to yours"
- Suggest pairing on high complexity + multi-author files
- Detect merge conflict likelihood before pushing

---

## The Ultimate Vision: Code Observatory

This tool could become a **continuous monitoring system** that:

1. **Understands** codebase structure across all languages
2. **Tracks** evolution over time (commits, authors, patterns)
3. **Detects** architectural issues early (coupling, cycles, hotspots)
4. **Predicts** future problems (bug risk, maintenance burden)
5. **Recommends** specific refactorings with rationale
6. **Enforces** architectural rules in CI/CD
7. **Educates** developers with real-time feedback
8. **Generates** documentation automatically
9. **Integrates** with entire development workflow (IDE, PR, chat)
10. **Learns** from open-source to improve recommendations

---

## Immediate High-Impact Wins

To maximize value quickly, prioritize these features:

### 1. Complete the Python Parser ✅
**Effort:** Medium | **Impact:** High | **Dependencies:** None

Add AST visitors for calls, inheritance, decorators, type hints, variables. This unlocks the full power of structural analysis.

**Files to modify:**
- `depanalysis/structure_analyzer.py` - Add missing AST visitors
- `tests/test_structural_coupling.py` - Extend test coverage

### 2. Build Hotspot Analysis 🔥
**Effort:** Low | **Impact:** Very High | **Dependencies:** #1

Combine structure.db + history.db metrics to identify maintenance burden.

**Files to create:**
- SQL view for hotspot calculation
- Observable dashboard for visualization
- CLI command: `depanalysis show-hotspots <repo>`

### 3. Add Circular Dependency Detection ♻️
**Effort:** Medium | **Impact:** High | **Dependencies:** #1

Implement graph algorithm to find and visualize cycles.

**Files to modify:**
- `depanalysis/metrics.py` - Add cycle detection algorithm
- Observable dependency matrix - Highlight cycles

### 4. Create Hotspot Visualization 📊
**Effort:** Low | **Impact:** High | **Dependencies:** #2

Interactive dashboard showcasing fusion metrics.

**Files to create:**
- `docs/src/hotspots.md` - Observable page
- `docs/src/data/hotspots.json.py` - Data loader

### 5. Add TypeScript Parser 🔷
**Effort:** High | **Impact:** Medium | **Dependencies:** None

Prove polyglot architecture works with second language.

**Files to create:**
- `depanalysis/typescript_analyzer.py` - New parser
- `tests/test_typescript_parser.py` - Test suite

---

## Why This Foundation Enables Everything

The current architecture is **perfectly positioned** for this evolution:

- ✅ **Language-agnostic schema** → Easy to add parsers for any language
- ✅ **Dual database design** → Clean separation, efficient queries
- ✅ **SQLite as source of truth** → Portable, fast, SQL-queryable
- ✅ **Observable Framework** → Modern, interactive visualizations
- ✅ **Comprehensive tests** → Solid foundation for extension
- ✅ **Clean abstractions** → Easy to add analyzers, metrics, visualizations

Every feature in this roadmap is **achievable** because the architecture is sound. The foundation built in 2-3 weeks is enterprise-grade quality.

---

## Contributing

This roadmap is a living document. As features are implemented or priorities shift, update accordingly. Each tier builds on previous tiers, but many features within tiers can be developed in parallel.

**Priority Framework:**
- **High-Impact, Low-Effort** → Do first (Tier 1 features)
- **High-Impact, High-Effort** → Plan carefully (Polyglot support)
- **Low-Impact, Low-Effort** → Nice-to-haves (Additional visualizations)
- **Research** → Long-term exploration (Tier 7)

---

*Last Updated: 2025-01-18*
*Based on codebase analysis at commit: e86a9c6*
