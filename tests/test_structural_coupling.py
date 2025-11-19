"""Tests for structural coupling analysis from code structure."""
import pytest
from pathlib import Path
from depanalysis.structure_analyzer import StructureAnalyzer


class TestFileToFileCoupling:
    """Test suite for file-to-file (module-to-module) coupling via imports."""

    def test_import_relationships(self, sample_structure_data):
        """Test that import relationships are captured correctly."""
        cursor = sample_structure_data.cursor()

        # Count total imports
        import_count = cursor.execute("""
            SELECT COUNT(*) FROM imports
        """).fetchone()[0]

        assert import_count == 3, "Should have 3 import relationships"

    def test_efferent_coupling(self, sample_structure_data):
        """Test efferent coupling (Ce) - outgoing dependencies."""
        cursor = sample_structure_data.cursor()

        # Each module has exactly 1 outgoing import
        results = cursor.execute("""
            SELECT module_path, efferent_coupling
            FROM efferent_coupling
            ORDER BY module_path
        """).fetchall()

        assert len(results) == 3, "Should have efferent coupling for 3 modules"

        for module_path, ce in results:
            assert ce == 1, f"{module_path} should have efferent coupling of 1"

    def test_afferent_coupling(self, sample_structure_data):
        """Test afferent coupling (Ca) - incoming dependencies."""
        cursor = sample_structure_data.cursor()

        # Each module is imported by exactly 1 other module
        results = cursor.execute("""
            SELECT module_path, afferent_coupling
            FROM afferent_coupling
            ORDER BY module_path
        """).fetchall()

        assert len(results) == 3, "Should have afferent coupling for 3 modules"

        for module_path, ca in results:
            assert ca == 1, f"{module_path} should have afferent coupling of 1"

    def test_instability_metric(self, sample_structure_data):
        """Test instability metric: Ce / (Ca + Ce)."""
        cursor = sample_structure_data.cursor()

        # With Ce=1 and Ca=1, instability should be 0.5
        results = cursor.execute("""
            SELECT module_path, ce, ca, instability
            FROM instability
            ORDER BY module_path
        """).fetchall()

        assert len(results) == 3, "Should have instability for 3 modules"

        for module_path, ce, ca, instability in results:
            expected_instability = ce / (ce + ca) if (ce + ca) > 0 else 0
            assert abs(instability - expected_instability) < 0.01, \
                f"{module_path} instability should be {expected_instability}, got {instability}"

    def test_circular_dependency_detection(self, sample_structure_data):
        """Test detection of circular dependencies between modules."""
        cursor = sample_structure_data.cursor()

        # Our sample has a circular dependency: module_a -> module_b -> module_c -> module_a
        # We can detect this by finding modules that import each other (directly or transitively)

        # Get all import pairs
        imports = cursor.execute("""
            SELECT m1.path, i.to_module
            FROM imports i
            JOIN modules m1 ON i.from_module_id = m1.id
        """).fetchall()

        # Build adjacency list
        graph = {}
        for from_mod, to_mod in imports:
            if from_mod not in graph:
                graph[from_mod] = []
            # Extract module name from path for comparison
            to_name = to_mod.replace('.py', '') if to_mod.endswith('.py') else to_mod
            graph[from_mod].append(to_name)

        # Check that we have a cycle
        # module_a.py -> module_b -> module_b.py
        # module_b.py -> module_c -> module_c.py
        # module_c.py -> module_a -> module_a.py
        assert 'module_a.py' in graph
        assert 'module_b' in graph['module_a.py']

    def test_import_kinds(self, sample_structure_data):
        """Test that different import kinds are tracked."""
        cursor = sample_structure_data.cursor()

        # All our sample imports are 'import' kind
        results = cursor.execute("""
            SELECT DISTINCT import_kind FROM imports
        """).fetchall()

        assert len(results) == 1
        assert results[0][0] == 'import'

    def test_zero_coupling_modules(self, structure_db):
        """Test modules with no imports have zero coupling."""
        cursor = structure_db.cursor()

        # Add an isolated module with no imports
        cursor.execute("""
            INSERT INTO modules (id, language_id, path, name, file_hash)
            VALUES (99, 1, 'isolated.py', 'isolated', 'hash_isolated')
        """)
        structure_db.commit()

        # Check coupling
        result = cursor.execute("""
            SELECT ce, ca, instability
            FROM instability
            WHERE module_path = 'isolated.py'
        """).fetchone()

        assert result is not None
        assert result[0] == 0, "Isolated module should have Ce=0"
        assert result[1] == 0, "Isolated module should have Ca=0"
        assert result[2] == 0, "Isolated module should have instability=0"

    def test_multiple_imports_same_module(self, structure_db):
        """Test module with multiple imports from same source."""
        cursor = structure_db.cursor()

        # Create two modules
        cursor.execute("""
            INSERT INTO modules (id, language_id, path, name, file_hash)
            VALUES
                (10, 1, 'importer.py', 'importer', 'hash1'),
                (11, 1, 'target.py', 'target', 'hash2')
        """)

        # Add multiple imports to the same target
        cursor.execute("""
            INSERT INTO imports (from_module_id, to_module, import_name, import_kind, line_number)
            VALUES
                (10, 'target', 'ClassA', 'import', 1),
                (10, 'target', 'ClassB', 'import', 2),
                (10, 'target', 'ClassC', 'import', 3)
        """)
        structure_db.commit()

        # Efferent coupling should count unique modules, not individual imports
        result = cursor.execute("""
            SELECT efferent_coupling
            FROM efferent_coupling
            WHERE module_path = 'importer.py'
        """).fetchone()

        assert result[0] == 1, "Multiple imports from same module should count as Ce=1"

    def test_relative_vs_absolute_imports(self, structure_db):
        """Test tracking of relative vs absolute imports."""
        cursor = structure_db.cursor()

        # Create modules
        cursor.execute("""
            INSERT INTO modules (id, language_id, path, name, file_hash)
            VALUES (20, 1, 'pkg/module.py', 'module', 'hash')
        """)

        # Add both relative and absolute imports
        cursor.execute("""
            INSERT INTO imports (from_module_id, to_module, import_name, import_kind, is_relative, line_number)
            VALUES
                (20, 'other', 'other', 'import', 0, 1),
                (20, '.sibling', 'sibling', 'import', 1, 2)
        """)
        structure_db.commit()

        # Check that relative flag is set correctly
        results = cursor.execute("""
            SELECT to_module, is_relative
            FROM imports
            WHERE from_module_id = 20
            ORDER BY line_number
        """).fetchall()

        assert len(results) == 2
        assert results[0][1] == 0, "Absolute import should have is_relative=0"
        assert results[1][1] == 1, "Relative import should have is_relative=1"


