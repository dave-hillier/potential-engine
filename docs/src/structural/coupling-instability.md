# Coupling & Instability

NDepend-style metrics for analyzing module stability and coupling.

```js
const repos = FileAttachment("data/repo-list.json").json();
// Note: Data shown is for the first repository. Dynamic selection not yet implemented.
const currentRepo = repos[0];
```

```js
const metrics = FileAttachment("data/instability-metrics.json").json();
```

<div style="background: #dbeafe; border-left: 4px solid #4facfe; border-radius: 8px; padding: 0.75rem 1rem; margin: 1rem 0; font-size: 0.9rem;">
  <strong>Repository:</strong> ${currentRepo} (showing first repository only)
</div>

## Overview

```js
{
  if (metrics.error) {
    return html`<div style="background: #fee2e2; border-left: 4px solid #f5576c; border-radius: 8px; padding: 1rem 1.5rem; margin: 1.5rem 0;">
      <h4 style="margin: 0 0 0.5rem 0; font-size: 1rem; font-weight: 600; color: #991b1b;">⚠️ Error Loading Data</h4>
      <p style="margin: 0; line-height: 1.5; color: #991b1b;">${metrics.error}</p>
    </div>`;
  }

  const modules = metrics.modules || [];
  const stats = metrics.statistics || {};

  if (modules.length === 0) {
    return html`<div style="background: #dbeafe; border-left: 4px solid #4facfe; border-radius: 8px; padding: 1rem 1.5rem; margin: 1.5rem 0;">
      <h4 style="margin: 0 0 0.5rem 0; font-size: 1rem; font-weight: 600; color: #1e40af;">ℹ️ No Data</h4>
      <p style="margin: 0; line-height: 1.5; color: #1e40af;">No instability metrics available for this repository.</p>
    </div>`;
  }

  const highRisk = modules.filter(m => m.classification === 'high_risk').length;
  const rigid = modules.filter(m => m.classification === 'rigid').length;

  return html`
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.5rem 0;">
      <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; padding: 1.5rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.9;">Total Modules</h3>
        <div style="font-size: 2rem; font-weight: 700; line-height: 1; margin-top: 0.5rem;">${modules.length}</div>
      </div>
      <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; border-radius: 8px; padding: 1.5rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.9;">Avg Instability</h3>
        <div style="font-size: 2rem; font-weight: 700; line-height: 1; margin-top: 0.5rem;">${stats.avg_instability}</div>
      </div>
      <div style="background: linear-gradient(135deg, #f5576c 0%, #fa709a 100%); color: white; border-radius: 8px; padding: 1.5rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.9;">High Risk</h3>
        <div style="font-size: 2rem; font-weight: 700; line-height: 1; margin-top: 0.5rem;">${highRisk}</div>
        <div style="font-size: 0.875rem; opacity: 0.8; margin-top: 0.25rem;">Unstable & coupled</div>
      </div>
      <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; border-radius: 8px; padding: 1.5rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.9;">Rigid Modules</h3>
        <div style="font-size: 2rem; font-weight: 700; line-height: 1; margin-top: 0.5rem;">${rigid}</div>
        <div style="font-size: 0.875rem; opacity: 0.8; margin-top: 0.25rem;">Stable but dependent</div>
      </div>
    </div>
  `;
}
```

## Instability Distribution

**Instability** = Ce / (Ca + Ce), where:
- **Ca** (Afferent Coupling): Incoming dependencies
- **Ce** (Efferent Coupling): Outgoing dependencies

```js
{
  const modules = metrics.modules || [];
  if (modules.length === 0) return '';

  return Plot.plot({
    marginLeft: 250,
    x: {label: "Instability", domain: [0, 1], grid: true},
    y: {label: null},
    color: {
      domain: ["high_risk", "rigid", "normal"],
      range: ["#f5576c", "#4facfe", "#43e97b"],
      legend: true
    },
    marks: [
      Plot.barX(modules.slice(0, 20), {
        x: "instability",
        y: "path",
        fill: "classification",
        sort: {y: "-x"},
        tip: true
      }),
      Plot.ruleX([0.5], {stroke: "#999", strokeDasharray: "4,4"})
    ]
  });
}
```

## Afferent Coupling (Ca)

Modules with the most incoming dependencies:

```js
{
  const modules = metrics.modules || [];
  if (modules.length === 0) return '';

  return Plot.plot({
    marginLeft: 250,
    x: {label: "Afferent Coupling (Ca)", grid: true},
    y: {label: null},
    marks: [
      Plot.barX(modules.slice(0, 15), {
        x: "ca",
        y: "path",
        fill: "steelblue",
        sort: {y: "-x"},
        tip: true
      }),
      Plot.ruleX([0])
    ]
  });
}
```

## Efferent Coupling (Ce)

Modules with the most outgoing dependencies:

```js
{
  const modules = metrics.modules || [];
  if (modules.length === 0) return '';

  return Plot.plot({
    marginLeft: 250,
    x: {label: "Efferent Coupling (Ce)", grid: true},
    y: {label: null},
    marks: [
      Plot.barX(modules.slice(0, 15), {
        x: "ce",
        y: "path",
        fill: "#e74c3c",
        sort: {y: "-x"},
        tip: true
      }),
      Plot.ruleX([0])
    ]
  });
}
```

## High-Risk Modules

Modules with high instability (> 0.8) and high afferent coupling (> 5):

```js
{
  const modules = metrics.modules || [];
  const highRisk = modules.filter(m => m.classification === 'high_risk');

  if (highRisk.length === 0) {
    return html`<div style="background: #d1fae5; border-left: 4px solid #43e97b; border-radius: 8px; padding: 1rem 1.5rem; margin: 1.5rem 0;">
      <h4 style="margin: 0 0 0.5rem 0; font-size: 1rem; font-weight: 600; color: #065f46;">✅ No High-Risk Modules</h4>
      <p style="margin: 0; line-height: 1.5; color: #065f46;">All modules have acceptable instability levels.</p>
    </div>`;
  }

  return Inputs.table(highRisk, {
    columns: ["path", "ca", "ce", "instability"],
    header: {
      path: "Module Path",
      ca: "Ca (Afferent)",
      ce: "Ce (Efferent)",
      instability: "Instability"
    }
  });
}
```

## Module Details

```js
{
  const modules = metrics.modules || [];
  if (modules.length === 0) return '';

  return Inputs.table(modules, {
    columns: ["path", "ca", "ce", "instability", "classification"],
    header: {
      path: "Module Path",
      ca: "Ca",
      ce: "Ce",
      instability: "Instability",
      classification: "Classification"
    },
    sort: "instability",
    reverse: true
  });
}
```

## About Instability Metrics

**Instability (I)** measures how resistant a module is to change:
- **I = 0**: Maximally stable (only incoming dependencies)
- **I = 1**: Maximally unstable (only outgoing dependencies)
- **I = 0.5**: Balanced

**Classifications:**
- **High Risk**: High instability (>0.8) + High afferent coupling (>5) = Many dependents but unstable
- **Rigid**: Low instability (<0.2) + High efferent coupling (>5) = Stable but many dependencies
- **Normal**: Everything else

---

<div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 2px solid #e5e7eb; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 1rem; font-size: 0.875rem;">
  <a href="../" style="color: #667eea; text-decoration: none;">← Home</a>
  <span>|</span>
  <a href="../structural/dependency-matrix" style="color: #667eea; text-decoration: none;">Dependency Matrix →</a>
</div>
