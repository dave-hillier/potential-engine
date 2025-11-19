# Polyglot Overview

Language distribution, cross-language coupling, and ecosystem statistics for polyglot repositories.

```js
const repos = FileAttachment("../data/repo-list.json").json();
const selectedRepo = view(Inputs.select(repos, {label: "Repository", value: repos[0]}));
```

```js
const polyglotData = FileAttachment("../data/polyglot-stats.json.py", {cache: false}).json({
  command: ["../../../../venv/bin/python3", "../data/polyglot-stats.json.py", selectedRepo]
});
```

## Language Distribution

```js
{
  if (polyglotData.error) {
    return html`<div class="alert alert--warning">
      <h4>⚠️ Error Loading Data</h4>
      <p>${polyglotData.error}</p>
    </div>`;
  }

  const languages = polyglotData.languages || [];

  if (languages.length === 0) {
    return html`<div class="alert alert--info">
      <h4>ℹ️ No Language Data</h4>
      <p>No parsed files found in this repository.</p>
    </div>`;
  }

  const totalFiles = d3.sum(languages, d => d.files);
  const totalFunctions = d3.sum(languages, d => d.functions);
  const totalComplexity = d3.sum(languages, d => d.complexity);

  return html`
    <div class="grid-4">
      <div class="metric-card">
        <h3>Languages</h3>
        <div class="value">${languages.length}</div>
        <div class="subvalue">Detected</div>
      </div>
      <div class="metric-card metric-card--pink">
        <h3>Total Files</h3>
        <div class="value">${totalFiles}</div>
        <div class="subvalue">Across all languages</div>
      </div>
      <div class="metric-card metric-card--blue">
        <h3>Total Functions</h3>
        <div class="value">${totalFunctions}</div>
        <div class="subvalue">Callable units</div>
      </div>
      <div class="metric-card metric-card--green">
        <h3>Total Complexity</h3>
        <div class="value">${totalComplexity}</div>
        <div class="subvalue">Cyclomatic complexity</div>
      </div>
    </div>
  `;
}
```

## Files by Language

```js
{
  const languages = polyglotData.languages || [];

  if (languages.length === 0) {
    return '';
  }

  return Plot.plot({
    marginLeft: 100,
    x: {label: "File Count", grid: true},
    y: {label: null},
    color: {legend: true},
    marks: [
      Plot.barX(languages, {
        x: "files",
        y: "name",
        fill: "name",
        sort: {y: "-x"},
        tip: true
      }),
      Plot.ruleX([0])
    ]
  });
}
```

## Complexity by Language

```js
{
  const languages = polyglotData.languages || [];

  if (languages.length === 0) {
    return '';
  }

  return Plot.plot({
    marginLeft: 100,
    x: {label: "Total Cyclomatic Complexity", grid: true},
    y: {label: null},
    color: {legend: true},
    marks: [
      Plot.barX(languages, {
        x: "complexity",
        y: "name",
        fill: "name",
        sort: {y: "-x"},
        tip: true
      }),
      Plot.ruleX([0])
    ]
  });
}
```

## Cross-Language Imports

```js
{
  const crossLangImports = polyglotData.cross_language_imports || [];

  if (crossLangImports.length === 0) {
    return html`<div class="alert alert--success">
      <h4>✅ No Cross-Language Imports</h4>
      <p>This repository does not have imports between different programming languages.</p>
    </div>`;
  }

  return html`
    <div class="alert alert--info">
      <h4>🔗 Cross-Language Dependencies Detected</h4>
      <p>${crossLangImports.length} import relationship(s) between different languages.</p>
    </div>
  `;
}
```

```js
{
  const crossLangImports = polyglotData.cross_language_imports || [];

  if (crossLangImports.length === 0) {
    return '';
  }

  return Inputs.table(crossLangImports, {
    columns: ["from", "to", "count"],
    header: {
      from: "From Language",
      to: "To Language",
      count: "Import Count"
    }
  });
}
```

## External Dependencies by Ecosystem

```js
{
  const externalDeps = polyglotData.external_dependencies || [];

  if (externalDeps.length === 0) {
    return html`<div class="empty-state">
      <div class="empty-state-icon">📦</div>
      <h3>No External Dependencies</h3>
      <p>No package dependencies detected in manifest files.</p>
    </div>`;
  }

  const totalPackages = d3.sum(externalDeps, d => d.unique_packages);
  const totalProd = d3.sum(externalDeps, d => d.prod_packages);
  const totalDev = d3.sum(externalDeps, d => d.dev_packages);

  return html`
    <div class="grid-4">
      <div class="metric-card metric-card--teal">
        <h3>Ecosystems</h3>
        <div class="value">${externalDeps.length}</div>
        <div class="subvalue">Package managers</div>
      </div>
      <div class="metric-card metric-card--pink">
        <h3>Total Packages</h3>
        <div class="value">${totalPackages}</div>
        <div class="subvalue">Unique dependencies</div>
      </div>
      <div class="metric-card metric-card--blue">
        <h3>Production</h3>
        <div class="value">${totalProd}</div>
        <div class="subvalue">Prod dependencies</div>
      </div>
      <div class="metric-card metric-card--orange">
        <h3>Development</h3>
        <div class="value">${totalDev}</div>
        <div class="subvalue">Dev dependencies</div>
      </div>
    </div>
  `;
}
```

