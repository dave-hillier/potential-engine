# Type Safety

Type hint coverage and generic parameter usage across the codebase.

```js
const repos = FileAttachment("../data/repo-list.json").json();
const selectedRepo = view(Inputs.select(repos, {label: "Repository", value: repos[0]}));
```

```js
const data = FileAttachment("../data/type-safety-metrics.json.py", {cache: false}).json({
  command: ["../../../../venv/bin/python3", "../data/type-safety-metrics.json.py", selectedRepo]
});
```

## Overview

```js
{
  if (data.error) {
    return html`<div style="background: #fee2e2; border-left: 4px solid #f5576c; border-radius: 8px; padding: 1rem 1.5rem;">
      <h4 style="margin: 0 0 0.5rem 0; color: #991b1b;">⚠️ Error</h4>
      <p style="margin: 0; color: #991b1b;">${data.error}</p>
    </div>`;
  }

  const stats = data.statistics || {};
  const untyped = stats.total_functions - stats.typed_functions;

  return html`
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.5rem 0;">
      <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Coverage</h3>
        <div style="font-size: 2rem; font-weight: 700;">${stats.coverage_percent}%</div>
      </div>
      <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Typed Functions</h3>
        <div style="font-size: 2rem; font-weight: 700;">${stats.typed_functions}</div>
      </div>
      <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Untyped Functions</h3>
        <div style="font-size: 2rem; font-weight: 700;">${untyped}</div>
      </div>
      <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Total Functions</h3>
        <div style="font-size: 2rem; font-weight: 700;">${stats.total_functions}</div>
      </div>
    </div>
  `;
}
```

## Coverage by Module

```js
{
  const modules = data.modules || [];
  if (modules.length === 0) {
    return html`<div style="text-align: center; padding: 2rem; color: #9ca3af;">No type hint data available</div>`;
  }

  return Plot.plot({
    marginLeft: 250,
    x: {label: "Type Hint Coverage (%)", domain: [0, 100], grid: true},
    y: {label: null},
    marks: [
      Plot.barX(modules.slice(0, 20), {
        x: "coverage",
        y: "path",
        fill: d => d.coverage > 80 ? "#43e97b" : d.coverage > 50 ? "#4facfe" : "#f5576c",
        sort: {y: "-x"},
        tip: true
      }),
      Plot.ruleX([80], {stroke: "#43e97b", strokeDasharray: "4,4"}),
      Plot.ruleX([50], {stroke: "#f5576c", strokeDasharray: "4,4"})
    ]
  });
}
```

## Generic Parameter Usage

```js
{
  const generics = data.generics || [];

  if (generics.length === 0) {
    return html`<div style="background: #dbeafe; border-left: 4px solid #4facfe; border-radius: 8px; padding: 1rem 1.5rem;">
      <h4 style="margin: 0 0 0.5rem 0; color: #1e40af;">ℹ️ No Generic Parameters</h4>
      <p style="margin: 0; color: #1e40af;">No generic parameters detected in this repository.</p>
    </div>`;
  }

  return Plot.plot({
    marginLeft: 150,
    x: {label: "Usage Count", grid: true},
    y: {label: null},
    marks: [
      Plot.barX(generics.slice(0, 15), {
        x: "count",
        y: "name",
        fill: "steelblue",
        sort: {y: "-x"},
        tip: true
      }),
      Plot.ruleX([0])
    ]
  });
}
```

## Module Details

```js
{
  const modules = data.modules || [];
  if (modules.length === 0) return '';

  return Inputs.table(modules, {
    columns: ["path", "total_functions", "typed_functions", "coverage"],
    header: {
      path: "Module Path",
      total_functions: "Total Functions",
      typed_functions: "Typed Functions",
      coverage: "Coverage %"
    },
    sort: "coverage",
    reverse: true
  });
}
```

---

<div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 2px solid #e5e7eb; display: flex; justify-content: space-between; font-size: 0.875rem;">
  <a href="../" style="color: #667eea; text-decoration: none;">← Home</a>
  <a href="../quality/decorators" style="color: #667eea; text-decoration: none;">Decorator Usage →</a>
</div>
