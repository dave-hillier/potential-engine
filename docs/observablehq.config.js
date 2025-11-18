// Observable Framework configuration
// https://observablehq.com/framework/config

export default {
  root: "src",
  title: "depanalysis Reports",
  pages: [
    {name: "Overview", path: "/"},
    {name: "Temporal Coupling", path: "/coupling"},
    {name: "Author Analytics", path: "/authors"},
    {name: "Compare Repositories", path: "/compare"}
  ],
  head: '<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📊</text></svg>">',
};
