# Test Suite for depanalysis

This directory contains comprehensive test coverage for the dependency analysis tool, focusing on coupling analysis.

## Test Structure

### Test Files

- **`test_temporal_coupling.py`** - Tests for Git history-based temporal coupling analysis
- **`test_structural_coupling.py`** - Tests for AST-based structural coupling analysis
- **`test_integration.py`** - End-to-end integration tests
- **`conftest.py`** - Pytest fixtures and test utilities

## Test Coverage

### Temporal Coupling (Git History Analysis)

**Coverage**: 18 test cases

**Areas tested**:
- ✅ Jaccard similarity calculation for file pairs
- ✅ Co-change counting accuracy
- ✅ Perfect coupling (Jaccard = 1.0) detection
- ✅ Independent files (no coupling) handling
- ✅ Ordered file pairs (file_a < file_b)
- ✅ File deletion behavior
- ✅ Single file repositories
- ✅ Churn metrics (total commits, lines added/deleted, author count)
- ✅ Author ownership calculation
- ✅ High temporal coupling view (co_change >= 3, Jaccard >= 0.3)
- ✅ Code age metrics
- ✅ Author statistics aggregation

**Key test scenarios**:
1. Files that always change together → Jaccard similarity = 1.0
2. Files that never change together → No coupling entry
3. Files deleted after co-changing → Retain historical coupling
4. Multiple authors modifying same files → Ownership tracking

### Structural Coupling (AST Analysis)

**Coverage**: 22 test cases

**File-to-file coupling via imports**:
- ✅ Import relationship tracking
- ✅ Efferent coupling (Ce) - outgoing dependencies
- ✅ Afferent coupling (Ca) - incoming dependencies
- ✅ Instability metric (Ce / (Ca + Ce))
- ✅ Stability metric (1 - instability)
- ✅ Circular dependency detection
- ✅ Import kinds (import, require, using, include, use)
- ✅ Relative vs absolute imports
- ✅ Multiple imports from same module
- ✅ Zero coupling for isolated modules
- ✅ No self-dependencies validation

**Class-to-class coupling**:
- ✅ Inheritance relationships
- ✅ Multi-level inheritance chains
- ✅ Interface implementation
- ✅ Multiple inheritance
- ✅ Method call relationships between classes
- ✅ Cross-class method calls
- ✅ Abstract classes
- ✅ Generic/parameterized classes
- ✅ Class complexity aggregation from methods

**Combined metrics**:
- ✅ Module complexity views
- ✅ Language statistics
- ✅ Coupling + complexity analysis
- ✅ Dependency depth calculation

### Integration Tests

**Coverage**: 14 test cases

**End-to-end workflows**:
- ✅ Full analysis pipeline: repo → analysis → metrics → export
- ✅ Multi-repository comparison
- ✅ Cross-repository author statistics
- ✅ Cross-repository churn comparison
- ✅ Database manager CRUD operations
- ✅ Incremental analysis (idempotent re-analysis)
- ✅ High temporal coupling detection
- ✅ CSV and JSON export functionality

**Query and filtering**:
- ✅ Churn metrics filtering
- ✅ Temporal coupling thresholds (min co-changes, min similarity)
- ✅ Author ownership by file
- ✅ Code age metrics
- ✅ Summary statistics generation

**Error handling**:
- ✅ Nonexistent repository handling
- ✅ Empty repository handling
- ✅ Missing schema files
- ✅ Concurrent database access

## Running Tests

### Run all tests
```bash
pytest tests/
```

### Run specific test file
```bash
pytest tests/test_temporal_coupling.py
pytest tests/test_structural_coupling.py
pytest tests/test_integration.py
```

### Run with coverage
```bash
pytest tests/ --cov=depanalysis --cov-report=term-missing
```

### Run verbose
```bash
pytest tests/ -v
```

### Run specific test
```bash
pytest tests/test_temporal_coupling.py::TestTemporalCoupling::test_jaccard_similarity_calculation -v
```

## Test Coverage Summary

| Module | Coverage |
|--------|----------|
| `db_manager.py` | 98% |
| `metrics.py` | 93% |
| `git_analyzer.py` | 87% |

Total: **54 test cases**, all passing

## Test Fixtures

The `conftest.py` provides reusable fixtures:

- `temp_dir` - Temporary directory for test isolation
- `schema_dir` - Path to SQL schema files
- `db_manager` - Initialized DatabaseManager instance
- `history_db` - SQLite connection to initialized history.db
- `structure_db` - SQLite connection to initialized structure.db
- `sample_git_repo` - Git repository with known commit history
- `sample_structure_data` - Pre-populated structure database with modules, classes, imports, inheritance

## Key Testing Principles

1. **Isolation**: Each test uses temporary directories and databases
2. **Known data**: Sample fixtures with predictable outcomes
3. **Edge cases**: Empty repos, single files, deletions, circular dependencies
4. **Accuracy**: Exact Jaccard similarity and coupling calculations verified
5. **Integration**: Full end-to-end workflows tested
6. **Error handling**: Graceful handling of missing files and invalid inputs

## Future Test Additions

As new features are added, ensure test coverage for:
- [ ] Python AST parser (when implemented)
- [ ] Circular dependency detection algorithms
- [ ] Graph traversal for transitive dependencies
- [ ] Additional language parsers (TypeScript, C#, Java, etc.)
- [ ] GraphML export functionality
