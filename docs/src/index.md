# depanalysis Reports

Welcome to the interactive analysis dashboard for your code repositories. Explore Git history, temporal coupling, and author contributions.

## Analyzed Repositories

```js
const repos = FileAttachment("./data/repo-list.json").json();
const summaries = FileAttachment("./data/all-repos-summary.json").json();
```

```js
// Create repository cards with summary stats
const repoCards = summaries.map(repo => html`
  <a href="./repo/${repo.name}" class="repo-link">
    <h3 style="margin: 0 0 0.5rem 0;">${repo.name}</h3>
    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem; font-size: 0.9rem; color: #666;">
      <div>📝 ${repo.total_commits} commits</div>
      <div>👥 ${repo.total_authors} authors</div>
      <div>📄 ${repo.files_tracked} files</div>
      <div>🔗 ${repo.temporal_couplings} couplings</div>
    </div>
  </a>
`);
```

<div class="grid-2">
  ${repoCards}
</div>

---

## Structural Analysis

Analyze code architecture through static analysis of dependencies, complexity, and relationships.

<div class="grid-3">
  <div class="card">
    <h3>🔗 Coupling & Instability</h3>
    <p>NDepend-style metrics: afferent/efferent coupling, instability scores, and Main Sequence analysis.</p>
    <a href="./structural/coupling-instability">View Metrics →</a>
  </div>

  <div class="card">
    <h3>📊 Dependency Matrix</h3>
    <p>Interactive DSM showing structural and temporal coupling between modules.</p>
    <a href="./structural/dependency-matrix">View Matrix →</a>
  </div>

  <div class="card">
    <h3>📈 Complexity Distribution</h3>
    <p>Cyclomatic complexity metrics, function size analysis, and quality thresholds.</p>
    <a href="./structural/complexity">View Complexity →</a>
  </div>

  <div class="card">
    <h3>🌳 Call Graphs</h3>
    <p>Function call relationships, entry points, and dead code detection.</p>
    <a href="./structural/call-graphs">View Call Graphs →</a>
  </div>

  <div class="card">
    <h3>🏗️ Inheritance Trees</h3>
    <p>Class hierarchies, interface implementations, and OOP design patterns.</p>
    <a href="./structural/inheritance">View Hierarchies →</a>
  </div>
</div>

---

## Temporal Analysis

Understand how code evolves over time through Git history analysis.

<div class="grid-3">
  <div class="card">
    <h3>🔗 Coupling Network</h3>
    <p>Files that change together, revealing hidden dependencies and architectural issues.</p>
    <a href="./temporal/coupling">View Network →</a>
  </div>

  <div class="card">
    <h3>⏰ Code Age & Churn</h3>
    <p>Track file age, change frequency, and identify legacy hotspots.</p>
    <a href="./temporal/age-churn">View Age Analysis →</a>
  </div>

  <div class="card">
    <h3>📊 Commit Patterns</h3>
    <p>Development velocity, commit frequency heatmaps, and activity trends.</p>
    <a href="./temporal/commits">View Patterns →</a>
  </div>

  <div class="card">
    <h3>🏥 Architecture Health</h3>
    <p>Hotspots, circular dependencies, and hidden coupling detection.</p>
    <a href="./temporal/architecture-health">View Health Dashboard →</a>
  </div>
</div>

---

## Cross-Language Analysis

Analyze polyglot repositories and cross-language dependencies.

<div class="grid-3">
  <div class="card">
    <h3>🌐 API Boundaries</h3>
    <p>REST endpoints, API calls, and service boundaries across languages.</p>
    <a href="./cross-language/api-boundaries">View API Analysis →</a>
  </div>

  <div class="card">
    <h3>🗂️ Polyglot Overview</h3>
    <p>Language distribution, cross-language coupling, and ecosystem statistics.</p>
    <a href="./cross-language/polyglot">View Polyglot Stats →</a>
  </div>

  <div class="card">
    <h3>📦 Dependency Ecosystem</h3>
    <p>External dependencies, version conflicts, and supply chain analysis.</p>
    <a href="./cross-language/dependencies">View Dependencies →</a>
  </div>
</div>

---

## Code Quality

Track code quality metrics, type safety, and best practices.

<div class="grid-3">
  <div class="card">
    <h3>🔒 Type Safety</h3>
    <p>Type hint coverage, generic parameter usage, and type safety trends.</p>
    <a href="./quality/type-safety">View Type Metrics →</a>
  </div>

  <div class="card">
    <h3>🎨 Decorator Usage</h3>
    <p>Framework decorators, Flask/FastAPI routes, and decorator patterns.</p>
    <a href="./quality/decorators">View Decorators →</a>
  </div>

  <div class="card">
    <h3>✅ Quality Metrics</h3>
    <p>Combined quality scores, technical debt indicators, and recommendations.</p>
    <a href="./quality/overview">View Quality Dashboard →</a>
  </div>
</div>

---

## Insights

Cross-cutting analysis and comparisons.

<div class="grid-2">
  <div class="card">
    <h3>👥 Author Analytics</h3>
    <p>Contributor patterns, code ownership, and collaboration dynamics.</p>
    <a href="./insights/authors">View Author Stats →</a>
  </div>

  <div class="card">
    <h3>📊 Compare Repositories</h3>
    <p>Side-by-side comparison of metrics across multiple repositories.</p>
    <a href="./insights/compare">Compare Repos →</a>
  </div>
</div>

---

## About

This dashboard is powered by **depanalysis**, a multi-language dependency analysis tool that combines:

- **Static Structural Analysis**: Tree-sitter-based parsing for Python, TypeScript, JavaScript, C#, Java, Rust, C++, and Go
- **Temporal Behavioral Analysis**: Git history mining for change patterns and coupling
- **Cross-Language Support**: API boundary detection, polyglot metrics, and ecosystem analysis

**Analysis Capabilities:**
- 🔗 **Coupling Metrics**: Afferent/efferent coupling, instability, temporal coupling
- 📈 **Complexity**: Cyclomatic complexity, function size, module metrics
- ⏰ **Temporal Patterns**: Churn, code age, commit frequency, hotspots
- 🌐 **Cross-Language**: API boundaries, shared types, dependency conflicts
- ✅ **Quality**: Type safety, decorator usage, technical debt
