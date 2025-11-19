# Code Age & Churn

Track file age, change frequency, and identify legacy hotspots.

```js
const repos = FileAttachment("../data/repo-list.json").json();
```

```js
const allData = FileAttachment("../data/all-code-age-metrics.json").json();
```

```js
const selectedRepo = view(Inputs.select(repos, {label: "Repository", value: repos[0]}));
```

```js
const data = allData[selectedRepo] || {};
```

## Oldest Files

Files that haven't been modified recently:

```js
{
  if (data.error) {
    return html`<div style="background: #fee2e2; border-left: 4px solid #f5576c; border-radius: 8px; padding: 1rem 1.5rem;">
      <h4 style="margin: 0 0 0.5rem 0; color: #991b1b;">⚠️ Error</h4>
      <p style="margin: 0; color: #991b1b;">${data.error}</p>
    </div>`;
  }

  const ageData = data.age_data || [];

  if (ageData.length === 0) {
    return html`<div style="text-align: center; padding: 2rem; color: #9ca3af;">No age data available</div>`;
  }

  return Plot.plot({
    marginLeft: 250,
    x: {label: "Days Since Last Change", grid: true},
    y: {label: null},
    marks: [
      Plot.barX(ageData.slice(0, 20), {
        x: "days_old",
        y: "file",
        fill: d => d.days_old > 365 ? "#f5576c" : d.days_old > 180 ? "#f093fb" : "#4facfe",
        sort: {y: "-x"},
        tip: true
      }),
      Plot.ruleX([365], {stroke: "#f5576c", strokeDasharray: "4,4"}),
      Plot.ruleX([180], {stroke: "#f093fb", strokeDasharray: "4,4"})
    ]
  });
}
```

## High Churn Files

Files with the most changes:

```js
{
  const churnData = data.churn_data || [];

  if (churnData.length === 0) {
    return html`<div style="text-align: center; padding: 2rem; color: #9ca3af;">No churn data available</div>`;
  }

  return Plot.plot({
    marginLeft: 250,
    x: {label: "Churn Score", grid: true},
    y: {label: null},
    marks: [
      Plot.barX(churnData.slice(0, 20), {
        x: "churn_score",
        y: "file",
        fill: "steelblue",
        sort: {y: "-x"},
        tip: true
      }),
      Plot.ruleX([0])
    ]
  });
}
```

## Churn Details

```js
{
  const churnData = data.churn_data || [];
  if (churnData.length === 0) return '';

  return Inputs.table(churnData, {
    columns: ["file", "changes", "lines_added", "lines_deleted", "churn_score"],
    header: {
      file: "File",
      changes: "Changes",
      lines_added: "Lines Added",
      lines_deleted: "Lines Deleted",
      churn_score: "Churn Score"
    },
    sort: "churn_score",
    reverse: true
  });
}
```

## Age Details

```js
{
  const ageData = data.age_data || [];
  if (ageData.length === 0) return '';

  return Inputs.table(ageData, {
    columns: ["file", "days_old", "last_modified"],
    header: {
      file: "File",
      days_old: "Days Old",
      last_modified: "Last Modified"
    },
    sort: "days_old",
    reverse: true
  });
}
```

---

<div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 2px solid #e5e7eb; display: flex; justify-content: space-between; font-size: 0.875rem;">
  <a href="../" style="color: #667eea; text-decoration: none;">← Home</a>
  <a href="../temporal/coupling" style="color: #667eea; text-decoration: none;">Coupling Network →</a>
</div>