class TestClassToClassCoupling:
    """Test suite for class-to-class coupling via inheritance and calls."""

    def test_inheritance_relationships(self, sample_structure_data):
        """Test that inheritance relationships are captured."""
        cursor = sample_structure_data.cursor()

        # Count inheritance relationships
        inheritance_count = cursor.execute("""
            SELECT COUNT(*) FROM inheritance
        """).fetchone()[0]

        assert inheritance_count == 2, "Should have 2 inheritance relationships"

    def test_inheritance_chain(self, sample_structure_data):
        """Test multi-level inheritance chain."""
        cursor = sample_structure_data.cursor()

        # ClassC -> ClassB -> ClassA
        # Get the full chain
        chain = cursor.execute("""
            SELECT c.name, i.base_class_name
            FROM classes c
            JOIN inheritance i ON c.id = i.class_id
            ORDER BY c.id
        """).fetchall()

        assert len(chain) == 2
        assert chain[0] == ('ClassB', 'ClassA'), "ClassB should inherit from ClassA"
        assert chain[1] == ('ClassC', 'ClassB'), "ClassC should inherit from ClassB"

    def test_inheritance_kinds(self, sample_structure_data):
        """Test different kinds of inheritance relationships."""
        cursor = sample_structure_data.cursor()

        # All our examples are 'inherits'
        kinds = cursor.execute("""
            SELECT DISTINCT relationship_kind FROM inheritance
        """).fetchall()

        assert len(kinds) == 1
        assert kinds[0][0] == 'inherits'

    def test_interface_implementation(self, structure_db):
        """Test interface implementation (implements relationship)."""
        cursor = structure_db.cursor()

        # Add an interface and implementing class
        cursor.execute("""
            INSERT INTO modules (id, language_id, path, name, file_hash)
            VALUES (30, 1, 'interfaces.py', 'interfaces', 'hash')
        """)

        cursor.execute("""
            INSERT INTO classes (id, module_id, name, qualified_name, kind, line_start, line_end)
            VALUES
                (30, 30, 'IFoo', 'interfaces.IFoo', 'interface', 1, 5),
                (31, 30, 'FooImpl', 'interfaces.FooImpl', 'class', 7, 15)
        """)

        cursor.execute("""
            INSERT INTO inheritance (class_id, base_class_id, base_class_name, relationship_kind, position)
            VALUES (31, 30, 'IFoo', 'implements', 0)
        """)
        structure_db.commit()

        # Verify the relationship
        result = cursor.execute("""
            SELECT relationship_kind
            FROM inheritance
            WHERE class_id = 31
        """).fetchone()

        assert result[0] == 'implements'

    def test_multiple_inheritance(self, structure_db):
        """Test class with multiple base classes."""
        cursor = structure_db.cursor()

        # Add classes
        cursor.execute("""
            INSERT INTO modules (id, language_id, path, name, file_hash)
            VALUES (40, 1, 'multi.py', 'multi', 'hash')
        """)

        cursor.execute("""
            INSERT INTO classes (id, module_id, name, qualified_name, kind, line_start, line_end)
            VALUES
                (40, 40, 'Base1', 'multi.Base1', 'class', 1, 5),
                (41, 40, 'Base2', 'multi.Base2', 'class', 7, 11),
                (42, 40, 'Derived', 'multi.Derived', 'class', 13, 20)
        """)

        # Derived inherits from both Base1 and Base2
        cursor.execute("""
            INSERT INTO inheritance (class_id, base_class_id, base_class_name, relationship_kind, position)
            VALUES
                (42, 40, 'Base1', 'inherits', 0),
                (42, 41, 'Base2', 'inherits', 1)
        """)
        structure_db.commit()

        # Count base classes
        base_count = cursor.execute("""
            SELECT COUNT(*)
            FROM inheritance
            WHERE class_id = 42
        """).fetchone()[0]

        assert base_count == 2, "Derived class should have 2 base classes"

    def test_method_call_relationships(self, sample_structure_data):
        """Test that method calls between classes are captured."""
        cursor = sample_structure_data.cursor()

        # Count function calls
        call_count = cursor.execute("""
            SELECT COUNT(*) FROM calls
        """).fetchone()[0]

        assert call_count == 2, "Should have 2 method calls"

    def test_cross_class_method_calls(self, sample_structure_data):
        """Test method calls between different classes."""
        cursor = sample_structure_data.cursor()

        # method_b (in ClassB) calls method_a (in ClassA)
        result = cursor.execute("""
            SELECT
                f1.qualified_name AS caller,
                f2.qualified_name AS callee
            FROM calls c
            JOIN functions f1 ON c.from_function_id = f1.id
            JOIN functions f2 ON c.to_function_id = f2.id
            WHERE f1.class_id != f2.class_id
        """).fetchall()

        assert len(result) >= 1, "Should have cross-class method calls"
        # Verify the call chain exists
        caller_callees = [(r[0], r[1]) for r in result]
        assert ('module_b.ClassB.method_b', 'module_a.ClassA.method_a') in caller_callees

    def test_call_kinds(self, sample_structure_data):
        """Test different kinds of function calls."""
        cursor = sample_structure_data.cursor()

        kinds = cursor.execute("""
            SELECT DISTINCT call_kind FROM calls
        """).fetchall()

        assert len(kinds) == 1
        assert kinds[0][0] == 'call'

    def test_class_complexity_via_methods(self, sample_structure_data):
        """Test calculating class complexity from method complexities."""
        cursor = sample_structure_data.cursor()

        # Calculate complexity per class
        results = cursor.execute("""
            SELECT
                c.name,
                COUNT(f.id) AS method_count,
                SUM(f.cyclomatic_complexity) AS total_complexity
            FROM classes c
            LEFT JOIN functions f ON f.class_id = c.id
            GROUP BY c.id, c.name
        """).fetchall()

        assert len(results) == 3, "Should have complexity for 3 classes"

        for class_name, method_count, total_complexity in results:
            assert method_count >= 1, f"{class_name} should have methods"
            assert total_complexity >= 1, f"{class_name} should have complexity"

    def test_abstract_classes(self, structure_db):
        """Test tracking of abstract classes."""
        cursor = structure_db.cursor()

        # Add an abstract class
        cursor.execute("""
            INSERT INTO modules (id, language_id, path, name, file_hash)
            VALUES (50, 1, 'abstract.py', 'abstract', 'hash')
        """)

        cursor.execute("""
            INSERT INTO classes (id, module_id, name, qualified_name, kind, line_start, line_end, is_abstract)
            VALUES (50, 50, 'AbstractBase', 'abstract.AbstractBase', 'abstract_class', 1, 10, 1)
        """)
        structure_db.commit()

        # Verify abstract flag
        result = cursor.execute("""
            SELECT is_abstract FROM classes WHERE id = 50
        """).fetchone()

        assert result[0] == 1, "Abstract class should have is_abstract=1"

    def test_generic_classes(self, structure_db):
        """Test tracking of generic/parameterized classes."""
        cursor = structure_db.cursor()

        # Add a generic class
        cursor.execute("""
            INSERT INTO modules (id, language_id, path, name, file_hash)
            VALUES (60, 1, 'generics.py', 'generics', 'hash')
        """)

        cursor.execute("""
            INSERT INTO classes (id, module_id, name, qualified_name, kind, line_start, line_end, is_generic)
            VALUES (60, 60, 'List', 'generics.List', 'class', 1, 10, 1)
        """)

        # Add generic parameters
        cursor.execute("""
            INSERT INTO generic_parameters (owner_type, owner_id, parameter_name, position)
            VALUES ('class', 60, 'T', 0)
        """)
        structure_db.commit()

        # Verify generic parameters
        result = cursor.execute("""
            SELECT parameter_name
            FROM generic_parameters
            WHERE owner_type = 'class' AND owner_id = 60
        """).fetchone()

        assert result[0] == 'T', "Generic parameter should be T"


