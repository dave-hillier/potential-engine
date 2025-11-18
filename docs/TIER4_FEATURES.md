# Tier 4: Integration & Ecosystem Features

This document describes the Tier 4 features implemented for depanalysis, focusing on making architectural insights actionable through integration with development workflows.

## Overview

Tier 4 features transform depanalysis from an analysis tool into an integrated part of the development ecosystem:

- **Feature 11**: IDE Integration - Real-time feedback while coding
- **Feature 12**: CI/CD Gates - Enforce architectural rules in pipelines
- **Feature 13**: Pull Request Enrichment - Automated PR impact analysis
- **Feature 14**: Migration Planning - Track large refactoring efforts

---

## Feature 12: CI/CD Gates 🚦

### Purpose

Enforce architectural rules automatically in CI/CD pipelines, preventing code that violates architectural constraints from being merged.

### Components

1. **Configuration System** (`.depanalysis.yml`)
2. **CLI Validation Command**
3. **GitHub Actions Integration**

### Quick Start

#### 1. Create Configuration File

Copy the example configuration:

```bash
cp .depanalysis.example.yml .depanalysis.yml
```

Edit thresholds for your project:

```yaml
thresholds:
  coupling:
    max_instability: 0.8
  complexity:
    max_cyclomatic_complexity: 15
  churn:
    max_file_churn: 100
  temporal_coupling:
    max_temporal_coupling_similarity: 0.9

circular_dependencies:
  allow: false

forbidden_imports:
  - from: "ui/*"
    to: "database/*"
    reason: "UI should not access database directly"
```

#### 2. Validate Locally

```bash
# Analyze repository
depanalysis analyze-repo .

# Validate against rules
depanalysis validate $(basename $(pwd))
```

Output example:

```
Validating my-project against architectural rules...
Configuration: .depanalysis.yml
======================================================================

❌ ERRORS (2):
----------------------------------------------------------------------
  Module app/ui/views.py has instability 0.95 (max: 0.8)
  High temporal coupling between auth.py and user.py: 0.92 (max: 0.9)

⚠️  WARNINGS (3):
----------------------------------------------------------------------
  Function complex_handler in api.py has complexity 18 (max: 15)
  File models.py has 42 functions (max: 30)
  File database.py has churn 150 (max: 100)

======================================================================
Summary: 2 errors, 3 warnings

❌ Validation failed (errors found)
```

#### 3. Add to CI/CD Pipeline

**GitHub Actions** (`.github/workflows/architecture-validation.yml`):

```yaml
name: Architecture Validation

on:
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install depanalysis
        run: pip install -e .

      - name: Analyze repository
        run: depanalysis analyze-repo .

      - name: Validate rules
        run: |
          depanalysis validate $(basename $(pwd)) \
            --fail-on-error \
            --no-fail-on-warning
```

### Configuration Reference

#### Coupling Thresholds

```yaml
thresholds:
  coupling:
    max_efferent_coupling: 20      # Max outgoing dependencies
    max_afferent_coupling: 50      # Max incoming dependencies
    max_instability: 0.8           # Ce / (Ca + Ce)
```

**Instability Metric**:
- 0.0 = Completely stable (many incoming, few outgoing)
- 1.0 = Completely unstable (many outgoing, few incoming)
- Core domain: < 0.3, Infrastructure: < 0.8

#### Complexity Thresholds

```yaml
thresholds:
  complexity:
    max_cyclomatic_complexity: 15  # Per function
    max_file_complexity: 100       # Per file (total)
```

#### Temporal Coupling

```yaml
thresholds:
  temporal_coupling:
    max_temporal_coupling_similarity: 0.9   # Error threshold
    warn_temporal_coupling_similarity: 0.7  # Warning threshold
```

#### Forbidden Imports (Layer Violations)

```yaml
forbidden_imports:
  - from: "ui/*"
    to: "database/*"
    reason: "UI layer should not access database directly"

  - from: "domain/*"
    to: "infrastructure/*"
    reason: "Domain should not depend on infrastructure"
```

### CLI Options

```bash
depanalysis validate <repo-name> [OPTIONS]

Options:
  --config PATH              Config file path (default: .depanalysis.yml)
  --fail-on-error            Exit with code 1 if errors found (default: true)
  --fail-on-warning          Exit with code 2 if warnings found (default: false)
```

---

## Feature 14: Migration Planning 🔄

### Purpose

Track progress of large refactoring efforts like Python 2→3 migrations, framework upgrades, or deprecation tracking.

### Quick Start

#### 1. Define Migration Patterns

Create `migrations/python2to3.yml`:

