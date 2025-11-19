# NDepend Rules and Equivalent Implementation

This document maps NDepend's rule system to our dependency analysis framework, describing how each category of rules can be implemented using our structure.db and history.db databases.

## Table of Contents

- [Overview of NDepend Rules](#overview-of-ndepend-rules)
- [CQLinq System](#cqlinq-system)
- [Rule Categories and Implementation](#rule-categories-and-implementation)
- [Quality Gates](#quality-gates)
- [Implementation Strategy](#implementation-strategy)

---

## Overview of NDepend Rules

NDepend provides **~200 default rules** organized into categories that enforce code quality, architectural constraints, and best practices for .NET codebases. Rules are written in **CQLinq** (Code Query over LINQ), a LINQ-based query language that operates on a code model consisting of:

- **Assemblies** (projects/modules)
- **Namespaces** (packages)
- **Types** (classes, interfaces, structs, enums)
- **Methods** (functions, constructors)
- **Fields** (variables, properties)

### Key Characteristics

1. **Declarative Rules**: Written as LINQ queries with conditions
2. **Severity Levels**: Issues can be Blocker, Critical, Major, Minor, Info
3. **Technical Debt**: Each rule violation estimates time-to-fix and debt
4. **Quality Gates**: High-level PASS/WARN/FAIL criteria that aggregate rule results
5. **Customizable**: All rules can be edited, disabled, or extended

---

## CQLinq System

### Rule Structure

A typical NDepend rule follows this pattern:

```csharp
warnif count > 10
from t in JustMyCode.Types
where t.NbLinesOfCode > 500
select new {
  t,
  Debt = (t.NbLinesOfCode - 500).ToMinutes().ToDebt(),
  Severity = IssueSeverity.Major
}
```

**Components**:
- **warnif count > N**: Trigger condition (number of violations)
- **from ... where**: LINQ query selecting violating code elements
- **select**: Details of the violation (debt, severity, message)

### Our Equivalent: SQL + Python Rules

We can implement an equivalent system using:

1. **SQL Views**: For structural and temporal queries
2. **Python Rules Engine**: For complex logic and graph algorithms
3. **Rule Registry**: JSON/YAML configuration defining rules
4. **Debt Estimation**: Formula-based time-to-fix calculations

---

## Rule Categories and Implementation

### 1. Code Quality & Metrics

Rules that measure code complexity, size, and maintainability.

#### NDepend Rules

| Rule | Description | Threshold |
|------|-------------|-----------|
| **Methods too big** | Methods with too many lines of code | > 30 LOC |
| **Methods too complex** | High cyclomatic complexity | > 15 CC |
| **Methods with too many parameters** | Parameter count | > 5 params |
| **Methods with too many variables** | Local variable count | > 8 variables |
| **Methods with too many overloads** | Overload count | > 6 overloads |
| **Avoid methods with high maintainability index** | Composite metric | MI < 10 |

#### Our Implementation

**Database Schema** (structure.db):
```sql
-- Already exists in our schema
CREATE TABLE functions (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  module_id INTEGER,
  start_line INTEGER,
  end_line INTEGER,
  complexity INTEGER,      -- Cyclomatic complexity
  parameter_count INTEGER,
  -- ... other fields
);

-- Materialized view for violations
CREATE VIEW code_quality_violations AS
SELECT
  f.id,
  f.name,
  f.module_id,
  m.file_path,
  CASE
    WHEN (f.end_line - f.start_line) > 30 THEN 'methods_too_big'
    WHEN f.complexity > 15 THEN 'methods_too_complex'
    WHEN f.parameter_count > 5 THEN 'too_many_parameters'
  END as violation_type,
  CASE
    WHEN (f.end_line - f.start_line) > 30 THEN (f.end_line - f.start_line - 30) * 2
    WHEN f.complexity > 15 THEN (f.complexity - 15) * 15
    WHEN f.parameter_count > 5 THEN (f.parameter_count - 5) * 30
  END as debt_minutes
FROM functions f
JOIN modules m ON f.module_id = m.id
WHERE (f.end_line - f.start_line) > 30
   OR f.complexity > 15
   OR f.parameter_count > 5;
```

**Python Rule** (for complex calculations):
```python
class MethodsTooComplexRule:
    def __init__(self, threshold=15):
        self.threshold = threshold

    def evaluate(self, db):
        query = """
        SELECT f.id, f.name, f.complexity, m.file_path
        FROM functions f
        JOIN modules m ON f.module_id = m.id
        WHERE f.complexity > ?
        """
        violations = db.execute(query, (self.threshold,)).fetchall()

        return [
            RuleViolation(
                rule_id='CC001',
                element_id=v['id'],
                element_name=v['name'],
                file_path=v['file_path'],
                severity='Major',
                debt_minutes=(v['complexity'] - self.threshold) * 15,
                message=f"Method has complexity {v['complexity']}, threshold is {self.threshold}"
            )
            for v in violations
        ]
```

---

### 2. Object-Oriented Design

Rules enforcing SOLID principles and OO best practices.

#### NDepend Rules

| Rule | Description | Metric |
|------|-------------|--------|
| **Types with poor cohesion** | Class does too many things (SRP violation) | LCOM > 0.8 |
| **Types with too many methods** | God class anti-pattern | > 20 methods |
| **Types with too many fields** | Complex state management | > 15 fields |
| **Classes should not be too deep in inheritance tree** | Deep hierarchies | Depth > 5 |
| **Avoid empty interfaces** | Marker interfaces | 0 members |

#### Our Implementation

**Database Schema**:
```sql
-- Classes table already exists
CREATE TABLE classes (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  module_id INTEGER,
  kind TEXT, -- 'class', 'interface', 'abstract_class'
  -- ... other fields
);

-- Cohesion metric (LCOM - Lack of Cohesion of Methods)
-- Requires analyzing method-field interactions
CREATE VIEW class_cohesion AS
SELECT
  c.id,
  c.name,
  COUNT(DISTINCT f.id) as method_count,
  COUNT(DISTINCT v.id) as field_count,
  -- LCOM calculation requires more complex analysis
  -- This is a simplified version
  1.0 - (
    SELECT COUNT(*)
    FROM calls ca
    WHERE ca.caller_id IN (
      SELECT id FROM functions WHERE class_id = c.id
    )
  ) * 1.0 / NULLIF(method_count * method_count, 0) as lcom_approx
FROM classes c
LEFT JOIN functions f ON f.class_id = c.id
LEFT JOIN variables v ON v.class_id = c.id
GROUP BY c.id, c.name;

-- OO Design violations
CREATE VIEW oo_design_violations AS
SELECT
  c.id,
  c.name,
  m.file_path,
  CASE
    WHEN method_count > 20 THEN 'too_many_methods'
    WHEN field_count > 15 THEN 'too_many_fields'
    WHEN lcom_approx > 0.8 THEN 'poor_cohesion'
  END as violation_type,
  CASE
    WHEN method_count > 20 THEN (method_count - 20) * 30
    WHEN field_count > 15 THEN (field_count - 15) * 20
    WHEN lcom_approx > 0.8 THEN 120
  END as debt_minutes
FROM class_cohesion cc
JOIN classes c ON cc.id = c.id
JOIN modules m ON c.module_id = m.id
WHERE method_count > 20
   OR field_count > 15
   OR lcom_approx > 0.8;
```

**Python Implementation** (for LCOM calculation):
```python
def calculate_lcom_hs(class_id, db):
    """
    Calculate LCOM-HS (Henderson-Sellers) metric.
    LCOM-HS = (M - sum(MF)/F) / (M - 1)
    where M = number of methods, F = number of fields, MF = fields accessed per method
    """
    # Get methods and fields for class
    methods = db.execute("""
        SELECT id FROM functions WHERE class_id = ?
    """, (class_id,)).fetchall()

    fields = db.execute("""
        SELECT id FROM variables WHERE class_id = ? AND kind = 'field'
    """, (class_id,)).fetchall()

    M = len(methods)
    F = len(fields)

    if M <= 1 or F == 0:
        return 0

    # Count field accesses per method (simplified - would need data flow analysis)
    total_field_accesses = 0
    for method in methods:
        # This requires tracking variable references in AST
        # Placeholder for actual implementation
        field_accesses = count_field_accesses(method['id'], fields, db)
        total_field_accesses += field_accesses

    lcom_hs = (M - total_field_accesses / F) / (M - 1)
    return lcom_hs
```

---

### 3. Architecture & Dependencies

Rules enforcing architectural layers, dependency constraints, and coupling limits.

#### NDepend Rules

| Rule | Description | Metric |
|------|-------------|--------|
| **Avoid namespaces with high efferent coupling** | Module depends on too many others | Ce > 50 |
| **Avoid namespaces mutually dependent** | Circular dependencies | Cycle detected |
| **Avoid types with high afferent coupling** | Too many dependents (hard to change) | Ca > 20 |
| **Avoid excessive class coupling** | Type depends on too many types | > 30 dependencies |
| **Namespace should not have dependency cycles** | Architectural violations | Any cycle |
| **UI layer shouldn't use database layer directly** | Layering violations | Direct dependency |

#### Our Implementation

**Database Schema**:
```sql
-- Coupling metrics
CREATE VIEW module_coupling AS
SELECT
  m.id,
  m.file_path,
  -- Efferent coupling: modules this one depends on
  (SELECT COUNT(DISTINCT i2.imported_module_id)
   FROM imports i2
   WHERE i2.module_id = m.id) as efferent_coupling,
  -- Afferent coupling: modules that depend on this one
  (SELECT COUNT(DISTINCT i3.module_id)
   FROM imports i3
   WHERE i3.imported_module_id = m.id) as afferent_coupling,
  -- Instability: Ce / (Ca + Ce)
  CAST(
    (SELECT COUNT(DISTINCT i2.imported_module_id) FROM imports i2 WHERE i2.module_id = m.id)
    AS FLOAT
  ) / NULLIF(
    (SELECT COUNT(DISTINCT i2.imported_module_id) FROM imports i2 WHERE i2.module_id = m.id) +
    (SELECT COUNT(DISTINCT i3.module_id) FROM imports i3 WHERE i3.imported_module_id = m.id),
    0
  ) as instability
FROM modules m;

-- Architecture violations
CREATE VIEW architecture_violations AS
SELECT
  m.id,
  m.file_path,
  CASE
    WHEN efferent_coupling > 50 THEN 'high_efferent_coupling'
    WHEN afferent_coupling > 20 THEN 'high_afferent_coupling'
    WHEN instability > 0.9 THEN 'highly_unstable'
  END as violation_type,
  efferent_coupling,
  afferent_coupling,
  instability,
  CASE
    WHEN efferent_coupling > 50 THEN (efferent_coupling - 50) * 10
    WHEN afferent_coupling > 20 THEN (afferent_coupling - 20) * 15
    WHEN instability > 0.9 THEN 60
  END as debt_minutes
FROM module_coupling
WHERE efferent_coupling > 50
   OR afferent_coupling > 20
   OR instability > 0.9;
```

**Python Implementation** (circular dependency detection):
```python
class CircularDependencyRule:
    def evaluate(self, db):
        # Build dependency graph
        graph = defaultdict(set)
        modules = {}

        for row in db.execute("""
            SELECT m.id, m.file_path, i.imported_module_id
            FROM modules m
            LEFT JOIN imports i ON m.id = i.module_id
        """):
            modules[row['id']] = row['file_path']
            if row['imported_module_id']:
                graph[row['id']].add(row['imported_module_id'])

        # Detect cycles using Tarjan's algorithm
        cycles = find_strongly_connected_components(graph)

        violations = []
        for cycle in cycles:
            if len(cycle) > 1:  # Actual cycle, not single node
                cycle_paths = [modules[nid] for nid in cycle]
                violations.append(
                    RuleViolation(
                        rule_id='ARCH001',
                        element_id=None,
                        element_name=f"Cycle: {' -> '.join(cycle_paths)}",
                        file_path=cycle_paths[0],
                        severity='Critical',
                        debt_minutes=len(cycle) * 120,  # 2 hours per module in cycle
                        message=f"Circular dependency detected involving {len(cycle)} modules"
                    )
                )

        return violations
```

---

### 4. Code Smells

Rules detecting common anti-patterns and maintainability issues.

#### NDepend Rules

| Rule | Description |
|------|-------------|
| **Avoid methods that could have a lower visibility** | Over-exposed API surface |
| **Avoid empty classes** | Classes with no behavior |
| **Avoid classes with only static members** | Should be static class |
| **Instance fields should be prefixed with 'm_'** | Naming convention |
| **Dead code (methods never called)** | Unused code |
| **Duplicated code** | Copy-paste detection |
| **God class** | Class with too many responsibilities |

#### Our Implementation

**Database Schema**:
```sql
-- Dead code detection
CREATE VIEW dead_functions AS
SELECT
  f.id,
  f.name,
  m.file_path,
  f.kind
FROM functions f
JOIN modules m ON f.module_id = m.id
WHERE f.id NOT IN (
  -- Not called by any other function
  SELECT DISTINCT called_function_id
  FROM calls
  WHERE called_function_id IS NOT NULL
)
-- Exclude entry points (main, __init__, test_*, etc.)
AND f.name NOT LIKE 'test_%'
AND f.name NOT LIKE '__init__'
AND f.name NOT LIKE 'main'
AND f.kind NOT IN ('constructor', 'destructor');

-- Empty classes
CREATE VIEW empty_classes AS
SELECT
  c.id,
  c.name,
  m.file_path
FROM classes c
JOIN modules m ON c.module_id = m.id
WHERE c.id NOT IN (
  SELECT DISTINCT class_id FROM functions WHERE class_id IS NOT NULL
  UNION
  SELECT DISTINCT class_id FROM variables WHERE class_id IS NOT NULL
);

-- Code smells view
CREATE VIEW code_smell_violations AS
SELECT
  'dead_function' as violation_type,
  f.id as element_id,
  f.name,
  m.file_path,
  30 as debt_minutes,
  'Major' as severity
FROM dead_functions df
JOIN functions f ON df.id = f.id
JOIN modules m ON f.module_id = m.id

UNION ALL

SELECT
  'empty_class' as violation_type,
  c.id as element_id,
  c.name,
  m.file_path,
  15 as debt_minutes,
  'Minor' as severity
FROM empty_classes ec
JOIN classes c ON ec.id = c.id
JOIN modules m ON c.module_id = m.id;
```

**Python Implementation** (code duplication detection):
```python
class CodeDuplicationRule:
    """Detect duplicated code blocks using AST similarity."""

    def __init__(self, min_lines=6, similarity_threshold=0.9):
        self.min_lines = min_lines
        self.similarity_threshold = similarity_threshold

    def evaluate(self, db):
        # Get all function bodies
        functions = db.execute("""
            SELECT f.id, f.name, m.file_path, f.start_line, f.end_line
            FROM functions f
            JOIN modules m ON f.module_id = m.id
        """).fetchall()

        violations = []

        # Compare function pairs for similarity
        for i, func1 in enumerate(functions):
            for func2 in functions[i+1:]:
                # Calculate AST similarity (simplified)
                similarity = calculate_ast_similarity(
                    func1['file_path'], func1['start_line'], func1['end_line'],
                    func2['file_path'], func2['start_line'], func2['end_line']
                )

                if similarity >= self.similarity_threshold:
                    violations.append(
                        RuleViolation(
                            rule_id='SMELL001',
                            element_id=func1['id'],
                            element_name=f"{func1['name']} ~ {func2['name']}",
                            file_path=func1['file_path'],
                            severity='Major',
                            debt_minutes=60,
                            message=f"Code duplication ({similarity*100:.0f}% similar) with {func2['file_path']}"
                        )
                    )

        return violations
```

---

### 5. Naming Conventions

Rules enforcing consistent naming patterns.

#### NDepend Rules

| Rule | Description | Pattern |
|------|-------------|---------|
| **Instance fields naming** | Fields should be prefixed | `m_FieldName` or `_fieldName` |
| **Types naming** | PascalCase for types | `^[A-Z][a-zA-Z0-9]*$` |
| **Methods naming** | PascalCase for methods | `^[A-Z][a-zA-Z0-9]*$` |
| **Constants naming** | UPPER_SNAKE_CASE | `^[A-Z][A-Z0-9_]*$` |
| **Private methods naming** | Consistent prefix/pattern | Language-specific |
| **Async methods should end with 'Async'** | Async naming convention | `*Async` |

#### Our Implementation

**Database Schema**:
```sql
-- Naming convention violations
CREATE VIEW naming_violations AS
-- Type naming (PascalCase for classes)
SELECT
  c.id as element_id,
  'class' as element_type,
  c.name,
  m.file_path,
  'type_naming' as violation_type,
  5 as debt_minutes,
  'Minor' as severity,
  'Class name should be PascalCase' as message
FROM classes c
JOIN modules m ON c.module_id = m.id
WHERE c.name NOT GLOB '[A-Z]*'  -- Doesn't start with uppercase

UNION ALL

-- Function naming (snake_case for Python, camelCase for others)
SELECT
  f.id as element_id,
  'function' as element_type,
  f.name,
  m.file_path,
  'function_naming' as violation_type,
  5 as debt_minutes,
  'Minor' as severity,
  'Function name should follow language conventions' as message
FROM functions f
JOIN modules m ON f.module_id = m.id
JOIN languages l ON m.language_id = l.id
WHERE
  -- Python: should be snake_case
  (l.name = 'python' AND f.name GLOB '*[A-Z]*' AND f.name NOT LIKE '__*__')
  OR
  -- TypeScript/JavaScript: should be camelCase
  (l.name IN ('typescript', 'javascript') AND f.name GLOB '[A-Z]*');
```

**Python Implementation** (flexible naming rules):
```python
class NamingConventionRule:
    """Enforce language-specific naming conventions."""

    CONVENTIONS = {
        'python': {
            'class': r'^[A-Z][a-zA-Z0-9]*$',  # PascalCase
            'function': r'^[a-z_][a-z0-9_]*$',  # snake_case
            'constant': r'^[A-Z][A-Z0-9_]*$',  # UPPER_SNAKE_CASE
        },
        'typescript': {
            'class': r'^[A-Z][a-zA-Z0-9]*$',  # PascalCase
            'function': r'^[a-z][a-zA-Z0-9]*$',  # camelCase
            'constant': r'^[A-Z][A-Z0-9_]*$',  # UPPER_SNAKE_CASE
        },
        'csharp': {
            'class': r'^[A-Z][a-zA-Z0-9]*$',  # PascalCase
            'function': r'^[A-Z][a-zA-Z0-9]*$',  # PascalCase
            'field': r'^_[a-z][a-zA-Z0-9]*$',  # _camelCase
        }
    }

    def evaluate(self, db):
        violations = []

        # Check class naming
        for row in db.execute("""
            SELECT c.id, c.name, m.file_path, l.name as language
            FROM classes c
            JOIN modules m ON c.module_id = m.id
            JOIN languages l ON m.language_id = l.id
        """):
            pattern = self.CONVENTIONS.get(row['language'], {}).get('class')
            if pattern and not re.match(pattern, row['name']):
                violations.append(
                    RuleViolation(
                        rule_id='NAME001',
                        element_id=row['id'],
                        element_name=row['name'],
                        file_path=row['file_path'],
                        severity='Minor',
                        debt_minutes=5,
                        message=f"Class '{row['name']}' doesn't match {row['language']} naming convention"
                    )
                )

        return violations
```

---

### 6. Dead Code Detection

Rules identifying unused or unreachable code.

#### NDepend Rules

| Rule | Description |
|------|-------------|
| **Dead Methods** | Methods never called |
| **Dead Types** | Types never instantiated or referenced |
| **Dead Fields** | Fields never read |
| **Unused Parameters** | Parameters never used in method body |
| **Unused Variables** | Local variables declared but not used |

#### Our Implementation

Already covered in Code Smells section. Additional refinements:

**Database Schema**:
```sql
-- Unused imports
CREATE VIEW unused_imports AS
SELECT
  i.id,
  i.module_id,
  i.imported_module_id,
  i.imported_name,
  m.file_path
FROM imports i
JOIN modules m ON i.module_id = m.id
WHERE i.imported_name IS NOT NULL
  AND i.imported_name NOT IN (
    -- Check if imported name is used in calls
    SELECT DISTINCT called_name
    FROM calls c
    WHERE c.caller_id IN (
      SELECT id FROM functions WHERE module_id = i.module_id
    )
  );

-- Dead fields (variables never read)
CREATE VIEW dead_fields AS
SELECT
  v.id,
  v.name,
  c.name as class_name,
  m.file_path
FROM variables v
JOIN classes c ON v.class_id = c.id
JOIN modules m ON v.module_id = m.id
WHERE v.kind = 'field'
  -- Would need data flow analysis to track field reads
  -- Placeholder: fields not accessed in any method
  AND NOT EXISTS (
    SELECT 1 FROM calls ca
    WHERE ca.caller_id IN (
      SELECT id FROM functions WHERE class_id = c.id
    )
    -- Would need to check if ca references v.name
  );
```

---

### 7. API Breaking Changes

Rules detecting changes that break backward compatibility.

#### NDepend Rules

| Rule | Description |
|------|-------------|
| **Breaking changes on public API** | Signature changes, removals |
| **Added required parameters** | Breaks existing callers |
| **Changed return type** | Type compatibility issues |
| **Removed public members** | API surface reduction |
| **Changed exception types** | Contract changes |

#### Our Implementation

This requires **comparing two snapshots** of structure.db (baseline vs current).

**Database Schema**:
```sql
-- Store baseline snapshot
CREATE TABLE baseline_functions AS
SELECT * FROM functions WHERE 1=0;  -- Empty table with same schema

-- Compare current vs baseline
CREATE VIEW api_breaking_changes AS
-- Removed public functions
SELECT
  'removed_function' as change_type,
  bf.id as baseline_id,
  bf.name,
  m.file_path,
  'Critical' as severity,
  60 as debt_minutes
FROM baseline_functions bf
JOIN modules m ON bf.module_id = m.id
WHERE bf.id NOT IN (SELECT id FROM functions)
  AND bf.visibility = 'public'

UNION ALL

-- Changed function signatures
SELECT
  'signature_change' as change_type,
  f.id,
  f.name,
  m.file_path,
  'Major' as severity,
  30 as debt_minutes
FROM functions f
JOIN baseline_functions bf ON f.id = bf.id
JOIN modules m ON f.module_id = m.id
WHERE f.parameter_count != bf.parameter_count
   OR f.return_type != bf.return_type;
```

**Python Implementation**:
```python
class APIBreakingChangesRule:
    def __init__(self, baseline_db_path):
        self.baseline_db = sqlite3.connect(baseline_db_path)

    def evaluate(self, current_db):
        violations = []

        # Compare public APIs
        baseline_api = self._extract_public_api(self.baseline_db)
        current_api = self._extract_public_api(current_db)

        # Detect removals
        for sig, info in baseline_api.items():
            if sig not in current_api:
                violations.append(
                    RuleViolation(
                        rule_id='API001',
                        element_id=info['id'],
                        element_name=info['name'],
                        file_path=info['file_path'],
                        severity='Critical',
                        debt_minutes=120,
                        message=f"Public API removed: {sig}"
                    )
                )

        # Detect signature changes
        for sig, current_info in current_api.items():
            if sig in baseline_api:
                baseline_info = baseline_api[sig]
                if self._signatures_incompatible(baseline_info, current_info):
                    violations.append(
                        RuleViolation(
                            rule_id='API002',
                            element_id=current_info['id'],
                            element_name=current_info['name'],
                            file_path=current_info['file_path'],
                            severity='Major',
                            debt_minutes=60,
                            message=f"API signature changed: {sig}"
                        )
                    )

        return violations

    def _extract_public_api(self, db):
        """Extract public API surface (public classes, methods, functions)."""
        api = {}

        for row in db.execute("""
            SELECT f.id, f.name, f.parameter_count, f.return_type, m.file_path
            FROM functions f
            JOIN modules m ON f.module_id = m.id
            WHERE f.visibility = 'public'
        """):
            signature = f"{row['file_path']}::{row['name']}({row['parameter_count']})"
            api[signature] = {
                'id': row['id'],
                'name': row['name'],
                'file_path': row['file_path'],
                'parameter_count': row['parameter_count'],
                'return_type': row['return_type']
            }

        return api
```

---

### 8. Code Coverage by Tests

Rules requiring adequate test coverage.

#### NDepend Rules

| Rule | Description | Threshold |
|------|-------------|-----------|
| **At least 80% coverage** | Overall coverage requirement | ≥ 80% |
| **New code should be 100% covered** | Prevent coverage regression | 100% on new code |
| **Uncovered complex methods** | High-risk areas | CC > 10 && coverage < 50% |
| **Public API should be covered** | External contracts tested | Public methods ≥ 90% |

#### Our Implementation

This requires **integration with coverage tools** (coverage.py, istanbul, etc.) and storing results.

**Database Schema** (extend structure.db):
```sql
-- Coverage data table
CREATE TABLE IF NOT EXISTS coverage (
  id INTEGER PRIMARY KEY,
  function_id INTEGER REFERENCES functions(id),
  lines_total INTEGER NOT NULL,
  lines_covered INTEGER NOT NULL,
  branches_total INTEGER,
  branches_covered INTEGER,
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Coverage violations
CREATE VIEW coverage_violations AS
SELECT
  f.id,
  f.name,
  f.complexity,
  m.file_path,
  c.lines_covered * 100.0 / NULLIF(c.lines_total, 0) as coverage_percent,
  CASE
    WHEN f.complexity > 10 AND (c.lines_covered * 100.0 / NULLIF(c.lines_total, 0)) < 50
      THEN 'uncovered_complex_method'
    WHEN f.visibility = 'public' AND (c.lines_covered * 100.0 / NULLIF(c.lines_total, 0)) < 90
      THEN 'uncovered_public_api'
    WHEN (c.lines_covered * 100.0 / NULLIF(c.lines_total, 0)) < 80
      THEN 'low_coverage'
  END as violation_type,
  f.complexity * (100 - c.lines_covered * 100.0 / NULLIF(c.lines_total, 0)) / 10 as debt_minutes
FROM functions f
JOIN modules m ON f.module_id = m.id
LEFT JOIN coverage c ON f.id = c.function_id
WHERE c.lines_covered * 100.0 / NULLIF(c.lines_total, 0) < 80
   OR (f.complexity > 10 AND c.lines_covered * 100.0 / NULLIF(c.lines_total, 0) < 50)
   OR (f.visibility = 'public' AND c.lines_covered * 100.0 / NULLIF(c.lines_total, 0) < 90);
```

**Python Implementation** (coverage import):
```python
class CoverageImporter:
    """Import coverage data from coverage.py XML reports."""

    def import_coverage(self, coverage_xml_path, db):
        tree = ET.parse(coverage_xml_path)
        root = tree.getroot()

        for package in root.findall('.//package'):
            for cls in package.findall('.//class'):
                filename = cls.get('filename')

                for method in cls.findall('.//method'):
                    method_name = method.get('name')

                    # Find corresponding function in structure.db
                    func = db.execute("""
                        SELECT f.id FROM functions f
                        JOIN modules m ON f.module_id = m.id
                        WHERE m.file_path = ? AND f.name = ?
                    """, (filename, method_name)).fetchone()

                    if func:
                        lines = method.findall('.//line')
                        lines_total = len(lines)
                        lines_covered = sum(1 for line in lines if line.get('hits', '0') != '0')

                        # Insert/update coverage
                        db.execute("""
                            INSERT OR REPLACE INTO coverage
                            (function_id, lines_total, lines_covered)
                            VALUES (?, ?, ?)
                        """, (func['id'], lines_total, lines_covered))

        db.commit()
```

---

### 9. Temporal & Churn-Based Rules

**Unique to our framework** - NDepend doesn't have Git history analysis.

#### Our Rules (Novel Contributions)

| Rule | Description | Metric |
|------|-------------|--------|
| **High-churn complex code (Hotspots)** | Frequently changing complex code | Churn > 10 AND CC > 15 |
| **Temporal coupling without structural dependency** | Hidden dependencies | Jaccard > 0.5 AND no import |
| **Code owned by departed developers** | Orphaned code risk | Last author inactive > 6 months |
| **Files with excessive authors** | Too many cooks | Author count > 5 |
| **Unstable API (frequent signature changes)** | Churn on public methods | Public method changes > 5 |

#### Our Implementation

**Database Schema** (joining structure.db + history.db):
```sql
-- Hotspots: high churn + high complexity
CREATE VIEW hotspots AS
SELECT
  f.id,
  f.name,
  f.complexity,
  m.file_path,
  h.churn_count,
  h.churn_magnitude,
  f.complexity * h.churn_count as hotspot_score,
  'Critical' as severity,
  f.complexity * h.churn_count / 10 as debt_minutes
FROM functions f
JOIN modules m ON f.module_id = m.id
JOIN (
  -- Join with history.db
  SELECT
    fc.file_path,
    COUNT(*) as churn_count,
    SUM(fc.lines_added + fc.lines_deleted) as churn_magnitude
  FROM file_changes fc
  GROUP BY fc.file_path
) h ON m.file_path = h.file_path
WHERE f.complexity > 15
  AND h.churn_count > 10
ORDER BY hotspot_score DESC;

-- Hidden dependencies (temporal coupling without structural dependency)
CREATE VIEW hidden_dependencies AS
SELECT
  tc.file_a,
  tc.file_b,
  tc.coupling_strength,
  tc.commit_count,
  'Major' as severity,
  60 as debt_minutes,
  'Files change together but have no structural dependency' as message
FROM temporal_coupling tc
WHERE tc.coupling_strength > 0.5  -- High Jaccard similarity
  AND NOT EXISTS (
    -- No import relationship
    SELECT 1 FROM imports i
    JOIN modules ma ON i.module_id = ma.id
    JOIN modules mb ON i.imported_module_id = mb.id
    WHERE (ma.file_path = tc.file_a AND mb.file_path = tc.file_b)
       OR (ma.file_path = tc.file_b AND mb.file_path = tc.file_a)
  );
```

---

## Quality Gates

NDepend's Quality Gates are high-level PASS/WARN/FAIL criteria based on aggregated metrics.

### NDepend Default Quality Gates

| Quality Gate | Warn Threshold | Fail Threshold |
|--------------|----------------|----------------|
| **Percentage Debt** | > 5% | > 10% |
| **New Debt since Baseline** | > 1 hour | > 4 hours |
| **Percentage Coverage** | < 70% | < 60% |
| **Coverage on New Code** | < 90% | < 80% |
| **Issues: Blocker** | > 0 | > 3 |
| **Issues: Critical** | > 5 | > 10 |
| **Critical Rules Violated** | > 0 | > 0 (fails build) |
| **Treat Compiler Warnings as Errors** | > 0 | - |

### Our Quality Gates Implementation

**Database Schema**:
```sql
-- Quality gate results table
CREATE TABLE quality_gates (
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  description TEXT,
  warn_threshold REAL,
  fail_threshold REAL,
  direction TEXT CHECK(direction IN ('above', 'below')),  -- above/below threshold
  enabled INTEGER DEFAULT 1
);

-- Quality gate evaluation
CREATE TABLE quality_gate_results (
  id INTEGER PRIMARY KEY,
  quality_gate_id INTEGER REFERENCES quality_gates(id),
  evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  value REAL NOT NULL,
  status TEXT CHECK(status IN ('PASS', 'WARN', 'FAIL')),
  baseline_value REAL
);

-- Insert default quality gates
INSERT INTO quality_gates (name, description, warn_threshold, fail_threshold, direction)
VALUES
  ('debt_percentage', 'Percentage of code with technical debt', 5.0, 10.0, 'above'),
  ('overall_coverage', 'Overall test coverage percentage', 70.0, 60.0, 'below'),
  ('critical_issues', 'Number of critical severity issues', 5, 10, 'above'),
  ('blocker_issues', 'Number of blocker severity issues', 0, 3, 'above'),
  ('average_complexity', 'Average cyclomatic complexity', 10.0, 15.0, 'above'),
  ('hotspot_count', 'Number of high-risk hotspots', 5, 10, 'above');
```

**Python Implementation**:
```python
class QualityGateEvaluator:
    """Evaluate quality gates and determine build status."""

    def __init__(self, structure_db, history_db):
        self.structure_db = structure_db
        self.history_db = history_db

    def evaluate_all(self):
        """Evaluate all enabled quality gates."""
        gates = self.structure_db.execute("""
            SELECT * FROM quality_gates WHERE enabled = 1
        """).fetchall()

        results = []

        for gate in gates:
            value = self._calculate_gate_value(gate['name'])
            status = self._determine_status(
                value,
                gate['warn_threshold'],
                gate['fail_threshold'],
                gate['direction']
            )

            # Store result
            self.structure_db.execute("""
                INSERT INTO quality_gate_results
                (quality_gate_id, value, status)
                VALUES (?, ?, ?)
            """, (gate['id'], value, status))

            results.append({
                'gate': gate['name'],
                'value': value,
                'status': status,
                'warn': gate['warn_threshold'],
                'fail': gate['fail_threshold']
            })

        self.structure_db.commit()
        return results

    def _calculate_gate_value(self, gate_name):
        """Calculate metric value for a quality gate."""
        if gate_name == 'debt_percentage':
            total_functions = self.structure_db.execute(
                "SELECT COUNT(*) as cnt FROM functions"
            ).fetchone()['cnt']

            functions_with_issues = self.structure_db.execute("""
                SELECT COUNT(DISTINCT element_id) as cnt
                FROM (
                    SELECT element_id FROM code_quality_violations
                    UNION
                    SELECT element_id FROM oo_design_violations
                    UNION
                    SELECT element_id FROM architecture_violations
                )
            """).fetchone()['cnt']

            return (functions_with_issues / total_functions * 100) if total_functions > 0 else 0

        elif gate_name == 'critical_issues':
            return self.structure_db.execute("""
                SELECT COUNT(*) as cnt
                FROM code_quality_violations
                WHERE severity = 'Critical'
            """).fetchone()['cnt']

        elif gate_name == 'hotspot_count':
            return self.structure_db.execute("""
                SELECT COUNT(*) as cnt FROM hotspots
            """).fetchone()['cnt']

        # Add more gate calculations...

        return 0

    def _determine_status(self, value, warn_threshold, fail_threshold, direction):
        """Determine PASS/WARN/FAIL status."""
        if direction == 'above':
            if value >= fail_threshold:
                return 'FAIL'
            elif value >= warn_threshold:
                return 'WARN'
            else:
                return 'PASS'
        else:  # below
            if value <= fail_threshold:
                return 'FAIL'
            elif value <= warn_threshold:
                return 'WARN'
            else:
                return 'PASS'

    def should_fail_build(self):
        """Determine if build should fail based on quality gates."""
        failed = self.structure_db.execute("""
            SELECT COUNT(*) as cnt
            FROM quality_gate_results
            WHERE status = 'FAIL'
              AND evaluated_at >= datetime('now', '-1 hour')
        """).fetchone()['cnt']

        return failed > 0
```

---

## Implementation Strategy

### Phase 1: Core Rule Engine (MVP)

**Goal**: Implement basic rule evaluation framework.

**Components**:
1. **Rule Registry** (`rules/registry.yaml`):
   ```yaml
   rules:
     - id: CC001
       name: "Methods too complex"
       category: "Code Quality"
       severity: "Major"
       enabled: true
       sql_query: |
         SELECT f.id, f.name, f.complexity, m.file_path
         FROM functions f
         JOIN modules m ON f.module_id = m.id
         WHERE f.complexity > 15
       debt_formula: "(complexity - 15) * 15"

     - id: ARCH001
       name: "Circular dependencies"
       category: "Architecture"
       severity: "Critical"
       enabled: true
       python_class: "CircularDependencyRule"
   ```

2. **Rule Engine** (`depanalysis/rules/engine.py`):
   ```python
   class RuleEngine:
       def __init__(self, structure_db, history_db, rules_registry):
           self.structure_db = structure_db
           self.history_db = history_db
           self.rules = self._load_rules(rules_registry)

       def evaluate_all_rules(self):
           """Run all enabled rules and collect violations."""
           all_violations = []

           for rule in self.rules:
               if not rule.enabled:
                   continue

               violations = rule.evaluate(self.structure_db, self.history_db)
               all_violations.extend(violations)

           return all_violations

       def generate_report(self, violations):
           """Generate HTML/JSON report of violations."""
           pass
   ```

3. **CLI Integration** (`depanalysis/cli.py`):
   ```python
   @click.command()
   @click.option('--rules-config', default='rules/registry.yaml')
   @click.option('--output-format', type=click.Choice(['json', 'html', 'csv']))
   def analyze_rules(rules_config, output_format):
       """Run rule analysis and generate report."""
       structure_db = sqlite3.connect('data/repo/structure.db')
       history_db = sqlite3.connect('data/repo/history.db')

       engine = RuleEngine(structure_db, history_db, rules_config)
       violations = engine.evaluate_all_rules()

       if output_format == 'json':
           print(json.dumps([v.to_dict() for v in violations], indent=2))
       elif output_format == 'html':
           generate_html_report(violations)
   ```

### Phase 2: Quality Gates & CI Integration

**Goal**: Add quality gate evaluation and build failure logic.

**Components**:
1. Quality gate configuration
2. Baseline comparison (detect new issues since last release)
3. CI exit codes (fail build on quality gate failure)
4. GitHub Actions integration

### Phase 3: Advanced Rules & Temporal Analysis

**Goal**: Implement unique temporal coupling rules.

**Components**:
1. Hotspot detection (churn + complexity)
2. Hidden dependencies (temporal coupling without structural dependency)
3. Ownership risk analysis
4. Predictive metrics (likely to change together)

### Phase 4: Visualization & Dashboards

**Goal**: Add Observable dashboards for rule violations.

**Components**:
1. Rules dashboard (`docs/rules.md`)
2. Quality gates trends over time
3. Debt heatmaps
4. Interactive violation explorer

### Phase 5: Custom Rule DSL (Future)

**Goal**: Create a DSL similar to CQLinq for custom rules.

**Options**:
- **SQL-based DSL**: Extend SQL with custom functions
- **Python-based DSL**: Fluent API for rule definition
- **YAML + Jinja**: Templates with embedded SQL/Python

**Example (Python Fluent API)**:
```python
# Define custom rule using fluent API
rule = (
    Rule("HighCouplingComplexity")
    .select(Functions)
    .where(lambda f: f.complexity > 15 and f.efferent_coupling > 10)
    .severity(IssueSeverity.Critical)
    .debt(lambda f: f.complexity * 10)
    .message(lambda f: f"Function {f.name} has high complexity ({f.complexity}) and coupling ({f.efferent_coupling})")
)
```

---

## Summary Comparison

| Feature | NDepend | Our Framework |
|---------|---------|---------------|
| **Query Language** | CQLinq (LINQ) | SQL + Python |
| **Code Model** | Assemblies, Types, Methods, Fields | Modules, Classes, Functions, Variables |
| **Metrics** | ~100 .NET-specific | Language-agnostic + temporal |
| **Architecture** | Static analysis only | Static + Git history |
| **Rules** | ~200 default | Start with ~50, grow to 100+ |
| **Quality Gates** | ~12 default | ~10 default |
| **Unique Features** | .NET deep integration | **Temporal coupling, hotspots, churn** |
| **Customization** | CQLinq editing | SQL views + Python plugins |
| **Languages** | .NET only | Python, TypeScript, C#, Java, Rust, C++, Go |
| **Visualization** | Desktop UI | **Observable web dashboards** |

---

## Next Steps

1. **Implement core rule engine** (Phase 1)
2. **Add 10-15 essential rules** covering code quality, architecture, smells
3. **Create quality gates system** with configurable thresholds
4. **Build Observable dashboard** for rule violations
5. **Extend with temporal rules** (our unique contribution)
6. **Document rule customization** guide for users

This design leverages our dual-database architecture to provide both NDepend-style structural rules AND unique temporal analysis that NDepend cannot offer.
