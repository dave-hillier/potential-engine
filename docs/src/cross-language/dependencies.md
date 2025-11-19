# Dependency Ecosystem

External package dependencies, version conflicts, and supply chain analysis.

```js
const repos = FileAttachment("../data/repo-list.json").json();
const currentRepo = repos[0];
```

```js
const data = FileAttachment("../data/dependency-ecosystem.json").json();
```

<div style="background: #dbeafe; border-left: 4px solid #4facfe; border-radius: 8px; padding: 0.75rem 1rem; margin: 1rem 0; font-size: 0.9rem;">
  <strong>Repository:</strong> ${currentRepo}
</div>

## Overview

```js
{
  if (data.error) {
    return html`<div style="background: #fee2e2; border-left: 4px solid #f5576c; border-radius: 8px; padding: 1rem 1.5rem;">
      <h4 style="margin: 0 0 0.5rem 0; color: #991b1b;">⚠️ Error</h4>
      <p style="margin: 0; color: #991b1b;">${data.error}</p>
    </div>`;
  }

  const deps = data.dependencies || [];
  const conflicts = data.conflicts || [];

  if (deps.length === 0) {
    return html`<div style="background: #dbeafe; border-left: 4px solid #4facfe; border-radius: 8px; padding: 1rem 1.5rem;">
      <h4 style="margin: 0 0 0.5rem 0; color: #1e40af;">ℹ️ No Dependencies</h4>
      <p style="margin: 0; color: #1e40af;">No external dependencies detected in manifest files.</p>
    </div>`;
  }

  const ecosystems = new Set(deps.map(d => d.ecosystem)).size;
  const prodDeps = deps.filter(d => !d.is_dev).length;
  const devDeps = deps.filter(d => d.is_dev).length;

  return html`
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.5rem 0;">
      <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Total Packages</h3>
        <div style="font-size: 2rem; font-weight: 700;">${deps.length}</div>
      </div>
      <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Production</h3>
        <div style="font-size: 2rem; font-weight: 700;">${prodDeps}</div>
      </div>
      <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Development</h3>
        <div style="font-size: 2rem; font-weight: 700;">${devDeps}</div>
      </div>
      <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Ecosystems</h3>
        <div style="font-size: 2rem; font-weight: 700;">${ecosystems}</div>
      </div>
    </div>
  `;
}
```

## Dependencies by Ecosystem

```js
{
  const deps = data.dependencies || [];
  if (deps.length === 0) return '';

  const byEcosystem = d3.rollup(
    deps,
    v => v.length,
    d => d.ecosystem
  );

  const ecosystemData = Array.from(byEcosystem, ([ecosystem, count]) => ({ecosystem, count}));

  return Plot.plot({
    marginLeft: 120,
    x: {label: "Package Count", grid: true},
    y: {label: null},
    marks: [
      Plot.barX(ecosystemData, {
        x: "count",
        y: "ecosystem",
        fill: "ecosystem",
        sort: {y: "-x"},
        tip: true
      }),
      Plot.ruleX([0])
    ]
  });
}
```

## Version Conflicts

```js
{
  const conflicts = data.conflicts || [];

  if (conflicts.length === 0) {
    return html`<div style="background: #d1fae5; border-left: 4px solid #43e97b; border-radius: 8px; padding: 1rem 1.5rem;">
      <h4 style="margin: 0 0 0.5rem 0; color: #065f46;">✅ No Version Conflicts</h4>
      <p style="margin: 0; color: #065f46;">All dependencies have consistent versions.</p>
    </div>`;
  }

  return html`<div style="background: #fee2e2; border-left: 4px solid #f5576c; border-radius: 8px; padding: 1rem 1.5rem; margin-bottom: 1rem;">
    <h4 style="margin: 0 0 0.5rem 0; color: #991b1b;">⚠️ ${conflicts.length} Version Conflict(s)</h4>
    <p style="margin: 0; color: #991b1b;">Different versions specified across manifest files.</p>
  </div>`;
}
```

```js
{
  const conflicts = data.conflicts || [];
  if (conflicts.length === 0) return '';

  return Inputs.table(conflicts, {
    columns: ["package", "version1", "version2", "type"],
    header: {
      package: "Package",
      version1: "Version 1",
      version2: "Version 2",
      type: "Conflict Type"
    }
  });
}
```

## All Dependencies

```js
{
  const deps = data.dependencies || [];
  if (deps.length === 0) return '';

  return Inputs.table(deps, {
    columns: ["package", "version", "ecosystem", "package_manager", "is_dev"],
    header: {
      package: "Package",
      version: "Version",
      ecosystem: "Ecosystem",
      package_manager: "Package Manager",
      is_dev: "Dev Dependency"
    },
    format: {
      is_dev: d => d ? "Yes" : "No"
    }
  });
}
```

---

<div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 2px solid #e5e7eb; display: flex; justify-content: space-between; font-size: 0.875rem;">
  <a href="../" style="color: #667eea; text-decoration: none;">← Home</a>
  <a href="../cross-language/polyglot" style="color: #667eea; text-decoration: none;">← Polyglot Overview</a>
</div>
