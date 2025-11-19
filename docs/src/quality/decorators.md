# Decorator Usage

Framework decorators, Flask/FastAPI routes, and decorator patterns across the codebase.

```js
const repos = FileAttachment("../data/repo-list.json").json();
const currentRepo = repos[0];
```

```js
const data = FileAttachment("../data/decorator-usage.json").json();
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

  const stats = data.statistics || {};

  if (stats.total_usage === 0) {
    return html`<div style="background: #dbeafe; border-left: 4px solid #4facfe; border-radius: 8px; padding: 1rem 1.5rem;">
      <h4 style="margin: 0 0 0.5rem 0; color: #1e40af;">ℹ️ No Decorators</h4>
      <p style="margin: 0; color: #1e40af;">No decorators detected in this repository.</p>
    </div>`;
  }

  return html`
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin: 1.5rem 0;">
      <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Unique Decorators</h3>
        <div style="font-size: 2rem; font-weight: 700;">${stats.unique_decorators}</div>
      </div>
      <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Total Usage</h3>
        <div style="font-size: 2rem; font-weight: 700;">${stats.total_usage}</div>
      </div>
    </div>
  `;
}
```

## Most Used Decorators

```js
{
  const decorators = data.decorators || [];
  if (decorators.length === 0) return '';

  // Aggregate by decorator name
  const byName = d3.rollup(
    decorators,
    v => d3.sum(v, d => d.count),
    d => d.name
  );

  const aggregated = Array.from(byName, ([name, count]) => ({name, count}));

  return Plot.plot({
    marginLeft: 200,
    x: {label: "Usage Count", grid: true},
    y: {label: null},
    marks: [
      Plot.barX(aggregated.slice(0, 20), {
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

## Most Decorated Functions

```js
{
  const functions = data.functions || [];

  if (functions.length === 0) {
    return html`<div style="text-align: center; padding: 2rem; color: #9ca3af;">No decorated functions</div>`;
  }

  return Inputs.table(functions, {
    columns: ["name", "module", "decorator_count"],
    header: {
      name: "Function",
      module: "Module",
      decorator_count: "Decorator Count"
    },
    sort: "decorator_count",
    reverse: true
  });
}
```

## Decorator Details

```js
{
  const decorators = data.decorators || [];
  if (decorators.length === 0) return '';

  return Inputs.table(decorators, {
    columns: ["name", "count", "module"],
    header: {
      name: "Decorator",
      count: "Usage Count",
      module: "Module"
    },
    sort: "count",
    reverse: true
  });
}
```

---

<div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 2px solid #e5e7eb; display: flex; justify-content: space-between; font-size: 0.875rem;">
  <a href="../" style="color: #667eea; text-decoration: none;">← Home</a>
  <a href="../quality/type-safety" style="color: #667eea; text-decoration: none;">← Type Safety</a>
</div>
