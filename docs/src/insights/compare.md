# Compare Repositories

Side-by-side comparison of metrics across multiple repositories.

```js
const summaries = FileAttachment("../data/all-repos-summary.json").json();
```

## Repository Overview Comparison

```js
display(Inputs.table(summaries, {
  columns: ["name", "total_commits", "total_authors", "files_tracked", "temporal_couplings"],
  header: {
    name: "Repository",
    total_commits: "Commits",
    total_authors: "Authors",
    files_tracked: "Files",
    temporal_couplings: "Couplings"
  },
  sort: "total_commits",
  reverse: true
}))
```

## Commits Comparison

```js
Plot.plot({
  marginLeft: 150,
  marginBottom: 60,
  x: {label: "Commits", grid: true},
  y: {label: null},
  marks: [
    Plot.barX(summaries, {
      x: "total_commits",
      y: "name",
      fill: "steelblue",
      sort: {y: "-x"}
    }),
    Plot.ruleX([0])
  ]
})
```

## Files Tracked Comparison

```js
Plot.plot({
  marginLeft: 150,
  marginBottom: 60,
  x: {label: "Files", grid: true},
  y: {label: null},
  marks: [
    Plot.barX(summaries, {
      x: "files_tracked",
      y: "name",
      fill: "#e74c3c",
      sort: {y: "-x"}
    }),
    Plot.ruleX([0])
  ]
})
```

## Temporal Coupling Comparison

```js
Plot.plot({
  marginLeft: 150,
  marginBottom: 60,
  x: {label: "Coupling Relationships", grid: true},
  y: {label: null},
  marks: [
    Plot.barX(summaries, {
      x: "temporal_couplings",
      y: "name",
      fill: "#9b59b6",
      sort: {y: "-x"}
    }),
    Plot.ruleX([0])
  ]
})
```

## Multi-dimensional Comparison

```js
Plot.plot({
  grid: true,
  x: {label: "Total Commits"},
  y: {label: "Temporal Couplings"},
  r: {label: "Files Tracked", range: [3, 20]},
  color: {legend: true},
  marks: [
    Plot.dot(summaries, {
      x: "total_commits",
      y: "temporal_couplings",
      r: "files_tracked",
      fill: "name",
      stroke: "white",
      strokeWidth: 2,
      tip: true,
      title: d => `${d.name}\n${d.total_commits} commits\n${d.files_tracked} files\n${d.temporal_couplings} couplings`
    })
  ]
})
```

## Repository Characteristics

```js
{
  return html`
    <div class="grid-2">
      ${summaries.map(repo => html`
        <div class="card">
          <h3><a href="./repo/${repo.name}">${repo.name}</a></h3>
          <table style="width: 100%; font-size: 0.9rem;">
            <tr>
              <td style="color: #666;">Commits:</td>
              <td style="text-align: right;"><strong>${repo.total_commits}</strong></td>
            </tr>
            <tr>
              <td style="color: #666;">Authors:</td>
              <td style="text-align: right;"><strong>${repo.total_authors}</strong></td>
            </tr>
            <tr>
              <td style="color: #666;">Files:</td>
              <td style="text-align: right;"><strong>${repo.files_tracked}</strong></td>
            </tr>
            <tr>
              <td style="color: #666;">Couplings:</td>
              <td style="text-align: right;"><strong>${repo.temporal_couplings}</strong></td>
            </tr>
            <tr>
              <td style="color: #666;">Date Range:</td>
              <td style="text-align: right; font-size: 0.8rem;">${new Date(repo.first_commit).toLocaleDateString()}<br>to ${new Date(repo.last_commit).toLocaleDateString()}</td>
            </tr>
          </table>
        </div>
      `)}
    </div>
  `;
}
```

## Insights

```js
{
  const mostCommits = summaries.reduce((a, b) => a.total_commits > b.total_commits ? a : b);
  const mostCoupling = summaries.reduce((a, b) => a.temporal_couplings > b.temporal_couplings ? a : b);
  const mostFiles = summaries.reduce((a, b) => a.files_tracked > b.files_tracked ? a : b);

  return html`
    <div class="grid-2">
      <div class="card">
        <h3>Most Active</h3>
        <p><strong>${mostCommits.name}</strong> has the most commits (${mostCommits.total_commits})</p>
      </div>
      <div class="card">
        <h3>Highest Coupling</h3>
        <p><strong>${mostCoupling.name}</strong> has the most temporal coupling relationships (${mostCoupling.temporal_couplings})</p>
      </div>
      <div class="card">
        <h3>Largest Codebase</h3>
        <p><strong>${mostFiles.name}</strong> has the most files tracked (${mostFiles.files_tracked})</p>
      </div>
      <div class="card">
        <h3>Total Overview</h3>
        <p>${summaries.length} repositories analyzed with ${d3.sum(summaries, d => d.total_commits)} total commits</p>
      </div>
    </div>
  `;
}
```

---

[← Back to Overview](./) | [Dependency Matrix](./dependency-matrix) | [Coupling Network](./coupling) | [Author Analytics](./authors)
