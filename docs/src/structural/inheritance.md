# Inheritance Trees

Class hierarchies, interface implementations, and OOP design patterns.

```js
const repos = FileAttachment("../data/repo-list.json").json();
```

```js
// Get the first repository name
const currentRepo = (await repos)[0];
```

```js
const data = FileAttachment("../data/inheritance-tree.json").json();
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

  if (stats.total_relationships === 0) {
    return html`<div style="background: #dbeafe; border-left: 4px solid #4facfe; border-radius: 8px; padding: 1rem 1.5rem;">
      <h4 style="margin: 0 0 0.5rem 0; color: #1e40af;">ℹ️ No Inheritance Data</h4>
      <p style="margin: 0; color: #1e40af;">No inheritance relationships detected in this repository.</p>
    </div>`;
  }

  return html`
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.5rem 0;">
      <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Total Relationships</h3>
        <div style="font-size: 2rem; font-weight: 700;">${stats.total_relationships}</div>
      </div>
      <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Child Classes</h3>
        <div style="font-size: 2rem; font-weight: 700;">${stats.unique_children}</div>
      </div>
      <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Parent Classes</h3>
        <div style="font-size: 2rem; font-weight: 700;">${stats.unique_parents}</div>
      </div>
    </div>
  `;
}
```

## Class Types

```js
{
  const classKinds = data.class_kinds || [];

  if (classKinds.length === 0) return '';

  return Plot.plot({
    marginLeft: 120,
    x: {label: "Count", grid: true},
    y: {label: null},
    marks: [
      Plot.barX(classKinds, {
        x: "count",
        y: "kind",
        fill: "kind",
        sort: {y: "-x"},
        tip: true
      }),
      Plot.ruleX([0])
    ]
  });
}
```

## Most Extended Classes

Base classes with the most child classes:

```js
{
  const mostExtended = data.most_extended || [];

  if (mostExtended.length === 0) {
    return html`<div style="text-align: center; padding: 2rem; color: #9ca3af;">No inheritance data available</div>`;
  }

  return Plot.plot({
    marginLeft: 200,
    x: {label: "Child Class Count", grid: true},
    y: {label: null},
    marks: [
      Plot.barX(mostExtended, {
        x: "child_count",
        y: "class",
        fill: "steelblue",
        sort: {y: "-x"},
        tip: true
      }),
      Plot.ruleX([0])
    ]
  });
}
```

## Inheritance Depth

Classes with the most parent classes (multiple inheritance):

```js
{
  const depthAnalysis = data.depth_analysis || [];

  if (depthAnalysis.length === 0) return '';

  const multipleInheritance = depthAnalysis.filter(d => d.parent_count > 1);

  if (multipleInheritance.length > 0) {
    return html`<div>
      <div style="background: #fee2e2; border-left: 4px solid #f5576c; border-radius: 8px; padding: 1rem 1.5rem; margin-bottom: 1rem;">
        <h4 style="margin: 0 0 0.5rem 0; color: #991b1b;">⚠️ Multiple Inheritance Detected</h4>
        <p style="margin: 0; color: #991b1b;">${multipleInheritance.length} class(es) inherit from multiple parents.</p>
      </div>
      ${Inputs.table(depthAnalysis.slice(0, 20), {
        columns: ["class", "module", "parent_count"],
        header: {
          class: "Class",
          module: "Module",
          parent_count: "Parent Count"
        },
        sort: "parent_count",
        reverse: true
      })}
    </div>`;
  }

  return Inputs.table(depthAnalysis.slice(0, 20), {
    columns: ["class", "module", "parent_count"],
    header: {
      class: "Class",
      module: "Module",
      parent_count: "Parent Count"
    },
    sort: "parent_count",
    reverse: true
  });
}
```

## Inheritance Relationships

```js
{
  const relationships = data.relationships || [];
  if (relationships.length === 0) return '';

  return Inputs.table(relationships, {
    columns: ["child", "parent", "child_module", "kind"],
    header: {
      child: "Child Class",
      parent: "Parent Class",
      child_module: "Module",
      kind: "Relationship Type"
    }
  });
}
```

---

<div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 2px solid #e5e7eb; display: flex; justify-content: space-between; font-size: 0.875rem;">
  <a href="../" style="color: #667eea; text-decoration: none;">← Home</a>
  <a href="../structural/call-graphs" style="color: #667eea; text-decoration: none;">← Call Graphs</a>
</div>
