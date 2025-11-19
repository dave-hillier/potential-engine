# Quality Metrics

Combined quality scores, technical debt indicators, and recommendations.

```js
const repos = FileAttachment("../data/repo-list.json").json();
```

```js
// Get the first repository name
const currentRepo = (await repos)[0];
```

```js
const data = FileAttachment("../data/quality-overview.json").json();
```

<div style="background: #dbeafe; border-left: 4px solid #4facfe; border-radius: 8px; padding: 0.75rem 1rem; margin: 1rem 0; font-size: 0.9rem;">
  <strong>Repository:</strong> ${currentRepo}
</div>

## Quality Scores

```js
{
  if (data.error) {
    return html`<div style="background: #fee2e2; border-left: 4px solid #f5576c; border-radius: 8px; padding: 1rem 1.5rem;">
      <h4 style="margin: 0 0 0.5rem 0; color: #991b1b;">⚠️ Error</h4>
      <p style="margin: 0; color: #991b1b;">${data.error}</p>
    </div>`;
  }

  const scores = data.scores || {};

  const getColor = (score) => {
    if (score >= 80) return 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)';
    if (score >= 60) return 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)';
    if (score >= 40) return 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)';
    return 'linear-gradient(135deg, #f5576c 0%, #fa709a 100%)';
  };

  return html`
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.5rem 0;">
      <div style="background: ${getColor(scores.overall)}; color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Overall Quality</h3>
        <div style="font-size: 2.5rem; font-weight: 700;">${scores.overall}</div>
        <div style="font-size: 0.875rem; opacity: 0.8;">out of 100</div>
      </div>
      <div style="background: ${getColor(scores.complexity)}; color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Complexity Score</h3>
        <div style="font-size: 2rem; font-weight: 700;">${scores.complexity}</div>
      </div>
      <div style="background: ${getColor(scores.type_safety)}; color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Type Safety Score</h3>
        <div style="font-size: 2rem; font-weight: 700;">${scores.type_safety}</div>
      </div>
      <div style="background: ${getColor(scores.instability)}; color: white; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; opacity: 0.9;">Stability Score</h3>
        <div style="font-size: 2rem; font-weight: 700;">${scores.instability}</div>
      </div>
    </div>
  `;
}
```

## Quality Breakdown

```js
{
  const scores = data.scores || {};
  const scoreData = [
    {metric: "Complexity", score: scores.complexity},
    {metric: "Type Safety", score: scores.type_safety},
    {metric: "Stability", score: scores.instability}
  ];

  return Plot.plot({
    marginLeft: 120,
    x: {label: "Score (0-100)", domain: [0, 100], grid: true},
    y: {label: null},
    marks: [
      Plot.barX(scoreData, {
        x: "score",
        y: "metric",
        fill: d => {
          if (d.score >= 80) return "#43e97b";
          if (d.score >= 60) return "#4facfe";
          if (d.score >= 40) return "#f093fb";
          return "#f5576c";
        },
        tip: true
      }),
      Plot.ruleX([80], {stroke: "#43e97b", strokeDasharray: "4,4"}),
      Plot.ruleX([60], {stroke: "#4facfe", strokeDasharray: "4,4"}),
      Plot.ruleX([40], {stroke: "#f5576c", strokeDasharray: "4,4"})
    ]
  });
}
```

## Complexity Metrics

```js
{
  const complexity = data.complexity_metrics || {};

  return html`
    <div style="background: #f9fafb; border-radius: 8px; padding: 1.5rem; margin: 1.5rem 0;">
      <h3 style="margin: 0 0 1rem 0; color: #374151;">Complexity Analysis</h3>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
        <div>
          <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 0.25rem;">Average Complexity</div>
          <div style="font-size: 1.5rem; font-weight: 600; color: #1f2937;">${complexity.avg_complexity}</div>
        </div>
        <div>
          <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 0.25rem;">Max Complexity</div>
          <div style="font-size: 1.5rem; font-weight: 600; color: #1f2937;">${complexity.max_complexity}</div>
        </div>
        <div>
          <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 0.25rem;">High Complexity Functions</div>
          <div style="font-size: 1.5rem; font-weight: 600; color: ${complexity.high_complexity_count > 10 ? '#f5576c' : '#43e97b'};">${complexity.high_complexity_count}</div>
          <div style="font-size: 0.75rem; color: #9ca3af;">> 15 complexity</div>
        </div>
        <div>
          <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 0.25rem;">Total Functions</div>
          <div style="font-size: 1.5rem; font-weight: 600; color: #1f2937;">${complexity.total_functions}</div>
        </div>
      </div>
    </div>
  `;
}
```

## Type Safety Metrics