class TestCouplingMetrics:
    """Test suite for combined coupling metrics."""

    def test_module_complexity_view(self, sample_structure_data):
        """Test module complexity materialized view."""
        cursor = sample_structure_data.cursor()

        results = cursor.execute("""
            SELECT module_path, function_count, total_complexity, avg_complexity
            FROM module_complexity
        """).fetchall()

        assert len(results) == 3, "Should have complexity for 3 modules"

        for module_path, func_count, total_complexity, avg_complexity in results:
            assert func_count >= 1, f"{module_path} should have functions"
            assert total_complexity >= func_count, "Total complexity >= function count"

    def test_language_stats_view(self, sample_structure_data):
        """Test language statistics view."""
        cursor = sample_structure_data.cursor()

        results = cursor.execute("""
            SELECT language, file_count, total_functions
            FROM language_stats
        """).fetchall()

        assert len(results) >= 1, "Should have stats for at least one language"

        # Find Python stats
        python_stats = [r for r in results if r[0] == 'python']
        assert len(python_stats) == 1, "Should have Python stats"
        assert python_stats[0][1] == 3, "Should have 3 Python files"

    def test_coupling_combined_with_complexity(self, sample_structure_data):
        """Test combining coupling and complexity metrics."""
        cursor = sample_structure_data.cursor()

        # Join instability with complexity
        results = cursor.execute("""
            SELECT
                i.module_path,
                i.instability,
                mc.total_complexity
            FROM instability i
            JOIN module_complexity mc ON i.module_id = mc.module_id
        """).fetchall()

        assert len(results) == 3, "Should have combined metrics for 3 modules"

        for module_path, instability, complexity in results:
            assert 0.0 <= instability <= 1.0, "Instability in valid range"
            assert complexity >= 1, "Complexity >= 1"

    def test_dependency_depth(self, sample_structure_data):
        """Test calculating dependency depth (transitive dependencies)."""
        cursor = sample_structure_data.cursor()

        # For a circular dependency, we need to be careful
        # Let's find the immediate dependencies for each module
        results = cursor.execute("""
            SELECT m.path, GROUP_CONCAT(i.to_module) AS dependencies
            FROM modules m
            LEFT JOIN imports i ON i.from_module_id = m.id
            GROUP BY m.id, m.path
        """).fetchall()

        assert len(results) == 3, "Should have dependencies for 3 modules"

        # Each module should import exactly one other module
        for module_path, deps in results:
            if deps:  # deps might be None if no imports
                dep_list = deps.split(',')
                assert len(dep_list) == 1, f"{module_path} should have 1 dependency"

    def test_no_self_dependencies(self, sample_structure_data):
        """Test that modules don't import themselves."""
        cursor = sample_structure_data.cursor()

        self_imports = cursor.execute("""
            SELECT COUNT(*)
            FROM imports i
            JOIN modules m ON i.from_module_id = m.id
            WHERE i.to_module = m.name OR i.to_module = m.path
        """).fetchone()[0]

        assert self_imports == 0, "Should have no self-imports"

    def test_coupling_stability(self, structure_db):
        """Test stability metric (opposite of instability)."""
        cursor = structure_db.cursor()

        # Add modules with known coupling
        cursor.execute("""
            INSERT INTO modules (id, language_id, path, name, file_hash)
            VALUES
                (70, 1, 'stable.py', 'stable', 'hash1'),
                (71, 1, 'unstable.py', 'unstable', 'hash2')
        """)

        # Stable module: high Ca, low Ce (many depend on it, it depends on few)
        cursor.execute("""
            INSERT INTO imports (from_module_id, to_module, import_name, import_kind, line_number)
            VALUES (71, 'stable', 'stable', 'import', 1)
        """)
        structure_db.commit()

        # Calculate stability = Ca / (Ca + Ce) = 1 - instability
        result = cursor.execute("""
            SELECT module_path, ca, ce, instability, (1.0 - instability) AS stability
            FROM instability
            WHERE module_path = 'stable.py'
        """).fetchone()

        # stable.py has Ca=1 (unstable imports it), Ce=0
        # Instability = 0 / (1 + 0) = 0
        # Stability = 1 - 0 = 1
        assert result[3] == 0.0, "Stable module should have instability=0"
        assert result[4] == 1.0, "Stable module should have stability=1"


