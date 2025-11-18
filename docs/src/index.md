# depanalysis Reports

Welcome to the interactive analysis dashboard for your code repositories. Explore Git history, temporal coupling, and author contributions.

## Analyzed Repositories

```js
const repos = FileAttachment("./data/repo-list.json").json();
const summaries = FileAttachment("./data/all-repos-summary.json").json();
```

```js
// Create repository cards with summary stats
const repoCards = summaries.map(repo => html`
  <a href="./repo/${repo.name}" class="repo-link">
    <h3 style="margin: 0 0 0.5rem 0;">${repo.name}</h3>
    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem; font-size: 0.9rem; color: #666;">
      <div>📝 ${repo.total_commits} commits</div>
      <div>👥 ${repo.total_authors} authors</div>
      <div>📄 ${repo.files_tracked} files</div>
      <div>🔗 ${repo.temporal_couplings} couplings</div>
    </div>
  </a>
`);
```

<div class="grid-2">
  ${repoCards}
</div>

---

## Quick Navigation

<div class="grid-2">
  <div class="card">
    <h3>🔗 Temporal Coupling</h3>
    <p>Explore files that frequently change together. Identify hidden dependencies and architectural issues.</p>
    <a href="./coupling">View Coupling Network →</a>
  </div>

  <div class="card">
    <h3>👥 Author Analytics</h3>
    <p>Analyze contributor patterns, code ownership, and collaboration dynamics across repositories.</p>
    <a href="./authors">View Author Stats →</a>
  </div>

  <div class="card">
    <h3>📊 Compare Repositories</h3>
    <p>Side-by-side comparison of metrics across multiple repositories.</p>
    <a href="./compare">Compare Repos →</a>
  </div>

  <div class="card">
    <h3>📈 All Metrics</h3>
    <p>Click on any repository above to see detailed churn metrics, code age, and temporal coupling analysis.</p>
  </div>
</div>

---

## About

This dashboard is powered by **depanalysis**, a Python tool that combines static structural analysis with temporal behavioral analysis from Git history.

**Key Metrics:**
- **Churn**: Frequency and magnitude of file changes
- **Temporal Coupling**: Files that change together (Jaccard similarity)
- **Code Age**: Time since last modification
- **Author Ownership**: Contribution patterns by developer