```js
{
  const typeMetrics = data.type_metrics || {};

  return html`
    <div style="background: #f9fafb; border-radius: 8px; padding: 1.5rem; margin: 1.5rem 0;">
      <h3 style="margin: 0 0 1rem 0; color: #374151;">Type Safety Analysis</h3>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
        <div>
          <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 0.25rem;">Coverage</div>
          <div style="font-size: 1.5rem; font-weight: 600; color: ${typeMetrics.coverage_percent >= 80 ? '#43e97b' : typeMetrics.coverage_percent >= 50 ? '#4facfe' : '#f5576c'};">${typeMetrics.coverage_percent}%</div>
        </div>
        <div>
          <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 0.25rem;">Typed Functions</div>
          <div style="font-size: 1.5rem; font-weight: 600; color: #1f2937;">${typeMetrics.typed_functions}</div>
        </div>
        <div>
          <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 0.25rem;">Total Functions</div>
          <div style="font-size: 1.5rem; font-weight: 600; color: #1f2937;">${typeMetrics.total_functions}</div>
        </div>
      </div>
    </div>
  `;
}
```

## Stability Metrics

```js
{
  const instability = data.instability_metrics || {};

  return html`
    <div style="background: #f9fafb; border-radius: 8px; padding: 1.5rem; margin: 1.5rem 0;">
      <h3 style="margin: 0 0 1rem 0; color: #374151;">Stability Analysis</h3>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
        <div>
          <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 0.25rem;">Average Instability</div>
          <div style="font-size: 1.5rem; font-weight: 600; color: #1f2937;">${instability.avg_instability}</div>
          <div style="font-size: 0.75rem; color: #9ca3af;">0 = stable, 1 = unstable</div>
        </div>
        <div>
          <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 0.25rem;">High Risk Modules</div>
          <div style="font-size: 1.5rem; font-weight: 600; color: ${instability.high_risk_modules > 0 ? '#f5576c' : '#43e97b'};">${instability.high_risk_modules}</div>
          <div style="font-size: 0.75rem; color: #9ca3af;">Unstable + coupled</div>
        </div>
      </div>
    </div>
  `;
}
```

## Recommendations

```js
{
  const complexity = data.complexity_metrics || {};
  const typeMetrics = data.type_metrics || {};
  const instability = data.instability_metrics || {};
  const scores = data.scores || {};

  const recommendations = [];

  if (complexity.high_complexity_count > 10) {
    recommendations.push({
      priority: "high",
      area: "Complexity",
      issue: `${complexity.high_complexity_count} functions have cyclomatic complexity > 15`,
      action: "Refactor complex functions into smaller, more manageable units"
    });
  }

  if (typeMetrics.coverage_percent < 50) {
    recommendations.push({
      priority: "high",
      area: "Type Safety",
      issue: `Only ${typeMetrics.coverage_percent}% of functions have type hints`,
      action: "Add type hints to improve code maintainability and catch errors early"
    });
  }

  if (instability.high_risk_modules > 0) {
    recommendations.push({
      priority: "medium",
      area: "Stability",
      issue: `${instability.high_risk_modules} modules are highly unstable with many dependents`,
      action: "Stabilize high-risk modules or reduce their coupling"
    });
  }

  if (scores.overall < 60) {
    recommendations.push({
      priority: "high",
      area: "Overall Quality",
      issue: `Quality score is ${scores.overall}/100`,
      action: "Focus on improving complexity, type safety, and stability metrics"
    });
  }

  if (recommendations.length === 0) {
    return html`<div style="background: #d1fae5; border-left: 4px solid #43e97b; border-radius: 8px; padding: 1rem 1.5rem;">
      <h4 style="margin: 0 0 0.5rem 0; color: #065f46;">✅ Excellent Code Quality!</h4>
      <p style="margin: 0; color: #065f46;">No major quality issues detected. Keep up the good work!</p>
    </div>`;
  }

  return html`<div>
    <h3 style="margin: 1.5rem 0 1rem 0; color: #374151;">Improvement Recommendations</h3>
    ${recommendations.map(rec => html`
      <div style="background: ${rec.priority === 'high' ? '#fee2e2' : '#fef3c7'}; border-left: 4px solid ${rec.priority === 'high' ? '#f5576c' : '#f59e0b'}; border-radius: 8px; padding: 1rem 1.5rem; margin-bottom: 1rem;">
        <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
          <span style="background: ${rec.priority === 'high' ? '#f5576c' : '#f59e0b'}; color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-right: 0.5rem;">${rec.priority}</span>
          <h4 style="margin: 0; color: #374151;">${rec.area}</h4>
        </div>
        <p style="margin: 0 0 0.5rem 0; color: #6b7280;"><strong>Issue:</strong> ${rec.issue}</p>
        <p style="margin: 0; color: #6b7280;"><strong>Action:</strong> ${rec.action}</p>
      </div>
    `)}
  </div>`;
}
```

---

<div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 2px solid #e5e7eb; display: flex; justify-content: space-between; font-size: 0.875rem;">
  <a href="../" style="color: #667eea; text-decoration: none;">← Home</a>
  <a href="../quality/decorators" style="color: #667eea; text-decoration: none;">← Decorators</a>
</div>