```yaml
migration_id: "python2to3"
name: "Python 2 to 3 Migration"
description: "Track migration from Python 2 to Python 3"
target_completion_date: "2024-12-31"

patterns:
  - id: "print_statement"
    name: "Print Statement"
    description: "Python 2 print statement"
    type: "regex"
    pattern: '^\s*print\s+(?!\()'
    severity: "high"
    replacement: "Use print() function"

  - id: "raw_input"
    name: "raw_input() function"
    type: "call"
    pattern: "raw_input"
    severity: "critical"
    replacement: "Replace with input()"
```

#### 2. Scan for Patterns

```bash
depanalysis migration scan . --config migrations/python2to3.yml
```

Output:

```
Migration: Python 2 to 3 Migration
Patterns: 2
======================================================================

Scanning: Print Statement (high)...
  Found: 15 occurrences
    src/utils.py:42 - print 'Processing...'
    src/api.py:18 - print "Starting server"
    ... and 13 more

Scanning: raw_input() function (critical)...
  Found: 3 occurrences
    src/cli.py:25 - raw_input
    ... and 2 more

======================================================================
Total occurrences: 18
Affected files: 8
```

#### 3. Track Progress Over Time

Run scans periodically (weekly/monthly):

```bash
# Week 1
depanalysis migration scan . --config migrations/python2to3.yml

# After fixes...

# Week 2
depanalysis migration scan . --config migrations/python2to3.yml
```

#### 4. View Progress Dashboard

```bash
depanalysis migration progress my-repo python2to3
```

Or visit the Observable dashboard:
```
http://localhost:3000/migration?repo=my-repo&id=python2to3
```

### Pattern Types

#### Regex Patterns

Search for code patterns using regular expressions:

```yaml
- id: "percent_formatting"
  type: "regex"
  pattern: '"\s*%[sd]'
  description: "Old-style % string formatting"
```

#### Import Patterns

Find specific imports:

```yaml
- id: "future_division"
  type: "import"
  pattern: "from __future__ import division"
```

#### Call Patterns

Find function/method calls:

```yaml
- id: "deprecated_api"
  type: "call"
  pattern: "old_function_name"
```

### Use Cases

#### Python 2 → 3 Migration

See `migrations/python2to3.example.yml` for complete patterns.

#### Framework Migration

```yaml
migration_id: "flask-to-fastapi"
name: "Flask to FastAPI Migration"

patterns:
  - id: "flask_route"
    type: "regex"
    pattern: '@app\.route\('

  - id: "flask_import"
    type: "import"
    pattern: "from flask import"
```

#### Deprecation Tracking

```yaml
migration_id: "deprecated-apis"
name: "Deprecated API Cleanup"

patterns:
  - id: "old_config_api"
    type: "call"
    pattern: "load_legacy_config"
    severity: "medium"
```

---

## Feature 13: Pull Request Enrichment 📊

### Purpose

Automatically analyze the architectural impact of pull requests and post comments with metrics comparison.

### Quick Start

#### 1. Enable GitHub Action

Add `.github/workflows/pr-enrichment.yml` (already provided).

#### 2. Create Pull Request

When you open a PR, the workflow automatically:

1. Analyzes architectural diff (base branch → PR branch)
2. Compares metrics (coupling, complexity, etc.)
3. Posts comment with impact analysis

Example comment:

```markdown
## 📊 Architectural Impact Analysis

**Comparing:** `main` → `feature-branch`
**Files Changed:** 8

**Overall Impact:** ⚠️ MIXED

### Summary
- ✅ Metrics Improved: 2
- ⚠️  Metrics Degraded: 3
- ➖ Metrics Unchanged: 5

### Key Changes

| Metric | Change | Impact |
|--------|--------|--------|
| avg_cyclomatic_complexity | +12.5% | ⚠️ |
| total_imports | -5.0% | ✅ |
| max_efferent_coupling | +15.0% | ⚠️ |

### ⚠️  Degraded Metrics

- **avg_cyclomatic_complexity**: 8.5 → 9.6 (+12.5%)
- **max_efferent_coupling**: 12 → 14 (+15.0%)

### ✅ Improved Metrics

- **total_imports**: 45 → 43 (-5.0%)
```

#### 3. Use CLI for Local Diff

Before creating PR:

```bash
# Compare current branch against main
depanalysis diff . main

# Save report to file
depanalysis diff . main --output pr-impact.md
```

### Diff Analysis Metrics

- **Total counts**: modules, classes, functions, imports
- **Coupling**: Average and max efferent/afferent coupling
- **Complexity**: Average and max cyclomatic complexity
- **Files changed**: Count and list

---

## Feature 11: IDE Integration 💡

### Purpose

Provide real-time architectural feedback while coding, with warnings for hotspots, coupling, and other issues.

### Current Status

**Foundation implemented** - Ready for LSP integration.

