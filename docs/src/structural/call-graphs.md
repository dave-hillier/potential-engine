# Call Graphs

Function call relationships, entry points, and dead code detection.

```js
const repos = FileAttachment("../data/repo-list.json").json();
```

```js
// Get the first repository name
const currentRepo = (await repos)[0];
```

```js
const data = FileAttachment("../data/call-graph.json").json();
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

  return html`
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.5rem 0;">
      <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Total Calls</h3>
        <div style="font-size: 2rem; font-weight: 700;">${stats.total_calls}</div>
      </div>
      <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Entry Points</h3>
        <div style="font-size: 2rem; font-weight: 700;">${stats.entry_points}</div>
        <div style="font-size: 0.875rem; opacity: 0.8;">Never called</div>
      </div>
      <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Unique Callers</h3>
        <div style="font-size: 2rem; font-weight: 700;">${stats.unique_callers}</div>
      </div>
      <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Unique Callees</h3>
        <div style="font-size: 2rem; font-weight: 700;">${stats.unique_callees}</div>
      </div>
    </div>
  `;
}
```

## Most Called Functions

Functions that are called most frequently:

```js
{
  const mostCalled = data.most_called || [];

  if (mostCalled.length === 0) {
    return html`<div style="text-align: center; padding: 2rem; color: #9ca3af;">No call data available</div>`;
  }

  return Plot.plot({
    marginLeft: 200,
    x: {label: "Call Count", grid: true},
    y: {label: null},
    marks: [
      Plot.barX(mostCalled, {
        x: "call_count",
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

## Functions with Most Outgoing Calls

Functions that make the most calls to other functions:

```js
{
  const callDepth = data.call_depth || [];

  if (callDepth.length === 0) {
    return html`<div style="text-align: center; padding: 2rem; color: #9ca3af;">No call depth data available</div>`;
  }

  return Plot.plot({
    marginLeft: 200,
    x: {label: "Outgoing Calls", grid: true},
    y: {label: null},
    marks: [
      Plot.barX(callDepth, {
        x: "outgoing_calls",
        y: "name",
        fill: "#e74c3c",
        sort: {y: "-x"},
        tip: true
      }),
      Plot.ruleX([0])
    ]
  });
}
```

## Entry Points (Potential Dead Code)

Functions that are never called - potential entry points or dead code:

```js
{
  const entryPoints = data.entry_points || [];

  if (entryPoints.length === 0) {
    return html`<div style="background: #d1fae5; border-left: 4px solid #43e97b; border-radius: 8px; padding: 1rem 1.5rem;">
      <h4 style="margin: 0 0 0.5rem 0; color: #065f46;">✅ No Uncalled Functions</h4>
      <p style="margin: 0; color: #065f46;">All functions are called at least once.</p>
    </div>`;
  }

  return Inputs.table(entryPoints.slice(0, 30), {
    columns: ["name", "module", "complexity"],
    header: {
      name: "Function",
      module: "Module",
      complexity: "Complexity"
    },
    sort: "complexity",
    reverse: true
  });
}
```

## Call Details

```js
{
  const calls = data.calls || [];
  if (calls.length === 0) return '';

  return Inputs.table(calls.slice(0, 100), {
    columns: ["caller", "callee", "caller_module", "call_kind"],
    header: {
      caller: "Caller",
      callee: "Callee",
      caller_module: "Module",
      call_kind: "Call Type"
    }
  });
}
```

---

<div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 2px solid #e5e7eb; display: flex; justify-content: space-between; font-size: 0.875rem;">
  <a href="../" style="color: #667eea; text-decoration: none;">← Home</a>
  <a href="../structural/complexity" style="color: #667eea; text-decoration: none;">← Complexity</a>
</div>