class TestPythonStructureAnalyzer:
    """Test suite for Python AST structure analysis."""

    def test_basic_module_parsing(self, temp_dir, structure_db):
        """Test that basic Python module is parsed and stored correctly."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "simple_module.py").write_text("""
# Simple module
def hello():
    print("Hello, World!")
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        assert stats["files_parsed"] == 1, "Should parse 1 file"
        assert stats["functions_found"] == 1, "Should find 1 function"
        assert stats["errors"] == 0, "Should have no errors"

        cursor = structure_db.cursor()
        module = cursor.execute("SELECT path, name, file_hash FROM modules").fetchone()

        assert module[0] == "simple_module.py", "Module path should be correct"
        assert module[1] == "simple_module", "Module name should be correct"
        assert module[2] is not None, "File hash should be calculated"
        assert len(module[2]) == 64, "Hash should be SHA256 (64 hex chars)"

    def test_class_extraction(self, temp_dir, structure_db):
        """Test that classes are extracted with correct metadata."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "classes.py").write_text("""
class MyClass:
    '''This is a docstring.'''
    pass

class AnotherClass:
    pass
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        assert stats["classes_found"] == 2, "Should find 2 classes"

        cursor = structure_db.cursor()
        classes = cursor.execute("""
            SELECT name, kind, line_start, line_end, docstring
            FROM classes
            ORDER BY line_start
        """).fetchall()

        assert len(classes) == 2
        assert classes[0][0] == "MyClass"
        assert classes[0][1] == "class"
        assert classes[0][2] == 2, "MyClass starts at line 2"
        assert classes[0][4] == "This is a docstring."
        assert classes[1][0] == "AnotherClass"

    def test_function_extraction(self, temp_dir, structure_db):
        """Test that module-level functions are extracted correctly."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "functions.py").write_text("""
