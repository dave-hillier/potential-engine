# Complexity Distribution

Cyclomatic complexity analysis for functions and modules.

```js
const repos = FileAttachment("data/repo-list.json").json();
const currentRepo = repos[0];
```

```js
const data = FileAttachment("data/complexity-distribution.json").json();
```

<div style="background: #dbeafe; border-left: 4px solid #4facfe; border-radius: 8px; padding: 0.75rem 1rem; margin: 1rem 0; font-size: 0.9rem;">
  <strong>Repository:</strong> ${currentRepo}
</div>

## Overview

```js
{
  if (data.error) {
    return html`<div style="background: #fee2e2; border-left: 4px solid #f5576c; border-radius: 8px; padding: 1rem 1.5rem; margin: 1.5rem 0;">
      <h4 style="margin: 0 0 0.5rem 0; font-size: 1rem; font-weight: 600; color: #991b1b;">⚠️ Error</h4>
      <p style="margin: 0; color: #991b1b;">${data.error}</p>
    </div>`;
  }

  const stats = data.statistics || {};
  const highComplexityPct = stats.total_functions > 0
    ? ((stats.high_complexity_count / stats.total_functions) * 100).toFixed(1)
    : 0;

  return html`
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.5rem 0;">
      <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Total Functions</h3>
        <div style="font-size: 2rem; font-weight: 700;">${stats.total_functions}</div>
      </div>
      <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Avg Complexity</h3>
        <div style="font-size: 2rem; font-weight: 700;">${stats.avg_complexity}</div>
      </div>
      <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Max Complexity</h3>
        <div style="font-size: 2rem; font-weight: 700;">${stats.max_complexity}</div>
      </div>
      <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">High Complexity</h3>
        <div style="font-size: 2rem; font-weight: 700;">${stats.high_complexity_count}</div>
        <div style="font-size: 0.875rem; opacity: 0.8;">${highComplexityPct}% (>15)</div>
      </div>
    </div>
  `;
}
```

## Complexity Histogram

```js
{
  const functions = data.functions || [];
  if (functions.length === 0) return html`<div style="text-align: center; padding: 2rem; color: #9ca3af;">No function data available</div>`;

  // Create bins for complexity ranges
  const bins = [
    {range: "1-5", min: 1, max: 5, color: "#43e97b"},
    {range: "6-10", min: 6, max: 10, color: "#4facfe"},
    {range: "11-15", min: 11, max: 15, color: "#f093fb"},
    {range: "16-20", min: 16, max: 20, color: "#f5576c"},
    {range: "21+", min: 21, max: 9999, color: "#dc2626"}
  ];

  const binCounts = bins.map(bin => ({
    range: bin.range,
    count: functions.filter(f => f.complexity >= bin.min && f.complexity <= bin.max).length,
    color: bin.color
  }));

  return Plot.plot({
    marginBottom: 60,
    x: {label: "Complexity Range"},
    y: {label: "Function Count", grid: true},
    marks: [
      Plot.barY(binCounts, {
        x: "range",
        y: "count",
        fill: "color",
        tip: true
      }),
      Plot.ruleY([0])
    ]
  });
}
```

## Most Complex Functions

```js
{
  const functions = data.functions || [];
  if (functions.length === 0) return '';

  return Plot.plot({
    marginLeft: 200,
    x: {label: "Cyclomatic Complexity", grid: true},
    y: {label: null},
    marks: [
      Plot.barX(functions.slice(0, 20), {
        x: "complexity",
        y: "name",
        fill: d => d.complexity > 15 ? "#f5576c" : "#4facfe",
        sort: {y: "-x"},
        tip: true
      }),
      Plot.ruleX([15], {stroke: "#f5576c", strokeDasharray: "4,4"})
    ]
  });
}
```

## High Complexity Functions (>15)

```js
{
  const functions = data.functions || [];
  const highComplexity = functions.filter(f => f.complexity > 15);

  if (highComplexity.length === 0) {
    return html`<div style="background: #d1fae5; border-left: 4px solid #43e97b; border-radius: 8px; padding: 1rem 1.5rem;">
      <h4 style="margin: 0 0 0.5rem 0; color: #065f46;">✅ No High Complexity Functions</h4>
      <p style="margin: 0; color: #065f46;">All functions have complexity ≤ 15.</p>
    </div>`;
  }

  return Inputs.table(highComplexity, {
    columns: ["name", "complexity", "module", "line"],
    header: {
      name: "Function",
      complexity: "Complexity",
      module: "Module",
      line: "Line"
    },
    sort: "complexity",
    reverse: true
  });
}
```

## Module Complexity

```js
{
  const modules = data.modules || [];
  if (modules.length === 0) return '';

  return Inputs.table(modules, {
    columns: ["path", "function_count", "avg_complexity", "total_complexity"],
    header: {
      path: "Module Path",
      function_count: "Functions",
      avg_complexity: "Avg Complexity",
      total_complexity: "Total Complexity"
    },
    sort: "total_complexity",
    reverse: true
  });
}
```

## About Cyclomatic Complexity

**Cyclomatic Complexity** measures the number of independent paths through code:
- **1-5**: Simple, low risk
- **6-10**: Moderate complexity
- **11-15**: Complex, needs attention
- **16-20**: High complexity, refactor recommended
- **21+**: Very high complexity, difficult to test and maintain

---

<div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 2px solid #e5e7eb; display: flex; justify-content: space-between; font-size: 0.875rem;">
  <a href="../" style="color: #667eea; text-decoration: none;">← Home</a>
  <a href="../structural/call-graphs" style="color: #667eea; text-decoration: none;">Call Graphs →</a>
</div>
