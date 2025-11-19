# Repository Overview

Select a repository to view detailed analysis.

```js
const repos = FileAttachment("../data/repo-list.json").json();
const summaries = FileAttachment("../data/all-repos-summary.json").json();
```

## Analyzed Repositories

```js
// Create repository cards with summary stats
const repoCards = summaries.map(repo => html`
  <a href="./repo/${repo.name}" class="repo-link" style="display: block; background: white; border: 2px solid #e5e7eb; border-radius: 8px; padding: 1.5rem; text-decoration: none; color: #1f2937; transition: all 0.25s ease; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1); margin-bottom: 1rem;">
    <h3 style="margin: 0 0 0.5rem 0; color: #667eea; font-weight: 600;">${repo.name}</h3>
    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem; font-size: 0.9rem; color: #666;">
      <div>📝 ${repo.total_commits} commits</div>
      <div>👥 ${repo.total_authors} authors</div>
      <div>📄 ${repo.files_tracked} files</div>
      <div>🔗 ${repo.temporal_couplings} couplings</div>
    </div>
  </a>
`);
```

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin: 1.5rem 0;">
  ${repoCards}
</div>

---

<div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 2px solid #e5e7eb; font-size: 0.875rem;">
  <a href="../" style="color: #667eea; text-decoration: none;">← Home</a>
</div>
