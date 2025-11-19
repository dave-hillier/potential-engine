# Commit Patterns

Development velocity, commit frequency, and activity trends.

```js
const repos = FileAttachment("../data/repo-list.json").json();
```

```js
// Get the first repository name
const currentRepo = (await repos)[0];
```

```js
const data = FileAttachment("../data/commit-patterns.json").json();
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
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Total Commits</h3>
        <div style="font-size: 2rem; font-weight: 700;">${stats.total_commits}</div>
      </div>
      <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Contributors</h3>
        <div style="font-size: 2rem; font-weight: 700;">${stats.total_authors}</div>
      </div>
      <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">First Commit</h3>
        <div style="font-size: 1rem; font-weight: 700;">${stats.first_commit ? new Date(stats.first_commit).toLocaleDateString() : 'N/A'}</div>
      </div>
      <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Last Commit</h3>
        <div style="font-size: 1rem; font-weight: 700;">${stats.last_commit ? new Date(stats.last_commit).toLocaleDateString() : 'N/A'}</div>
      </div>
    </div>
  `;
}
```

## Weekly Commit Trend

```js
{
  const weeklyTrend = data.weekly_trend || [];

  if (weeklyTrend.length === 0) {
    return html`<div style="text-align: center; padding: 2rem; color: #9ca3af;">No commit trend data available</div>`;
  }

  return Plot.plot({
    marginBottom: 60,
    x: {label: "Week", tickRotate: -45},
    y: {label: "Commits", grid: true},
    marks: [
      Plot.lineY(weeklyTrend.reverse(), {
        x: "week",
        y: "count",
        stroke: "#667eea",
        strokeWidth: 2
      }),
      Plot.areaY(weeklyTrend, {
        x: "week",
        y: "count",
        fill: "#667eea",
        fillOpacity: 0.1
      }),
      Plot.dot(weeklyTrend, {
        x: "week",
        y: "count",
        fill: "#667eea",
        r: 3
      })
    ]
  });
}
```

## Most Active Files (Last 30 Days)

```js
{
  const activeAreas = data.active_areas || [];

  if (activeAreas.length === 0) {
    return html`<div style="background: #dbeafe; border-left: 4px solid #4facfe; border-radius: 8px; padding: 1rem 1.5rem;">
      <h4 style="margin: 0 0 0.5rem 0; color: #1e40af;">ℹ️ No Recent Activity</h4>
      <p style="margin: 0; color: #1e40af;">No commits in the last 30 days.</p>
    </div>`;
  }

  return Plot.plot({
    marginLeft: 250,
    x: {label: "Recent Commits (30 days)", grid: true},
    y: {label: null},
    marks: [
      Plot.barX(activeAreas, {
        x: "recent_commits",
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

## Commit Activity Heatmap (Day/Hour)

```js
{
  const commitsByTime = data.commits_by_time || [];

  if (commitsByTime.length === 0) {
    return html`<div style="text-align: center; padding: 2rem; color: #9ca3af;">No commit timing data available</div>`;
  }

  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  return Plot.plot({
    padding: 0,
    x: {label: "Hour of Day", domain: d3.range(24)},
    y: {label: "Day of Week", domain: d3.range(7), tickFormat: d => dayNames[d]},
    color: {scheme: "Blues", legend: true, label: "Commits"},
    marks: [
      Plot.cell(commitsByTime, {
        x: "hour",
        y: "day",
        fill: "count",
        tip: true,
        title: d => `${dayNames[d.day]} ${d.hour}:00 - ${d.count} commits`
      })
    ]
  });
}
```

## Active Development Areas

```js
{
  const activeAreas = data.active_areas || [];
  if (activeAreas.length === 0) return '';

  return Inputs.table(activeAreas, {
    columns: ["file", "recent_commits", "last_commit"],
    header: {
      file: "File Path",
      recent_commits: "Recent Commits",
      last_commit: "Last Commit"
    },
    format: {
      last_commit: d => new Date(d).toLocaleDateString()
    },
    sort: "recent_commits",
    reverse: true
  });
}
```

---

<div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 2px solid #e5e7eb; display: flex; justify-content: space-between; font-size: 0.875rem;">
  <a href="../" style="color: #667eea; text-decoration: none;">← Home</a>
  <a href="../temporal/age-churn" style="color: #667eea; text-decoration: none;">← Age & Churn</a>
</div>
