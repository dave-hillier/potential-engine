# Architecture Health Dashboard

Comprehensive analysis combining structural and temporal metrics to identify maintenance bottlenecks and architectural issues.

```js
const repos = FileAttachment("../data/repo-list.json").json();
```

```js
// Get the first repository name
const currentRepo = (await repos)[0];
```

```js
const hotspots = FileAttachment("../data/hotspots.json").json();
const cycles = FileAttachment("../data/circular-dependencies.json").json();
const hiddenDeps = FileAttachment("../data/hidden-dependencies.json").json();
```

<div style="background: #dbeafe; border-left: 4px solid #4facfe; border-radius: 8px; padding: 0.75rem 1rem; margin: 1rem 0; font-size: 0.9rem;">
  <strong>Repository:</strong> ${currentRepo}
</div>

## 🔥 Hotspots

Hotspots are files with **high complexity + high churn + high coupling** — the most critical maintenance bottlenecks.

**Hotspot Score** = Complexity × Churn × (Coupling + 1)

```js
hotspots.length === 0
  ? html`<div style="padding: 2rem; text-align: center; color: #666; background: #f9f9f9; border-radius: 8px;">
      <p style="font-size: 1.1rem;">✅ No significant hotspots detected!</p>
      <p>All files have manageable complexity, churn, and coupling levels.</p>
    </div>`
  : Inputs.table(hotspots, {
      columns: [
        "file_path",
        "hotspot_score",
        "total_complexity",
        "total_churn",
        "efferent_coupling",
        "afferent_coupling",
        "function_count"
      ],
      header: {
        file_path: "File",
        hotspot_score: "Hotspot Score",
        total_complexity: "Complexity",
        total_churn: "Churn",
        efferent_coupling: "Ce (Out)",
        afferent_coupling: "Ca (In)",
        function_count: "Functions"
      },
      format: {
        hotspot_score: x => x.toFixed(0),
        total_complexity: x => x.toFixed(0),
        total_churn: x => x.toFixed(0)
      },
      width: {
        file_path: 300
      },
      rows: 20
    })
```

### Top Hotspots Visualization

```js
hotspots.length > 0
  ? (() => {
      const topHotspots = hotspots.slice(0, 10);

      const width = 928;
      const height = 400;
      const marginTop = 20;
      const marginRight = 40;
      const marginBottom = 100;
      const marginLeft = 60;

      const x = d3.scaleBand()
        .domain(topHotspots.map(d => d.file_path))
        .range([marginLeft, width - marginRight])
        .padding(0.2);

      const y = d3.scaleLinear()
        .domain([0, d3.max(topHotspots, d => d.hotspot_score)])
        .nice()
        .range([height - marginBottom, marginTop]);

      const svg = d3.create("svg")
        .attr("width", width)
        .attr("height", height)
        .attr("viewBox", [0, 0, width, height])
        .attr("style", "max-width: 100%; height: auto; background: white; border: 1px solid #ddd; border-radius: 8px;");

      svg.append("g")
        .attr("transform", `translate(0,${height - marginBottom})`)
        .call(d3.axisBottom(x).tickSize(0))
        .selectAll("text")
          .attr("transform", "rotate(-45)")
          .style("text-anchor", "end")
          .attr("dx", "-0.8em")
          .attr("dy", "0.15em");

      svg.append("g")
        .attr("transform", `translate(${marginLeft},0)`)
        .call(d3.axisLeft(y))
        .call(g => g.select(".domain").remove())
        .call(g => g.selectAll(".tick line").clone()
          .attr("x2", width - marginLeft - marginRight)
          .attr("stroke-opacity", 0.1));

      const colorScale = d3.scaleSequential()
        .domain([0, d3.max(topHotspots, d => d.hotspot_score)])
        .interpolator(d3.interpolateYlOrRd);

      svg.append("g")
        .selectAll("rect")
        .data(topHotspots)
        .join("rect")
          .attr("x", d => x(d.file_path))
          .attr("y", d => y(d.hotspot_score))
          .attr("height", d => y(0) - y(d.hotspot_score))
          .attr("width", x.bandwidth())
          .attr("fill", d => colorScale(d.hotspot_score))
          .append("title")
            .text(d => `${d.file_path}\nScore: ${d.hotspot_score.toFixed(0)}\nComplexity: ${d.total_complexity}\nChurn: ${d.total_churn}\nCoupling: ${d.efferent_coupling + d.afferent_coupling}`);

      svg.append("text")
        .attr("x", width / 2)
        .attr("y", marginTop / 2)
        .attr("text-anchor", "middle")
        .attr("font-weight", "bold")
        .text("Top 10 Maintenance Hotspots");

      return svg.node();
    })()
  : html``
```

---

## ♻️ Circular Dependencies

Circular dependencies create tight coupling and make code harder to test, understand, and maintain.