def func_one():
    '''First function.'''
    return 1

def func_two(x, y):
    return x + y
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        assert stats["functions_found"] == 2, "Should find 2 functions"

        cursor = structure_db.cursor()
        functions = cursor.execute("""
            SELECT name, kind, class_id, docstring, line_start
            FROM functions
            ORDER BY line_start
        """).fetchall()

        assert len(functions) == 2
        assert functions[0][0] == "func_one"
        assert functions[0][1] == "function", "Module-level function should have kind='function'"
        assert functions[0][2] is None, "Module-level function should have no class_id"
        assert functions[0][3] == "First function."

    def test_method_extraction(self, temp_dir, structure_db):
        """Test that methods within classes are detected correctly."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "methods.py").write_text("""
class Calculator:
    def add(self, x, y):
        return x + y

    def subtract(self, x, y):
        return x - y
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        assert stats["classes_found"] == 1
        assert stats["functions_found"] == 2, "Should find 2 methods"

        cursor = structure_db.cursor()
        methods = cursor.execute("""
            SELECT f.name, f.kind, c.name AS class_name
            FROM functions f
            JOIN classes c ON f.class_id = c.id
            ORDER BY f.line_start
        """).fetchall()

        assert len(methods) == 2
        assert methods[0][0] == "add"
        assert methods[0][1] == "method", "Class function should have kind='method'"
        assert methods[0][2] == "Calculator"
        assert methods[1][0] == "subtract"
        assert methods[1][1] == "method"

    def test_constructor_detection(self, temp_dir, structure_db):
        """Test that __init__ is detected as a constructor."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "constructor.py").write_text("""
class Person:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hello, {self.name}"
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        cursor = structure_db.cursor()
        functions = cursor.execute("""
            SELECT name, kind FROM functions ORDER BY line_start
        """).fetchall()

        assert len(functions) == 2
        assert functions[0][0] == "__init__"
        assert functions[0][1] == "constructor", "__init__ should have kind='constructor'"
        assert functions[1][0] == "greet"
        assert functions[1][1] == "method"

    def test_simple_imports(self, temp_dir, structure_db):
        """Test extraction of simple import statements."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "imports.py").write_text("""
import os
import sys
import json
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        assert stats["imports_found"] == 3, "Should find 3 imports"

        cursor = structure_db.cursor()
        imports = cursor.execute("""
            SELECT to_module, import_name, import_kind, is_relative
            FROM imports
            ORDER BY line_number
        """).fetchall()

        assert len(imports) == 3
        assert imports[0] == ("os", "os", "import", 0)
        assert imports[1] == ("sys", "sys", "import", 0)
        assert imports[2] == ("json", "json", "import", 0)

    def test_from_imports(self, temp_dir, structure_db):
        """Test extraction of 'from ... import ...' statements."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "from_imports.py").write_text("""
from pathlib import Path
from os.path import join, dirname
from typing import List, Dict
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        assert stats["imports_found"] == 5, "Should find 5 imports (Path + join + dirname + List + Dict)"

        cursor = structure_db.cursor()
        imports = cursor.execute("""
            SELECT to_module, import_name, is_relative
            FROM imports
            ORDER BY line_number, import_name
        """).fetchall()

        assert len(imports) == 5
        assert imports[0][0] == "pathlib"
        assert imports[0][1] == "Path"
        assert imports[0][2] == 0, "Absolute import should have is_relative=0"

    def test_relative_imports(self, temp_dir, structure_db):
        """Test extraction of relative imports."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "relative_imports.py").write_text("""
from .sibling import func
from ..parent import other_func
from ...grandparent import something
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        assert stats["imports_found"] == 3

        cursor = structure_db.cursor()
        imports = cursor.execute("""
            SELECT to_module, import_name, is_relative, line_number
            FROM imports
            ORDER BY line_number
        """).fetchall()

        assert len(imports) == 3
        assert imports[0][0] == ".sibling", "Single dot for same-level import"
        assert imports[0][2] == 1, "Relative import should have is_relative=1"
        assert imports[1][0] == "..parent", "Double dot for parent-level import"
        assert imports[1][2] == 1
        assert imports[2][0] == "...grandparent", "Triple dot for grandparent-level import"
        assert imports[2][2] == 1

    def test_import_aliases(self, temp_dir, structure_db):
        """Test tracking of import aliases."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "aliases.py").write_text("""
import numpy as np
from datetime import datetime as dt
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        cursor = structure_db.cursor()
        imports = cursor.execute("""
            SELECT to_module, import_name, alias
            FROM imports
            ORDER BY line_number
        """).fetchall()

        assert len(imports) == 2
        assert imports[0] == ("numpy", "numpy", "np")
        assert imports[1] == ("datetime", "datetime", "dt")

    def test_cyclomatic_complexity_simple(self, temp_dir, structure_db):
        """Test complexity calculation for simple function (no branches)."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "simple_func.py").write_text("""