## Dependencies by Package Manager

```js
{
  const externalDeps = polyglotData.external_dependencies || [];

  if (externalDeps.length === 0) {
    return '';
  }

  return Plot.plot({
    marginLeft: 120,
    x: {label: "Package Count", grid: true},
    y: {label: null},
    marks: [
      Plot.barX(externalDeps, {
        x: "unique_packages",
        y: "package_manager",
        fill: "ecosystem",
        sort: {y: "-x"},
        tip: true
      }),
      Plot.ruleX([0])
    ]
  });
}
```

## Dependency Details

```js
{
  const externalDeps = polyglotData.external_dependencies || [];

  if (externalDeps.length === 0) {
    return '';
  }

  return Inputs.table(externalDeps, {
    columns: ["ecosystem", "package_manager", "unique_packages", "prod_packages", "dev_packages"],
    header: {
      ecosystem: "Ecosystem",
      package_manager: "Package Manager",
      unique_packages: "Total Packages",
      prod_packages: "Production",
      dev_packages: "Development"
    }
  });
}
```

## Version Conflicts

```js
{
  const conflicts = polyglotData.version_conflicts || [];

  if (conflicts.length === 0) {
    return html`<div class="alert alert--success">
      <h4>✅ No Version Conflicts</h4>
      <p>All dependencies have consistent versions across manifest files.</p>
    </div>`;
  }

  return html`<div class="alert alert--warning">
    <h4>⚠️ Version Conflicts Detected</h4>
    <p>${conflicts.length} package(s) have conflicting versions across different manifest files.</p>
  </div>`;
}
```

```js
{
  const conflicts = polyglotData.version_conflicts || [];

  if (conflicts.length === 0) {
    return '';
  }

  return Inputs.table(conflicts, {
    columns: ["package", "version1", "version2", "conflict_type"],
    header: {
      package: "Package Name",
      version1: "Version 1",
      version2: "Version 2",
      conflict_type: "Conflict Type"
    }
  });
}
```

## API Endpoints by Language

```js
{
  const apiEndpoints = polyglotData.api_endpoints || [];

  if (apiEndpoints.length === 0) {
    return html`<div class="empty-state">
      <div class="empty-state-icon">🌐</div>
      <h3>No API Endpoints</h3>
      <p>No REST API endpoints detected in this repository.</p>
    </div>`;
  }

  return Plot.plot({
    marginLeft: 100,
    x: {label: "Endpoint Count", grid: true},
    y: {label: null},
    color: {legend: true},
    marks: [
      Plot.barX(apiEndpoints, {
        x: "count",
        y: "language",
        fill: "type",
        sort: {y: "-x"},
        tip: true
      }),
      Plot.ruleX([0])
    ]
  });
}
```

## API Calls by Language

```js
{
  const apiCalls = polyglotData.api_calls || [];

  if (apiCalls.length === 0) {
    return html`<div class="empty-state">
      <div class="empty-state-icon">📡</div>
      <h3>No API Calls</h3>
      <p>No API calls detected in this repository.</p>
    </div>`;
  }

  return Plot.plot({
    marginLeft: 100,
    x: {label: "Call Count", grid: true},
    y: {label: null},
    color: {legend: true},
    marks: [
      Plot.barX(apiCalls, {
        x: "count",
        y: "language",
        fill: "type",
        sort: {y: "-x"},
        tip: true
      }),
      Plot.ruleX([0])
    ]
  });
}
```

## Shared Types

```js
{
  const sharedTypes = polyglotData.shared_types || [];

  if (sharedTypes.length === 0) {
    return html`<div class="empty-state">
      <div class="empty-state-icon">🔗</div>
      <h3>No Shared Types</h3>
      <p>No shared type definitions (Protocol Buffers, GraphQL, OpenAPI) detected.</p>
    </div>`;
  }

  return html`
    <div class="alert alert--info">
      <h4>🔗 Shared Type Systems</h4>
      <p>This repository uses shared type definitions for cross-language communication.</p>
    </div>
  `;
}
```

```js
{
  const sharedTypes = polyglotData.shared_types || [];

  if (sharedTypes.length === 0) {
    return '';
  }

  return Inputs.table(sharedTypes, {
    columns: ["type_system", "count"],
    header: {
      type_system: "Type System",
      count: "Type Count"
    }
  });
}
```

## Language Statistics Table

```js
{
  const languages = polyglotData.languages || [];

  if (languages.length === 0) {
    return '';
  }

  return Inputs.table(languages, {
    columns: ["name", "files", "functions", "complexity"],
    header: {
      name: "Language",
      files: "Files",
      functions: "Functions",
      complexity: "Complexity"
    },
    sort: "files",
    reverse: true
  });
}
```

---

<div class="footer-nav">
  <a href="../">← Home</a> |
  <a href="../cross-language/api-boundaries">← API Boundaries</a> |
  <a href="../cross-language/dependencies">Dependencies →</a>
</div>