```js
cycles.length === 0
  ? html`<div style="padding: 2rem; text-align: center; color: #666; background: #f0f8ff; border-radius: 8px;">
      <p style="font-size: 1.1rem;">✅ No circular dependencies detected!</p>
      <p>Your module dependency graph is acyclic.</p>
    </div>`
  : html`<div style="padding: 1rem; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px; margin: 1rem 0;">
      <p style="margin: 0;"><strong>⚠️ ${cycles.length} circular ${cycles.length === 1 ? 'dependency' : 'dependencies'} detected</strong></p>
      <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem;">Consider refactoring to break these cycles.</p>
    </div>`
```

```js
cycles.length > 0
  ? Inputs.table(cycles, {
      columns: ["cycle_id", "cycle_length", "files"],
      header: {
        cycle_id: "Cycle #",
        cycle_length: "Length",
        files: "Dependency Chain"
      },
      width: {
        files: 600
      }
    })
  : html``
```

---

## 🔗 Hidden Dependencies

Files with high temporal coupling but no structural coupling — they change together but don't import each other. This may indicate missing abstractions or feature entanglement.

```js
hiddenDeps.length === 0
  ? html`<div style="padding: 2rem; text-align: center; color: #666; background: #f9f9f9; border-radius: 8px;">
      <p style="font-size: 1.1rem;">✅ No hidden dependencies detected</p>
      <p>Files that change together have appropriate structural relationships.</p>
    </div>`
  : html`<div style="padding: 1rem; background: #e7f3ff; border-left: 4px solid #2196f3; border-radius: 4px; margin: 1rem 0;">
      <p style="margin: 0;"><strong>💡 ${hiddenDeps.length} hidden ${hiddenDeps.length === 1 ? 'dependency' : 'dependencies'} found</strong></p>
      <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem;">These files change together frequently but don't import each other.</p>
    </div>`
```

```js
hiddenDeps.length > 0
  ? Inputs.table(hiddenDeps, {
      columns: ["file1", "file2", "jaccard_similarity", "co_change_count"],
      header: {
        file1: "File 1",
        file2: "File2",
        jaccard_similarity: "Similarity",
        co_change_count: "Co-changes"
      },
      format: {
        jaccard_similarity: x => x.toFixed(3)
      },
      width: {
        file1: 300,
        file2: 300
      },
      rows: 20
    })
  : html``
```

---

## 📊 Summary

```js
html`<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 2rem 0;">
  <div style="padding: 1.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">${hotspots.length}</div>
    <div style="font-size: 0.9rem; opacity: 0.9;">Hotspots</div>
  </div>
  <div style="padding: 1.5rem; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">${cycles.length}</div>
    <div style="font-size: 0.9rem; opacity: 0.9;">Circular Dependencies</div>
  </div>
  <div style="padding: 1.5rem; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; border-radius: 8px; text-align: center;">
    <div style="font-size: 2rem; font-weight: bold;">${hiddenDeps.length}</div>
    <div style="font-size: 0.9rem; opacity: 0.9;">Hidden Dependencies</div>
  </div>
</div>`
```

---

## 💡 Recommendations

${hotspots.length > 0 ? html`<div style="padding: 1rem; background: #fff; border: 1px solid #ddd; border-radius: 8px; margin: 1rem 0;">
  <h3 style="margin-top: 0;">🔥 Address Hotspots First</h3>
  <p>Focus refactoring efforts on the top 3-5 hotspots. These files have the highest maintenance burden.</p>
  <ul>
    <li>Break down complex functions (high cyclomatic complexity)</li>
    <li>Extract reusable components (reduce coupling)</li>
    <li>Add comprehensive tests before refactoring (high churn means high risk)</li>
  </ul>
</div>` : html``}

${cycles.length > 0 ? html`<div style="padding: 1rem; background: #fff; border: 1px solid #ddd; border-radius: 8px; margin: 1rem 0;">
  <h3 style="margin-top: 0;">♻️ Break Circular Dependencies</h3>
  <p>Circular dependencies make code harder to test and understand. Break cycles by:</p>
  <ul>
    <li>Introducing interfaces/abstractions</li>
    <li>Moving shared code to a new module</li>
    <li>Using dependency injection</li>
  </ul>
</div>` : html``}

${hiddenDeps.length > 0 ? html`<div style="padding: 1rem; background: #fff; border: 1px solid #ddd; border-radius: 8px; margin: 1rem 0;">
  <h3 style="margin-top: 0;">🔗 Investigate Hidden Dependencies</h3>
  <p>Files that change together without structural coupling may indicate:</p>
  <ul>
    <li>Missing abstractions or shared utilities</li>
    <li>Feature entanglement across modules</li>
    <li>Parallel changes that could be coordinated</li>
  </ul>
</div>` : html``}