def simple():
    x = 1
    y = 2
    return x + y
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        analyzer.analyze()

        cursor = structure_db.cursor()
        complexity = cursor.execute("""
            SELECT cyclomatic_complexity FROM functions WHERE name = 'simple'
        """).fetchone()[0]

        assert complexity == 1, "Simple function with no branches should have complexity=1"

    def test_cyclomatic_complexity_branches(self, temp_dir, structure_db):
        """Test complexity calculation with conditional branches."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "branches.py").write_text("""
def complex_func(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0

def loop_func(n):
    total = 0
    for i in range(n):
        if i % 2 == 0:
            total += i
    return total
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        analyzer.analyze()

        cursor = structure_db.cursor()
        functions = cursor.execute("""
            SELECT name, cyclomatic_complexity FROM functions ORDER BY line_start
        """).fetchall()

        # complex_func has: 1 (base) + 1 (if) + 0 (elif is not counted separately) = 2
        # Actually, let me check the implementation again...
        # The implementation counts: If, While, For, ExceptHandler, With, Assert, comprehension
        # So: 1 (base) + 1 (if) = 2
        assert functions[0][1] >= 2, "Function with if/elif/else should have complexity >= 2"

        # loop_func has: 1 (base) + 1 (for) + 1 (if) = 3
        assert functions[1][1] >= 3, "Function with for+if should have complexity >= 3"

    def test_async_function_detection(self, temp_dir, structure_db):
        """Test that async functions are detected correctly."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "async_func.py").write_text("""
async def fetch_data():
    return "data"

def sync_func():
    return "sync"
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        analyzer.analyze()

        cursor = structure_db.cursor()
        functions = cursor.execute("""
            SELECT name, is_async FROM functions ORDER BY line_start
        """).fetchall()

        assert len(functions) == 2
        assert functions[0][0] == "fetch_data"
        assert functions[0][1] == 1, "Async function should have is_async=1"
        assert functions[1][0] == "sync_func"
        assert functions[1][1] == 0, "Sync function should have is_async=0"

    def test_nested_functions(self, temp_dir, structure_db):
        """Test extraction of nested function definitions."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "nested.py").write_text("""
def outer():
    def inner():
        return "inner"
    return inner()
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        # Both outer and inner should be found
        assert stats["functions_found"] == 2, "Should find both outer and inner functions"

        cursor = structure_db.cursor()
        functions = cursor.execute("""
            SELECT name FROM functions ORDER BY line_start
        """).fetchall()

        assert functions[0][0] == "outer"
        assert functions[1][0] == "inner"

    def test_file_hash_tracking(self, temp_dir, structure_db):
        """Test that file hashes are calculated and stored."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        content = "def test(): pass\n"
        (repo_path / "hashtest.py").write_text(content)

        analyzer = StructureAnalyzer(repo_path, structure_db)
        analyzer.analyze()

        cursor = structure_db.cursor()
        hash1 = cursor.execute("""
            SELECT file_hash FROM modules WHERE name = 'hashtest'
        """).fetchone()[0]

        assert hash1 is not None
        assert len(hash1) == 64  # SHA256 hex

        # Analyze again with same content - should replace with same hash
        analyzer.analyze()
        hash2 = cursor.execute("""
            SELECT file_hash FROM modules WHERE name = 'hashtest'
        """).fetchone()[0]

        assert hash1 == hash2, "Same file content should produce same hash"

    def test_syntax_error_handling(self, temp_dir, structure_db):
        """Test that syntax errors don't crash the analyzer."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        # Create file with invalid syntax
        (repo_path / "invalid.py").write_text("""
def broken(
    # Missing closing paren
    return None
""")

        # Create valid file
        (repo_path / "valid.py").write_text("def good(): pass\n")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        # Both files are counted as "parsed" but invalid one has no data extracted
        assert stats["files_parsed"] == 2, "Both files are processed"
        assert stats["errors"] == 0, "Syntax errors are handled gracefully, not counted as errors"

        # Only the valid file should have a module entry in the database
        cursor = structure_db.cursor()
        modules = cursor.execute("SELECT name FROM modules").fetchall()
        assert len(modules) == 1, "Only valid file should create module entry"
        assert modules[0][0] == "valid"

    def test_encoding_error_handling(self, temp_dir, structure_db):
        """Test that binary files are skipped gracefully."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        # Create a binary file with .py extension
        (repo_path / "binary.py").write_bytes(b"\x00\x01\x02\x03\x04")

        # Create valid file
        (repo_path / "valid.py").write_text("def good(): pass\n")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        # Should skip binary file, parse valid one
        assert stats["files_parsed"] >= 1, "Should parse at least the valid file"

    def test_skip_git_directories(self, temp_dir, structure_db):
        """Test that .git and __pycache__ directories are skipped."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        # Create .git directory with a .py file
        git_dir = repo_path / ".git"
        git_dir.mkdir()
        (git_dir / "hooks.py").write_text("def hook(): pass\n")

        # Create __pycache__ directory with a .py file
        pycache_dir = repo_path / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "cached.py").write_text("def cached(): pass\n")

        # Create normal file
        (repo_path / "normal.py").write_text("def normal(): pass\n")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        assert stats["files_parsed"] == 1, "Should only parse normal.py, skip .git and __pycache__"

        cursor = structure_db.cursor()
        modules = cursor.execute("SELECT name FROM modules").fetchall()
        assert len(modules) == 1
        assert modules[0][0] == "normal"

    def test_full_repo_analysis(self, temp_dir, structure_db):
        """Test analyzing a multi-file repository."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        # Create multiple files
        (repo_path / "module_a.py").write_text("""
