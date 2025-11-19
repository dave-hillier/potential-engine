# Repository: simple-linear

```js
const churn = FileAttachment("../data/simple-linear-churn.json").json();
const coupling = FileAttachment("../data/simple-linear-coupling.json").json();
const authors = FileAttachment("../data/simple-linear-authors.json").json();
```

```js
// Calculate summary stats
const totalCommits = authors.reduce((sum, a) => sum + a.total_commits, 0);
const totalFiles = churn.length;
const totalCouplings = coupling.length;
const totalAuthors = authors.length;
```

<div class="grid-4">
  <div class="metric-card">
    <h3>Commits</h3>
    <div class="value">${totalCommits}</div>
  </div>
  <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
    <h3>Authors</h3>
    <div class="value">${totalAuthors}</div>
  </div>
  <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
    <h3>Files</h3>
    <div class="value">${totalFiles}</div>
  </div>
  <div class="metric-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
    <h3>Couplings</h3>
    <div class="value">${totalCouplings}</div>
  </div>
</div>

## 🔥 File Churn Analysis

Files with the most changes (lines added + deleted):

```js
Plot.plot({
  marginLeft: 150,
  marginBottom: 60,
  x: {label: "Total Churn (lines)", grid: true},
  y: {label: null},
  marks: [
    Plot.barX(churn.slice(0, 10), {
      x: "total_churn",
      y: "file_path",
      fill: "steelblue",
      sort: {y: "-x"}
    }),
    Plot.ruleX([0])
  ]
})
```

## 🔗 Temporal Coupling

${totalCouplings > 0 ? html`
Files that frequently change together:

${Inputs.table(coupling.slice(0, 20), {
  columns: ["file_a", "file_b", "co_change_count", "jaccard_similarity"],
  header: {
    file_a: "File A",
    file_b: "File B",
    co_change_count: "Co-changes",
    jaccard_similarity: "Similarity"
  },
  format: {
    jaccard_similarity: d => d.toFixed(3)
  }
})}
` : html`<p style="color: #999; font-style: italic;">No temporal coupling detected in this repository.</p>`}

## 👥 Author Contributions

```js
Plot.plot({
  marginLeft: 150,
  marginBottom: 60,
  x: {label: "Commits", grid: true},
  y: {label: null},
  color: {legend: true},
  marks: [
    Plot.barX(authors, {
      x: "total_commits",
      y: "name",
      fill: "steelblue",
      sort: {y: "-x"}
    }),
    Plot.ruleX([0])
  ]
})
```

## 📈 Detailed Churn Metrics

```js
display(Inputs.table(churn, {
  columns: ["file_path", "total_commits", "total_lines_added", "total_lines_deleted", "total_churn", "author_count"],
  header: {
    file_path: "File",
    total_commits: "Commits",
    total_lines_added: "Added",
    total_lines_deleted: "Deleted",
    total_churn: "Churn",
    author_count: "Authors"
  },
  sort: "total_churn",
  reverse: true
}))
```

---

[← Back to Overview](../) | [View All Coupling](../coupling) | [View All Authors](../authors)