Components:
- `depanalysis/ide_integration.py` - Core insight engine
- `ide-integration/vscode-extension-template/` - VS Code extension template

### Capabilities

#### File Insights

Get architectural insights for any file:

```python
from depanalysis.ide_integration import IDEIntegration
from depanalysis.db_manager import DatabaseManager

db_manager = DatabaseManager()
integration = IDEIntegration("my-repo", db_manager)

insights = integration.get_file_insights("src/api.py")

print(insights.is_hotspot)        # True if high churn + complexity
print(insights.churn)             # Total changes
print(insights.complexity)        # Average complexity
print(insights.efferent_coupling) # Outgoing dependencies
print(insights.warnings)          # List of warnings
print(insights.suggestions)       # List of suggestions
```

#### Import Impact Analysis

Check impact before adding an import:

```python
impact = integration.get_import_impact("src/service.py", "external_lib")

print(impact["impact_level"])     # "low", "medium", or "high"
print(impact["new_coupling"])     # Coupling after import
print(impact["message"])          # Human-readable message
```

### VS Code Extension (Template)

See `ide-integration/vscode-extension-template/README.md` for:

- Complete implementation guide
- LSP server setup (using `pygls`)
- Extension client setup (TypeScript)
- Visual indicators for hotspots
- Hover tooltips with metrics
- Real-time diagnostics

**To implement:**

1. Follow template README
2. Install dependencies (`pygls`, `vscode-languageclient`)
3. Build and package extension
4. Publish to VS Code Marketplace

---

## Configuration Examples

### Strict Layered Architecture

```yaml
# .depanalysis.yml
thresholds:
  coupling:
    max_instability: 0.7
  complexity:
    max_cyclomatic_complexity: 10

circular_dependencies:
  allow: false

forbidden_imports:
  - from: "presentation/*"
    to: "data/*"
    reason: "Presentation layer should use domain, not data layer"

  - from: "domain/*"
    to: "presentation/*"
    reason: "Domain should not depend on presentation"
```

### Microservices

```yaml
thresholds:
  coupling:
    max_efferent_coupling: 10  # Low coupling between services
  temporal_coupling:
    max_temporal_coupling_similarity: 0.5  # Services should change independently
```

### Legacy Modernization

```yaml
# Start with high thresholds, gradually decrease
thresholds:
  complexity:
    max_cyclomatic_complexity: 25  # → 20 → 15 → 10
  churn:
    max_file_churn: 200  # → 150 → 100
```

---

## Best Practices

### CI/CD Gates

1. **Start lenient, tighten gradually**: Begin with high thresholds, decrease over time
2. **Warn before failing**: Use `--no-fail-on-warning` initially
3. **Granular rules**: Different thresholds for different directories
4. **Document violations**: Comment PRs with explanations

### Migration Planning

1. **Scan regularly**: Weekly or bi-weekly to track progress
2. **Prioritize by severity**: Fix critical patterns first
3. **Combine with Git history**: Identify stable vs changing files
4. **Set realistic dates**: Based on current occurrence counts

### PR Enrichment

1. **Review before merging**: Check architectural impact in PR comments
2. **Require approvals for degradation**: If metrics worsen significantly
3. **Archive reports**: Keep diff reports for future reference
4. **Track trends**: Compare multiple PRs over time

### IDE Integration

1. **Start with warnings**: Don't block development initially
2. **Focus on hotspots**: Highlight high-risk files
3. **Provide context**: Show who last modified, when
4. **Suggest refactorings**: Link to architectural best practices

---

## Troubleshooting

### "Repository not found in database"

```bash
# Ensure repository is analyzed first
depanalysis analyze-repo /path/to/repo
depanalysis list  # Verify it's in the list
```

### "Configuration file not found"

```bash
# Create from example
cp .depanalysis.example.yml .depanalysis.yml
```

### Diff analysis fails

```bash
# Ensure full Git history is available
git fetch --unshallow

# Verify base ref exists
git branch -a | grep origin/main
```

### Migration scan finds nothing

- Check `file_patterns` in migration config
- Verify files are not in `.gitignore`
- Test regex patterns with `grep` first

---

## Future Enhancements

Planned for future tiers:

- **Real-time LSP server**: Full IDE integration with pygls
- **GitHub App**: Automatic PR comments without Actions
- **Slack/Teams integration**: Notifications for violations
- **Grafana dashboards**: Time-series metrics tracking
- **AI-powered suggestions**: LLM-based refactoring recommendations

---

## References

- [ROADMAP.md](../ROADMAP.md) - Full feature roadmap
- [CLAUDE.md](../CLAUDE.md) - Project architecture overview
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [VS Code Extension API](https://code.visualstudio.com/api)
- [Language Server Protocol](https://microsoft.github.io/language-server-protocol/)