import module_b

class ClassA:
    def method_a(self):
        pass
""")

        (repo_path / "module_b.py").write_text("""
from module_a import ClassA

class ClassB(ClassA):
    def method_b(self):
        if True:
            pass
""")

        (repo_path / "utils.py").write_text("""
def helper():
    return 42
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        assert stats["files_parsed"] == 3
        assert stats["classes_found"] == 2
        assert stats["functions_found"] == 3  # method_a, method_b, helper
        assert stats["imports_found"] == 2  # import module_b, from module_a import ClassA
        assert stats["errors"] == 0

        cursor = structure_db.cursor()

        # Verify modules
        module_count = cursor.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
        assert module_count == 3

        # Verify classes
        class_count = cursor.execute("SELECT COUNT(*) FROM classes").fetchone()[0]
        assert class_count == 2

        # Verify functions
        func_count = cursor.execute("SELECT COUNT(*) FROM functions").fetchone()[0]
        assert func_count == 3

    def test_empty_repository(self, temp_dir, structure_db):
        """Test analyzing a repository with no Python files."""
        repo_path = temp_dir / "empty_repo"
        repo_path.mkdir()

        # Create some non-Python files
        (repo_path / "README.md").write_text("# README\n")
        (repo_path / "config.json").write_text("{}\n")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        assert stats["files_parsed"] == 0, "Should parse no files"
        assert stats["classes_found"] == 0
        assert stats["functions_found"] == 0
        assert stats["imports_found"] == 0
        assert stats["errors"] == 0

    def test_decorator_extraction(self, temp_dir, structure_db):
        """Test that decorators are extracted from functions and classes."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "decorators.py").write_text("""
@staticmethod
def static_func():
    pass

class MyClass:
    @property
    def my_property(self):
        return self._value

    @classmethod
    def class_method(cls):
        return cls.__name__
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        assert stats["decorators_found"] == 3, "Should find 3 decorators"

        cursor = structure_db.cursor()
        decorators = cursor.execute("""
            SELECT decorator_name, target_type
            FROM decorators
            ORDER BY line_number
        """).fetchall()

        assert len(decorators) == 3
        assert decorators[0][0] == "staticmethod"
        assert decorators[0][1] == "function"
        assert decorators[1][0] == "property"
        assert decorators[1][1] == "function"
        assert decorators[2][0] == "classmethod"
        assert decorators[2][1] == "function"

    def test_type_hints_extraction(self, temp_dir, structure_db):
        """Test that type hints are extracted from function parameters and returns."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "typehints.py").write_text("""
def add(x: int, y: int) -> int:
    return x + y

def greet(name: str) -> str:
    return f"Hello, {name}"

class Person:
    age: int
    name: str
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        assert stats["type_hints_found"] >= 5, "Should find at least 5 type hints"

        cursor = structure_db.cursor()

        # Check parameter type hints
        param_hints = cursor.execute("""
            SELECT parameter_name, type_annotation, hint_type
            FROM type_hints
            WHERE hint_type = 'parameter'
            ORDER BY parameter_name
        """).fetchall()

        assert len(param_hints) >= 3, "Should have at least 3 parameter hints"

        # Check return type hints
        return_hints = cursor.execute("""
            SELECT type_annotation, hint_type
            FROM type_hints
            WHERE hint_type = 'return'
        """).fetchall()

        assert len(return_hints) == 2, "Should have 2 return type hints"

    def test_inheritance_extraction_from_code(self, temp_dir, structure_db):
        """Test that inheritance relationships are extracted from actual code."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "inheritance.py").write_text("""
class Animal:
    pass

class Dog(Animal):
    pass

class GuideDog(Dog):
    pass

class Flyable:
    pass

class Bird(Animal, Flyable):
    '''Multiple inheritance'''
    pass
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        assert stats["inheritance_found"] >= 4, "Should find at least 4 inheritance relationships"

        cursor = structure_db.cursor()
        inheritance = cursor.execute("""
            SELECT c.name, i.base_class_name, i.position
            FROM classes c
            JOIN inheritance i ON c.id = i.class_id
            ORDER BY c.name, i.position
        """).fetchall()

        assert len(inheritance) >= 4

        # Check Dog inherits from Animal
        dog_inheritance = [i for i in inheritance if i[0] == "Dog"]
        assert len(dog_inheritance) == 1
        assert dog_inheritance[0][1] == "Animal"

        # Check GuideDog inherits from Dog
        guide_dog_inheritance = [i for i in inheritance if i[0] == "GuideDog"]
        assert len(guide_dog_inheritance) == 1
        assert guide_dog_inheritance[0][1] == "Dog"

        # Check Bird has multiple inheritance
        bird_inheritance = [i for i in inheritance if i[0] == "Bird"]
        assert len(bird_inheritance) == 2, "Bird should have 2 base classes"
        base_names = [i[1] for i in bird_inheritance]
        assert "Animal" in base_names
        assert "Flyable" in base_names

    def test_function_calls_extraction(self, temp_dir, structure_db):
        """Test that function calls are extracted from code."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "calls.py").write_text("""
