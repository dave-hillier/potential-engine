# API Boundaries

Analyze REST API endpoints, calls, and service boundaries across languages.

```js
const repos = FileAttachment("../data/repo-list.json").json();
const selectedRepo = view(Inputs.select(repos, {label: "Repository", value: repos[0]}));
```

```js
const apiData = FileAttachment("../data/api-boundaries.json.py", {cache: false}).json({
  command: ["../../../../venv/bin/python3", "../data/api-boundaries.json.py", selectedRepo]
});
```

## API Endpoint Inventory

```js
{
  if (apiData.error) {
    return html`<div class="alert alert--warning">
      <h4>⚠️ Error Loading Data</h4>
      <p>${apiData.error}</p>
    </div>`;
  }

  const endpoints = apiData.endpoints || [];
  const calls = apiData.calls || [];
  const matches = apiData.matches || [];

  if (endpoints.length === 0 && calls.length === 0) {
    return html`<div class="alert alert--info">
      <h4>ℹ️ No API Boundaries Detected</h4>
      <p>No REST endpoints or API calls found in this repository. API boundary detection looks for Flask/FastAPI routes and fetch/axios calls.</p>
    </div>`;
  }

  return html`
    <div class="grid-4">
      <div class="metric-card">
        <h3>API Endpoints</h3>
        <div class="value">${endpoints.length}</div>
        <div class="subvalue">REST routes</div>
      </div>
      <div class="metric-card metric-card--pink">
        <h3>API Calls</h3>
        <div class="value">${calls.length}</div>
        <div class="subvalue">External requests</div>
      </div>
      <div class="metric-card metric-card--green">
        <h3>Matched Pairs</h3>
        <div class="value">${matches.length}</div>
        <div class="subvalue">Internal calls</div>
      </div>
      <div class="metric-card metric-card--orange">
        <h3>Unmatched</h3>
        <div class="value">${calls.length - matches.length}</div>
        <div class="subvalue">External APIs</div>
      </div>
    </div>
  `;
}
```

## Endpoints by Method

```js
{
  const endpoints = apiData.endpoints || [];

  if (endpoints.length === 0) {
    return html`<div class="empty-state">
      <div class="empty-state-icon">🌐</div>
      <h3>No Endpoints Found</h3>
      <p>No REST API endpoints detected in this repository.</p>
    </div>`;
  }

  // Group by HTTP method
  const methodCounts = d3.rollup(
    endpoints,
    v => v.length,
    d => d.method || 'UNKNOWN'
  );

  const methodData = Array.from(methodCounts, ([method, count]) => ({
    method,
    count
  }));

  return Plot.plot({
    marginLeft: 80,
    x: {label: "Count", grid: true},
    y: {label: null},
    marks: [
      Plot.barX(methodData, {
        x: "count",
        y: "method",
        fill: d => {
          const colors = {
            'GET': '#43e97b',
            'POST': '#4facfe',
            'PUT': '#f5576c',
            'DELETE': '#f093fb',
            'PATCH': '#fa709a'
          };
          return colors[d.method] || '#667eea';
        },
        sort: {y: "-x"}
      }),
      Plot.ruleX([0])
    ]
  });
}
```

## API Endpoint Details

```js
{
  const endpoints = apiData.endpoints || [];

  if (endpoints.length === 0) {
    return '';
  }

  return Inputs.table(endpoints, {
    columns: ["method", "path", "function_name", "module_path", "line_number"],
    header: {
      method: "Method",
      path: "Endpoint Path",
      function_name: "Handler Function",
      module_path: "Module",
      line_number: "Line"
    },
    width: {
      method: 80,
      path: 200,
      function_name: 150,
      module_path: 250,
      line_number: 60
    }
  });
}
```

## API Call Network

