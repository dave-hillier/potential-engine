# Author Analytics

Analyze contributor patterns, code ownership, and collaboration dynamics.

```js
const repos = FileAttachment("data/repo-list.json").json();
const selectedRepo = view(Inputs.select(repos, {label: "Repository", value: repos[0]}));
```

```js
const authors = FileAttachment("data/authors.json.py", {cache: false}).json({
  command: ["../../../venv/bin/python3", "data/authors.json.py", selectedRepo]
});
```

## Contribution Overview

```js
{
  const totalCommits = d3.sum(authors, d => d.total_commits);
  const totalLines = d3.sum(authors, d => d.total_lines_added);
  const totalFiles = d3.sum(authors, d => d.files_touched);

  return html`
    <div class="grid-4">
      <div class="metric-card">
        <h3>Total Authors</h3>
        <div class="value">${authors.length}</div>
      </div>
      <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
        <h3>Total Commits</h3>
        <div class="value">${totalCommits}</div>
      </div>
      <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
        <h3>Lines Added</h3>
        <div class="value">${totalLines.toLocaleString()}</div>
      </div>
      <div class="metric-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
        <h3>Files Touched</h3>
        <div class="value">${totalFiles}</div>
      </div>
    </div>
  `;
}
```

## Commits by Author

```js
Plot.plot({
  marginLeft: 150,
  marginBottom: 60,
  x: {label: "Commits", grid: true},
  y: {label: null},
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

## Lines of Code by Author

```js
Plot.plot({
  marginLeft: 150,
  marginBottom: 60,
  x: {label: "Lines Added", grid: true},
  y: {label: null},
  marks: [
    Plot.barX(authors, {
      x: "total_lines_added",
      y: "name",
      fill: "#e74c3c",
      sort: {y: "-x"}
    }),
    Plot.ruleX([0])
  ]
})
```

## Files Touched by Author

```js
Plot.plot({
  marginLeft: 150,
  marginBottom: 60,
  x: {label: "Files", grid: true},
  y: {label: null},
  marks: [
    Plot.barX(authors, {
      x: "files_touched",
      y: "name",
      fill: "#9b59b6",
      sort: {y: "-x"}
    }),
    Plot.ruleX([0])
  ]
})
```

## Contribution Distribution

```js
Plot.plot({
  marks: [
    Plot.barY(authors, {
      x: "name",
      y: "total_commits",
      fill: "steelblue"
    })
  ],
  x: {label: null},
  y: {label: "Commits", grid: true}
})
```

## Detailed Author Statistics

```js
display(Inputs.table(authors, {
  columns: ["name", "email", "total_commits", "files_touched", "total_lines_added", "total_lines_deleted", "first_commit", "last_commit"],
  header: {
    name: "Name",
    email: "Email",
    total_commits: "Commits",
    files_touched: "Files",
    total_lines_added: "Lines Added",
    total_lines_deleted: "Lines Deleted",
    first_commit: "First Commit",
    last_commit: "Last Commit"
  },
  sort: "total_commits",
  reverse: true,
  format: {
    first_commit: d => new Date(d).toLocaleDateString(),
    last_commit: d => new Date(d).toLocaleDateString()
  }
}))
```

## Insights

```js
{
  const topAuthor = authors[0];
  const commitPercentage = ((topAuthor.total_commits / d3.sum(authors, d => d.total_commits)) * 100).toFixed(1);

  return html`
    <div class="card">
      <h3>Top Contributor</h3>
      <p><strong>${topAuthor.name}</strong> has made ${topAuthor.total_commits} commits (${commitPercentage}% of total),
      touching ${topAuthor.files_touched} files and adding ${topAuthor.total_lines_added.toLocaleString()} lines of code.</p>
    </div>
  `;
}
```

---

[← Back to Overview](./) | [View Coupling Network](./coupling) | [Compare Repositories](./compare)
