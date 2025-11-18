# Migration Progress Dashboard

Track progress of large refactoring efforts and migration projects.

```js
// Get repository and migration ID from URL params
const urlParams = new URLSearchParams(window.location.search);
const repoName = urlParams.get("repo") || "example-repo";
const migrationId = urlParams.get("id") || "python2to3";
```

```js
// Load migration data
const data = FileAttachment(`data/migration-progress.json?repo=${repoName}&id=${migrationId}`).json();
```

## ${data.migration?.name || "Migration Project"}

**Repository:** ${data.repo_name}
**Description:** ${data.migration?.description || "No description"}
**Target Date:** ${data.migration?.targetDate || "Not set"}

---

## Summary

<div class="grid grid-cols-4">
  <div class="card">
    <h2>${data.summary?.totalOccurrences || 0}</h2>
    <p>Total Occurrences</p>
  </div>
  <div class="card">
    <h2>${data.summary?.affectedFiles || 0}</h2>
    <p>Affected Files</p>
  </div>
  <div class="card">
    <h2>${data.summary?.patterns || 0}</h2>
    <p>Patterns Tracked</p>
  </div>
  <div class="card">
    <h2>${data.migration?.tags?.join(", ") || "None"}</h2>
    <p>Tags</p>
  </div>
</div>

---

## Occurrences by Severity

```js
const severityData = Object.entries(data.summary?.bySeverity || {}).map(([severity, count]) => ({
  severity,
  count,
  color: getSeverityColor(severity)
}));

function getSeverityColor(severity) {
  const colors = {
    critical: "#dc2626",
    high: "#ea580c",
    medium: "#f59e0b",
    low: "#84cc16",
    info: "#06b6d4"
  };
  return colors[severity] || "#6b7280";
}
```

```js
Plot.plot({
  marginLeft: 80,
  x: {label: "Occurrences"},
  y: {label: null},
  color: {legend: true},
  marks: [
    Plot.barX(severityData, {
      x: "count",
      y: "severity",
      fill: "color",
      sort: {y: "-x"}
    }),
    Plot.text(severityData, {
      x: "count",
      y: "severity",
      text: d => `${d.count}`,
      dx: -10,
      fill: "white",
      fontWeight: "bold"
    })
  ]
})
```

---

## Patterns

Top patterns by occurrence count:

```js
Inputs.table(data.patterns || [], {
  columns: ["name", "severity", "category", "occurrences", "affectedFiles", "description"],
  header: {
    name: "Pattern",
    severity: "Severity",
    category: "Category",
    occurrences: "Occurrences",
    affectedFiles: "Files",
    description: "Description"
  },
  width: {
    name: 200,
    description: 300
  },
  sort: "occurrences",
  reverse: true
})
```

---

## Most Affected Files

Files with the most migration pattern occurrences:

```js
// Group file data by path (sum across severities)
const fileMap = new Map();
(data.files || []).forEach(f => {
  if (!fileMap.has(f.path)) {
    fileMap.set(f.path, {path: f.path, occurrences: 0, severities: [], patterns: []});
  }
  const file = fileMap.get(f.path);
  file.occurrences += f.occurrences;
  file.severities.push(f.severity);
  file.patterns.push(...f.patterns);
});

const topFiles = Array.from(fileMap.values())
  .sort((a, b) => b.occurrences - a.occurrences)
  .slice(0, 20);
```

```js
Plot.plot({
  marginLeft: 250,
  height: Math.max(300, topFiles.length * 25),
  x: {label: "Occurrences"},
  y: {label: null},
  marks: [
    Plot.barX(topFiles, {
      x: "occurrences",
      y: "path",
      fill: "#3b82f6",
      sort: {y: "-x"}
    }),
    Plot.text(topFiles, {
      x: "occurrences",
      y: "path",
      text: d => `${d.occurrences}`,
      dx: 5,
      textAnchor: "start",
      fontSize: 11
    })
  ]
})
```

### File Details

```js
Inputs.table(topFiles, {
  columns: ["path", "occurrences", "patterns"],
  header: {
    path: "File Path",
    occurrences: "Total Occurrences",
    patterns: "Patterns Found"
  },
  format: {
    patterns: p => p.join(", ")
  },
  width: {
    path: 400,
    patterns: 300
  }
})
```

---

## Progress Over Time

${data.timeline?.length > 0 ? "Migration scan history:" : "No historical data available yet. Run scans periodically to track progress."}

```js
if (data.timeline?.length > 0) {
  display(Plot.plot({
    marginBottom: 50,
    x: {label: "Scan Date", tickRotate: -45},
    y: {label: "Total Occurrences"},
    marks: [
      Plot.line(data.timeline, {x: "date", y: "occurrences", stroke: "#3b82f6", strokeWidth: 2}),
      Plot.dot(data.timeline, {x: "date", y: "occurrences", fill: "#3b82f6", r: 4}),
      Plot.text(data.timeline, {
        x: "date",
        y: "occurrences",
        text: d => `${d.occurrences}`,
        dy: -10,
        fontSize: 11
      })
    ]
  }));
}
```

---

## How to Use

1. **Define migration patterns** in a YAML configuration file (see `migrations/*.example.yml`)
2. **Scan your repository:**
   ```bash
   depanalysis migration scan /path/to/repo --config migrations/python2to3.yml
   ```
3. **Track progress over time** by running scans periodically (weekly/monthly)
4. **View this dashboard** to identify high-priority files and track migration completion

### Example Commands

```bash
# Scan for Python 2→3 migration patterns
depanalysis migration scan . --config migrations/python2to3.yml

# View progress
depanalysis migration progress my-repo python2to3

# Re-scan to track changes
depanalysis migration scan . --config migrations/python2to3.yml
```
