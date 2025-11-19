# Dependency Structure Matrix (DSM)

Explore structural and temporal coupling between files in an NDepend-style dependency matrix.

```js
const repos = FileAttachment("data/repo-list.json").json();
const currentRepo = repos[0];
```

```js
const matrixType = view(Inputs.radio(
  ["structural", "temporal"],
  {
    label: "Coupling Type",
    value: "temporal",
    format: (d) => d === "structural" ? "Structural (Imports)" : "Temporal (Co-changes)"
  }
));
```

<div style="background: #dbeafe; border-left: 4px solid #4facfe; border-radius: 8px; padding: 0.75rem 1rem; margin: 1rem 0; font-size: 0.9rem;">
  <strong>Repository:</strong> ${currentRepo}
</div>

```js
// Load data for both matrix types (defaults to first repo)
const structuralData = FileAttachment("data/structural-coupling-matrix.json").json();
const temporalData = FileAttachment("data/temporal-coupling-matrix.json").json();

const matrixData = matrixType === "structural" ? structuralData : temporalData;
```

```js
// Directory collapse/expand state
const collapsedDirs = new Set();
```

## Dependency Matrix

The dependency matrix shows relationships between files. Rows represent source files, columns represent target files.

- **Structural coupling**: Import dependencies (source imports target)
- **Temporal coupling**: Files that change together (symmetric relationship)
- **Darker cells**: Stronger coupling
- **Hierarchical grouping**: Files grouped by directory (click directory labels to expand/collapse)

```js
if (!matrixData || matrixData.files.length === 0) {
  display(html`<div style="padding: 3rem; text-align: center; color: #999;">
    <p style="font-size: 1.2rem;">No ${matrixType} coupling data available for this repository.</p>
    ${matrixType === "structural"
      ? html`<p>Structural analysis requires parsing source code into structure.db.</p>`
      : html`<p>Temporal coupling requires Git history analysis.</p>`}
  </div>`);
} else {
  // Matrix visualization
  const files = matrixData.files;
  const matrix = matrixData.matrix;
  const directories = matrixData.directories;

  // Configuration
  const cellSize = 12;
  const labelWidth = 200;
  const labelHeight = 200;
  const dirHeaderSize = 20;
  const margin = {top: labelHeight + dirHeaderSize, right: 20, bottom: 20, left: labelWidth + dirHeaderSize};

  const width = Math.max(600, files.length * cellSize);
  const height = Math.max(600, files.length * cellSize);

  // Create SVG container with zoom
  const svg = d3.create("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .attr("viewBox", [0, 0, width + margin.left + margin.right, height + margin.top + margin.bottom])
    .attr("style", "max-width: 100%; height: auto; background: white; border: 1px solid #ddd; border-radius: 8px;");

  // Create zoom behavior
  const zoom = d3.zoom()
    .scaleExtent([0.5, 10])
    .on("zoom", (event) => {
      g.attr("transform", event.transform);
      topLabels.attr("transform", `translate(${event.transform.x + margin.left}, 0) scale(${event.transform.k}, 1)`);
      leftLabels.attr("transform", `translate(0, ${event.transform.y + margin.top}) scale(1, ${event.transform.k})`);
    });

  svg.call(zoom);

  // Main group for matrix
  const g = svg.append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  // Color scale
  const maxValue = d3.max(matrix.flatMap(row => row.cells.map(c => c.value))) || 1;
  const colorScale = matrixType === "structural"
    ? d3.scaleSequential(d3.interpolateBlues).domain([0, Math.min(maxValue, 10)])
    : d3.scaleSequential(d3.interpolateReds).domain([0, 1]);

  // Draw matrix cells
  const cells = g.append("g")
    .selectAll("rect")
    .data(matrix.flatMap(row => row.cells.map(cell => ({...cell, row: row.row}))))
    .join("rect")
    .attr("x", d => d.col * cellSize)
    .attr("y", d => d.row * cellSize)
    .attr("width", cellSize - 1)
    .attr("height", cellSize - 1)
    .attr("fill", d => colorScale(d.value))
    .attr("stroke", "white")
    .attr("stroke-width", 0.5);

  // Add tooltips
  cells.append("title")
    .text(d => {
      const source = files[d.row].path;
      const target = files[d.col].path;
      if (matrixType === "structural") {
        return `${source} → ${target}\nImports: ${d.value}`;
      } else {
        return `${source} ↔ ${target}\nJaccard Similarity: ${d.value.toFixed(3)}`;
      }
    });

  // Directory separators and labels
  const dirSeparators = g.append("g");
  const dirEntries = Object.entries(directories);

  dirEntries.forEach(([dirName, range]) => {
    const startY = range.start * cellSize;
    const endY = range.end * cellSize;
    const startX = range.start * cellSize;
    const endX = range.end * cellSize;

    // Horizontal separator
    dirSeparators.append("line")
      .attr("x1", 0)
      .attr("x2", width)
      .attr("y1", endY)
      .attr("y2", endY)
      .attr("stroke", "#666")
      .attr("stroke-width", 1)
      .attr("stroke-opacity", 0.3);

    // Vertical separator
    dirSeparators.append("line")
      .attr("x1", endX)
      .attr("x2", endX)
      .attr("y1", 0)
      .attr("y2", height)
      .attr("stroke", "#666")
      .attr("stroke-width", 1)
      .attr("stroke-opacity", 0.3);
  });

  // Top directory headers
  const topDirHeaders = svg.append("g")
    .attr("transform", `translate(${margin.left}, ${margin.top - dirHeaderSize})`)
    .selectAll("text")
    .data(dirEntries)
    .join("text")
    .attr("x", d => (d[1].start + d[1].end) / 2 * cellSize)
    .attr("y", 10)
    .attr("text-anchor", "middle")
    .attr("font-size", 11)
    .attr("font-weight", "bold")
    .attr("fill", "#333")
    .text(d => d[0]);

  // Left directory headers
  const leftDirHeaders = svg.append("g")
    .attr("transform", `translate(${margin.left - dirHeaderSize}, ${margin.top})`)
    .selectAll("text")
    .data(dirEntries)
    .join("text")
    .attr("x", -10)
    .attr("y", d => (d[1].start + d[1].end) / 2 * cellSize)
    .attr("text-anchor", "end")
    .attr("dominant-baseline", "middle")
    .attr("font-size", 11)
    .attr("font-weight", "bold")
    .attr("fill", "#333")
    .text(d => d[0]);

  // File labels (top)
  const topLabels = svg.append("g")
    .attr("class", "top-labels")
    .attr("transform", `translate(${margin.left}, 0)`);

  topLabels.selectAll("text")
    .data(files)
    .join("text")
    .attr("x", (d, i) => i * cellSize + cellSize / 2)
    .attr("y", margin.top - 5)
    .attr("text-anchor", "start")
    .attr("dominant-baseline", "middle")
    .attr("transform", (d, i) => `rotate(-45, ${i * cellSize + cellSize / 2}, ${margin.top - 5})`)
    .attr("font-size", 9)
    .attr("fill", "#666")
    .text(d => {
      const name = d.name || d.path.split('/').pop();
      return name.length > 30 ? name.substring(0, 27) + "..." : name;
    });

  // File labels (left)
  const leftLabels = svg.append("g")
    .attr("class", "left-labels")
    .attr("transform", `translate(0, ${margin.top})`);

  leftLabels.selectAll("text")
    .data(files)
    .join("text")
    .attr("x", margin.left - 5)
    .attr("y", (d, i) => i * cellSize + cellSize / 2)
    .attr("text-anchor", "end")
    .attr("dominant-baseline", "middle")
    .attr("font-size", 9)
    .attr("fill", "#666")
    .text(d => {
      const name = d.name || d.path.split('/').pop();
      return name.length > 30 ? name.substring(0, 27) + "..." : name;
    });

  // Legend
  const legendWidth = 200;
  const legendHeight = 20;
  const legend = svg.append("g")
    .attr("transform", `translate(${margin.left}, ${height + margin.top + 10})`);

  const legendScale = d3.scaleLinear()
    .domain([0, legendWidth])
    .range(colorScale.domain());

  const legendAxis = d3.axisBottom(d3.scaleLinear().domain(colorScale.domain()).range([0, legendWidth]))
    .ticks(5)
    .tickFormat(d => matrixType === "structural" ? d.toFixed(0) : d.toFixed(2));

  legend.selectAll("rect")
    .data(d3.range(legendWidth))
    .join("rect")
    .attr("x", d => d)
    .attr("y", 0)
    .attr("width", 1)
    .attr("height", legendHeight)
    .attr("fill", d => colorScale(legendScale(d)));

  legend.append("g")
    .attr("transform", `translate(0, ${legendHeight})`)
    .call(legendAxis);

  legend.append("text")
    .attr("x", legendWidth / 2)
    .attr("y", -5)
    .attr("text-anchor", "middle")
    .attr("font-size", 11)
    .attr("fill", "#333")
    .text(matrixType === "structural" ? "Import Count" : "Jaccard Similarity");

  display(svg.node());
}
```