```js
{
  const endpoints = apiData.endpoints || [];
  const calls = apiData.calls || [];
  const matches = apiData.matches || [];

  if (endpoints.length === 0 || calls.length === 0) {
    return '';
  }

  // Create nodes from endpoints and calls
  const nodes = [];
  const links = [];

  // Add endpoint nodes
  endpoints.forEach(ep => {
    nodes.push({
      id: `endpoint:${ep.path}`,
      label: `${ep.method} ${ep.path}`,
      type: 'endpoint',
      method: ep.method
    });
  });

  // Add call nodes and links
  calls.forEach(call => {
    const callId = `call:${call.url}`;
    if (!nodes.find(n => n.id === callId)) {
      nodes.push({
        id: callId,
        label: call.url,
        type: 'call',
        method: call.method
      });
    }

    // Check if this call matches an endpoint
    const match = matches.find(m =>
      m.call_url === call.url && m.endpoint_path
    );

    if (match) {
      links.push({
        source: callId,
        target: `endpoint:${match.endpoint_path}`,
        matched: true
      });
    }
  });

  return html`<div style="width: 100%; height: 600px; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden;">
    <svg id="api-network" width="100%" height="100%"></svg>
  </div>`;
}
```

```js
{
  const endpoints = apiData.endpoints || [];
  const calls = apiData.calls || [];
  const matches = apiData.matches || [];

  if (endpoints.length === 0 || calls.length === 0) {
    return '';
  }

  // Render D3 force-directed graph
  const svg = d3.select("#api-network");
  const width = svg.node().clientWidth;
  const height = svg.node().clientHeight;

  svg.selectAll("*").remove();

  // Create nodes
  const nodes = [];
  endpoints.forEach(ep => {
    nodes.push({
      id: `endpoint:${ep.path}`,
      label: `${ep.method} ${ep.path}`,
      type: 'endpoint',
      method: ep.method
    });
  });

  calls.forEach(call => {
    const callId = `call:${call.url}`;
    if (!nodes.find(n => n.id === callId)) {
      nodes.push({
        id: callId,
        label: call.url,
        type: 'call',
        method: call.method
      });
    }
  });

  // Create links
  const links = [];
  calls.forEach(call => {
    const match = matches.find(m =>
      m.call_url === call.url && m.endpoint_path
    );

    if (match) {
      links.push({
        source: `call:${call.url}`,
        target: `endpoint:${match.endpoint_path}`,
        matched: true
      });
    }
  });

  const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(150))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(30));

  const link = svg.append("g")
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("stroke", "#999")
    .attr("stroke-width", 2)
    .attr("stroke-dasharray", d => d.matched ? "0" : "5,5");

  const node = svg.append("g")
    .selectAll("g")
    .data(nodes)
    .join("g")
    .call(d3.drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended));

  node.append("circle")
    .attr("r", 8)
    .attr("fill", d => d.type === 'endpoint' ? '#43e97b' : '#4facfe');

  node.append("text")
    .attr("dx", 12)
    .attr("dy", 4)
    .text(d => d.label)
    .style("font-size", "10px")
    .style("fill", "#333");

  simulation.on("tick", () => {
    link
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);

    node.attr("transform", d => `translate(${d.x},${d.y})`);
  });

  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }

  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }

  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }
}
```

## API Call Details

```js
{
  const calls = apiData.calls || [];

  if (calls.length === 0) {
    return html`<div class="empty-state">
      <div class="empty-state-icon">📡</div>
      <h3>No API Calls Found</h3>
      <p>No API calls detected in this repository.</p>
    </div>`;
  }

  return Inputs.table(calls, {
    columns: ["method", "url", "function_name", "module_path", "line_number"],
    header: {
      method: "Method",
      url: "URL",
      function_name: "Calling Function",
      module_path: "Module",
      line_number: "Line"
    },
    width: {
      method: 80,
      url: 250,
      function_name: 150,
      module_path: 250,
      line_number: 60
    }
  });
}
```

---

<div class="footer-nav">
  <a href="../">← Home</a> |
  <a href="../cross-language/polyglot">Polyglot Overview →</a>
</div>