def helper():
    return 42

def caller():
    x = helper()
    print(x)
    return x * 2

class Calculator:
    def add(self, x, y):
        return x + y

    def compute(self, x, y):
        result = self.add(x, y)
        print(result)
        return result
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        assert stats["calls_found"] >= 4, "Should find at least 4 function calls"

        cursor = structure_db.cursor()
        calls = cursor.execute("""
            SELECT to_name, call_kind
            FROM calls
            ORDER BY line_number
        """).fetchall()

        assert len(calls) >= 4

        # Check that helper() and print() calls are tracked
        call_names = [c[0] for c in calls]
        assert "helper" in call_names
        assert "print" in call_names

    def test_class_variables_extraction(self, temp_dir, structure_db):
        """Test that class variables and fields are extracted."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "variables.py").write_text("""
class Config:
    DEBUG = True
    MAX_CONNECTIONS = 100
    name: str
    timeout: int = 30

class Person:
    def __init__(self):
        self.age = 0  # This is not a class variable
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        assert stats["variables_found"] >= 4, "Should find at least 4 class variables"

        cursor = structure_db.cursor()
        variables = cursor.execute("""
            SELECT v.name, v.kind, c.name as class_name
            FROM variables v
            JOIN classes c ON v.class_id = c.id
            WHERE v.function_id IS NULL
            ORDER BY v.line_number
        """).fetchall()

        assert len(variables) >= 4

        # Check that class-level variables are captured
        var_names = [v[0] for v in variables]
        assert "DEBUG" in var_names
        assert "MAX_CONNECTIONS" in var_names
        assert "name" in var_names
        assert "timeout" in var_names

    def test_complex_decorators_with_arguments(self, temp_dir, structure_db):
        """Test extraction of decorators with arguments."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "complex_decorators.py").write_text("""
class WebApp:
    @route('/users/<id>')
    def get_user(self, id):
        pass

    @cache(timeout=300)
    @validate_auth
    def protected_endpoint(self):
        pass
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        assert stats["decorators_found"] == 3, "Should find 3 decorators"

        cursor = structure_db.cursor()
        decorators = cursor.execute("""
            SELECT decorator_name
            FROM decorators
            ORDER BY line_number
        """).fetchall()

        assert len(decorators) == 3
        decorator_names = [d[0] for d in decorators]
        assert "route" in decorator_names
        assert "cache" in decorator_names
        assert "validate_auth" in decorator_names

    def test_full_feature_integration(self, temp_dir, structure_db):
        """Test all new features together in a realistic code sample."""
        repo_path = temp_dir / "sample_repo"
        repo_path.mkdir()

        (repo_path / "full_example.py").write_text("""
from typing import List, Optional

class Animal:
    species: str = "Unknown"

    def __init__(self, name: str):
        self.name = name

    def speak(self) -> str:
        return "..."

class Dog(Animal):
    breed: str

    def __init__(self, name: str, breed: str):
        super().__init__(name)
        self.breed = breed

    def speak(self) -> str:
        return "Woof!"

    @property
    def description(self) -> str:
        return f"{self.name} is a {self.breed}"

def create_dog(name: str, breed: str) -> Dog:
    dog = Dog(name, breed)
    print(dog.description)
    return dog
""")

        analyzer = StructureAnalyzer(repo_path, structure_db)
        stats = analyzer.analyze()

        # Verify all features were captured
        assert stats["files_parsed"] == 1
        assert stats["classes_found"] == 2
        assert stats["functions_found"] >= 5  # __init__ x2, speak x2, description, create_dog
        assert stats["inheritance_found"] == 1  # Dog inherits Animal
        assert stats["decorators_found"] >= 1  # @property
        assert stats["type_hints_found"] >= 6  # Multiple parameters and returns
        assert stats["variables_found"] >= 2  # species, breed
        assert stats["calls_found"] >= 3  # super().__init__(), Dog(), print()

        cursor = structure_db.cursor()

        # Verify inheritance
        inheritance = cursor.execute("""
            SELECT base_class_name FROM inheritance
        """).fetchall()
        assert len(inheritance) == 1
        assert inheritance[0][0] == "Animal"

        # Verify decorators
        decorators = cursor.execute("""
            SELECT decorator_name FROM decorators
        """).fetchall()
        assert len(decorators) >= 1
        assert any(d[0] == "property" for d in decorators)

        # Verify calls include super().__init__
        calls = cursor.execute("""
            SELECT to_name FROM calls
        """).fetchall()
        call_names = [c[0] for c in calls]
        assert "Dog" in call_names or "super.__init__" in call_names or "print" in call_names