## Matrix Statistics

```js
if (matrixData && matrixData.files.length > 0) {
  const totalFiles = matrixData.files.length;
  const totalDependencies = matrixData.matrix.reduce((sum, row) => sum + row.cells.length, 0);
  const avgDepsPerFile = (totalDependencies / totalFiles).toFixed(2);
  const directoryCount = Object.keys(matrixData.directories).length;

  const stats = [
    {metric: "Total Files", value: totalFiles},
    {metric: "Total Directories", value: directoryCount},
    {metric: matrixType === "structural" ? "Total Imports" : "Total Couplings", value: totalDependencies},
    {metric: matrixType === "structural" ? "Avg Imports/File" : "Avg Couplings/File", value: avgDepsPerFile}
  ];

  display(Inputs.table(stats, {
    columns: ["metric", "value"],
    header: {
      metric: "Metric",
      value: "Value"
    }
  }));
}
```

## Interpretation

### Structural Coupling (Imports)
- **Upper triangle**: Module A imports from Module B
- **Lower triangle**: Module B imports from Module A
- **Diagonal clustering**: Files within same directory tend to depend on each other
- **Dark cells far from diagonal**: Cross-cutting dependencies that may indicate coupling issues

### Temporal Coupling (Co-changes)
- **Symmetric**: Both triangles show the same relationship
- **High values (>0.7)**: Files that almost always change together
- **May indicate**: Tight logical coupling, missing abstractions, or natural API/implementation pairs

### Best Practices
- **Structural**: Dependencies should flow in one direction (minimize cycles)
- **Temporal**: High temporal coupling without structural coupling suggests hidden dependencies
- **Both**: Strong clustering within directories indicates good modularity

---

[← Back to Overview](./) | [Network View](./coupling) | [Author Analytics](./authors)
