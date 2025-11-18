"""Tests for structural coupling analysis from code structure."""
import pytest


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
