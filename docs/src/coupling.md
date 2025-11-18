# Temporal Coupling Explorer

Explore files that frequently change together across all repositories.

```js
const repos = FileAttachment("./data/repo-list.json").json();
const allCoupling = FileAttachment("./data/all-coupling.json").json();
```

```js
const selectedRepo = view(Inputs.select(repos, {label: "Repository", value: repos[0]}));
```

```js
const coupling = allCoupling.filter(d => d.repo_name === selectedRepo);
```

## Network Visualization

Files are represented as nodes, and edges show temporal coupling strength. Thicker edges indicate stronger coupling (higher Jaccard similarity).

```js
coupling.length === 0
  ? html`<div style="padding: 3rem; text-align: center; color: #999;">
      <p style="font-size: 1.2rem;">No temporal coupling detected in this repository.</p>
      <p>This means files tend to change independently rather than together.</p>
    </div>`
  : (() => {
      // Build nodes and links
      const nodesMap = new Map();
      coupling.forEach(d => {
        if (!nodesMap.has(d.file_a)) nodesMap.set(d.file_a, {id: d.file_a});
        if (!nodesMap.has(d.file_b)) nodesMap.set(d.file_b, {id: d.file_b});
      });

      const nodes = Array.from(nodesMap.values());
      const links = coupling.map(d => ({
        source: d.file_a,
        target: d.file_b,
        value: d.jaccard_similarity,
        coChanges: d.co_change_count
      }));

      const width = 928;
      const height = 600;

      const simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(d => d.id).distance(100))
        .force("charge", d3.forceManyBody().strength(-400))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide(30));

      const svg = d3.create("svg")
        .attr("width", width)
        .attr("height", height)
        .attr("viewBox", [0, 0, width, height])
        .attr("style", "max-width: 100%; height: auto; background: white; border: 1px solid #ddd; border-radius: 8px;");

      const link = svg.append("g")
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6)
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke-width", d => Math.sqrt(d.value * 10))
        .append("title")
          .text(d => `${d.source.id} ↔ ${d.target.id}\nSimilarity: ${d.value.toFixed(3)}\nCo-changes: ${d.coChanges}`);

      const node = svg.append("g")
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5)
        .selectAll("circle")
        .data(nodes)
        .join("circle")
        .attr("r", 8)
        .attr("fill", "#3498db")
        .call(drag(simulation));

      node.append("title")
        .text(d => d.id);

      const label = svg.append("g")
        .selectAll("text")
        .data(nodes)
        .join("text")
        .text(d => d.id)
        .attr("font-size", 11)
        .attr("dx", 12)
        .attr("dy", 4);

      simulation.on("tick", () => {
        link
          .attr("x1", d => d.source.x)
          .attr("y1", d => d.source.y)
          .attr("x2", d => d.target.x)
          .attr("y2", d => d.target.y);

        node
          .attr("cx", d => d.x)
          .attr("cy", d => d.y);

        label
          .attr("x", d => d.x)
          .attr("y", d => d.y);
      });

      function drag(simulation) {
        function dragstarted(event) {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          event.subject.fx = event.subject.x;
          event.subject.fy = event.subject.y;
        }

        function dragged(event) {
          event.subject.fx = event.x;
          event.subject.fy = event.y;
        }

        function dragended(event) {
          if (!event.active) simulation.alphaTarget(0);
          event.subject.fx = null;
          event.subject.fy = null;
        }

        return d3.drag()
          .on("start", dragstarted)
          .on("drag", dragged)
          .on("end", dragended);
      }

      return svg.node();
    })()
```

## Coupling Details

```js
display(Inputs.table(coupling, {
  columns: ["file_a", "file_b", "co_change_count", "jaccard_similarity"],
  header: {
    file_a: "File A",
    file_b: "File B",
    co_change_count: "Co-changes",
    jaccard_similarity: "Jaccard Similarity"
  },
  format: {
    jaccard_similarity: d => d.toFixed(3)
  },
  sort: "jaccard_similarity",
  reverse: true
}))
```

## Interpretation

- **Jaccard Similarity**: Measures how often files change together. A value of 1.0 means files always change together; 0.0 means they never do.
- **Co-change Count**: The number of commits where both files were modified.
- **Strong Coupling (>0.7)**: Files with high similarity may indicate:
  - Tight logical coupling (e.g., models and serializers)
  - Missing abstractions or modularity issues
  - Opportunities for refactoring

---

[← Back to Overview](./) | [View Author Analytics](./authors) | [Compare Repositories](./compare)
