// Observable Framework configuration
// https://observablehq.com/framework/config

export default {
  root: "src",
  title: "depanalysis Reports",
  pages: [
    {name: "Home", path: "/"},
    {
      name: "Repositories",
      open: false,
      pages: [
        {name: "Overview", path: "/repositories"}
      ]
    },
    {
      name: "Structural Analysis",
      open: false,
      pages: [
        {name: "Coupling & Instability", path: "/structural/coupling-instability"},
        {name: "Dependency Matrix", path: "/structural/dependency-matrix"},
        {name: "Complexity Distribution", path: "/structural/complexity"},
        {name: "Call Graphs", path: "/structural/call-graphs"},
        {name: "Inheritance Trees", path: "/structural/inheritance"}
      ]
    },
    {
      name: "Temporal Analysis",
      open: false,
      pages: [
        {name: "Coupling Network", path: "/temporal/coupling"},
        {name: "Code Age & Churn", path: "/temporal/age-churn"},
        {name: "Commit Patterns", path: "/temporal/commits"},
        {name: "Architecture Health", path: "/temporal/architecture-health"}
      ]
    },
    {
      name: "Cross-Language Analysis",
      open: false,
      pages: [
        {name: "API Boundaries", path: "/cross-language/api-boundaries"},
        {name: "Polyglot Overview", path: "/cross-language/polyglot"},
        {name: "Dependency Ecosystem", path: "/cross-language/dependencies"}
      ]
    },
    {
      name: "Code Quality",
      open: false,
      pages: [
        {name: "Type Safety", path: "/quality/type-safety"},
        {name: "Decorator Usage", path: "/quality/decorators"},
        {name: "Quality Metrics", path: "/quality/overview"}
      ]
    },
    {
      name: "Insights",
      open: false,
      pages: [
        {name: "Author Analytics", path: "/insights/authors"},
        {name: "Compare Repositories", path: "/insights/compare"}
      ]
    }
  ],
  search: true,
  head: '<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📊</text></svg>">',
};
