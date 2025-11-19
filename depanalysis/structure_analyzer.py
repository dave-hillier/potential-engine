"""
Structural analyzer for Python code.

Parses Python files using AST to extract modules, classes, functions,
and their relationships, populating the structure.db database.
"""
import ast
import hashlib
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple


class StructureAnalyzer:
    """Analyzes Python code structure and populates structure.db."""

    def __init__(self, repo_path: Path, db_connection: sqlite3.Connection):
        """
        Initialize Structure analyzer.

        Args:
            repo_path: Path to the repository root
            db_connection: SQLite connection to structure.db
        """
        self.repo_path = Path(repo_path)
        self.conn = db_connection
        self.cursor = self.conn.cursor()
        
        # Cache language ID for Python
        self.python_lang_id = self._get_python_lang_id()

    def _get_python_lang_id(self) -> int:
        """Get the ID for the Python language from the database."""
        self.cursor.execute("SELECT id FROM languages WHERE name = 'python'")
        result = self.cursor.fetchone()
        if result:
            return result[0]
        
        # Fallback if not found (should be pre-populated)
        self.cursor.execute("INSERT INTO languages (name) VALUES ('python')")
        return self.cursor.lastrowid

    def analyze(self) -> dict:
        """
        Perform full structural analysis of the repository.

        Returns:
            Dictionary with analysis statistics
        """
        stats = {
            "files_parsed": 0,
            "classes_found": 0,
            "functions_found": 0,
            "imports_found": 0,
            "calls_found": 0,
            "inheritance_found": 0,
            "decorators_found": 0,
            "type_hints_found": 0,
            "variables_found": 0,
            "errors": 0
        }

        # Walk through all Python files
        for file_path in self.repo_path.rglob("*.py"):
            if ".git" in file_path.parts or "__pycache__" in file_path.parts:
                continue

            try:
                self._analyze_file(file_path, stats)
                stats["files_parsed"] += 1
            except Exception as e:
                # print(f"Error parsing {file_path}: {e}")
                stats["errors"] += 1

        self.conn.commit()
        return stats

    def _analyze_file(self, file_path: Path, stats: dict) -> None:
        """Analyze a single Python file."""
        # Calculate relative path for storage
        rel_path = str(file_path.relative_to(self.repo_path))
        
        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return  # Skip binary or weird encoding files

        # Calculate hash
        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        
        # Parse AST
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return  # Skip invalid syntax

        # Insert module
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO modules 
            (language_id, path, name, file_hash, last_parsed)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (self.python_lang_id, rel_path, file_path.stem, file_hash)
        )
        module_id = self.cursor.lastrowid

        # Walk AST
        self._visit_node(tree, module_id, None, None, stats)

    def _visit_node(self, node: ast.AST, module_id: int, class_id: Optional[int], 
                   function_id: Optional[int], stats: dict) -> None:
        """Recursively visit AST nodes."""
        
        # Handle Imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                self._insert_import(module_id, alias.name, alias.name, alias.asname, "import", node.lineno)
                stats["imports_found"] += 1
                
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            level = node.level
            
            # Handle relative imports
            is_relative = level > 0
            if is_relative:
                # Construct relative path representation (e.g., ..utils)
                module = "." * level + module
                
            for alias in node.names:
                import_name = alias.name
                full_target = f"{module}.{import_name}" if module else import_name
                self._insert_import(
                    module_id, 
                    module, 
                    import_name, 
                    alias.asname, 
                    "import", 
                    node.lineno,
                    is_relative=is_relative
                )
                stats["imports_found"] += 1

        # Handle Classes
        elif isinstance(node, ast.ClassDef):
            new_class_id = self._insert_class(module_id, node, stats)
            stats["classes_found"] += 1

            # Visit children with new class context
            for child in ast.iter_fields(node):
                child_val = child[1]
                if isinstance(child_val, list):
                    for item in child_val:
                        if isinstance(item, ast.AST):
                            self._visit_node(item, module_id, new_class_id, None, stats)
                elif isinstance(child_val, ast.AST):
                    self._visit_node(child_val, module_id, new_class_id, None, stats)
            return # Don't continue generic traversal for this node

        # Handle Functions
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            is_async = isinstance(node, ast.AsyncFunctionDef)
            new_func_id = self._insert_function(module_id, class_id, node, is_async)
            stats["functions_found"] += 1
            stats["decorators_found"] += len(node.decorator_list)
            stats["type_hints_found"] += len([arg for arg in node.args.args if arg.annotation])
            if node.returns:
                stats["type_hints_found"] += 1

            # Visit children with new function context
            for child in ast.iter_fields(node):
                child_val = child[1]
                if isinstance(child_val, list):
                    for item in child_val:
                        if isinstance(item, ast.AST):
                            self._visit_node(item, module_id, class_id, new_func_id, stats)
                elif isinstance(child_val, ast.AST):
                    self._visit_node(child_val, module_id, class_id, new_func_id, stats)
            return # Don't continue generic traversal for this node

        # Handle function calls
        elif isinstance(node, ast.Call) and function_id is not None:
            call_name = self._extract_name_from_node(node.func)
            if call_name:
                call_kind = 'async_call' if isinstance(node.func, ast.Attribute) and \
                                            hasattr(node.func, 'attr') and \
                                            node.func.attr in ('await', 'async') else 'call'
                self.cursor.execute(
                    """
                    INSERT INTO calls
                    (from_function_id, to_name, call_kind, line_number)
                    VALUES (?, ?, ?, ?)
                    """,
                    (function_id, call_name, call_kind, node.lineno)
                )
                stats["calls_found"] += 1

        # Handle class-level variable assignments (fields)
        elif isinstance(node, ast.AnnAssign) and class_id is not None and function_id is None:
            if isinstance(node.target, ast.Name):
                var_name = node.target.id
                type_str = self._extract_type_annotation(node.annotation) if node.annotation else None

                self.cursor.execute(
                    """
                    INSERT INTO variables
                    (module_id, class_id, name, kind, line_number)
                    VALUES (?, ?, ?, 'field', ?)
                    """,
                    (module_id, class_id, var_name, node.lineno)
                )
                var_id = self.cursor.lastrowid
                stats["variables_found"] += 1

                # Add type hint if present
                if type_str:
                    self.cursor.execute(
                        """
                        INSERT INTO type_hints
                        (variable_id, hint_type, type_annotation)
                        VALUES (?, 'variable', ?)
                        """,
                        (var_id, type_str)
                    )
                    stats["type_hints_found"] += 1

        # Handle regular assignments for class fields (e.g., x = 5 in class body)
        elif isinstance(node, ast.Assign) and class_id is not None and function_id is None:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_name = target.id
                    self.cursor.execute(
                        """
                        INSERT INTO variables
                        (module_id, class_id, name, kind, line_number)
                        VALUES (?, ?, ?, 'field', ?)
                        """,
                        (module_id, class_id, var_name, node.lineno)
                    )
                    stats["variables_found"] += 1

        # Continue traversal for other nodes
        for child in ast.iter_child_nodes(node):
            self._visit_node(child, module_id, class_id, function_id, stats)

    def _insert_import(self, module_id: int, to_module: str, import_name: str, 
                      alias: Optional[str], kind: str, lineno: int, 
                      is_relative: bool = False) -> None:
        """Insert import record."""
        self.cursor.execute(
            """
            INSERT INTO imports 
            (from_module_id, to_module, import_name, alias, import_kind, 
             is_relative, line_number)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (module_id, to_module, import_name, alias, kind, is_relative, lineno)
        )

    def _insert_class(self, module_id: int, node: ast.ClassDef, stats: dict) -> int:
        """Insert class record and return its ID."""
        # Determine line range
        line_start = node.lineno
        line_end = getattr(node, 'end_lineno', line_start)

        docstring = ast.get_docstring(node)

        self.cursor.execute(
            """
            INSERT INTO classes
            (module_id, name, kind, line_start, line_end, docstring)
            VALUES (?, ?, 'class', ?, ?, ?)
            """,
            (module_id, node.name, line_start, line_end, docstring)
        )
        class_id = self.cursor.lastrowid

        # Extract inheritance relationships
        for position, base in enumerate(node.bases):
            base_name = self._extract_name_from_node(base)
            if base_name:
                self.cursor.execute(
                    """
                    INSERT INTO inheritance
                    (class_id, base_class_name, relationship_kind, position)
                    VALUES (?, ?, 'inherits', ?)
                    """,
                    (class_id, base_name, position)
                )
                stats["inheritance_found"] += 1

        return class_id

    def _insert_function(self, module_id: int, class_id: Optional[int],
                        node: ast.FunctionDef, is_async: bool) -> int:
        """Insert function record and return its ID."""
        line_start = node.lineno
        line_end = getattr(node, 'end_lineno', line_start)
        docstring = ast.get_docstring(node)

        # Calculate simple cyclomatic complexity (branches + 1)
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                                 ast.With, ast.Assert, ast.comprehension)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        kind = 'method' if class_id else 'function'
        if node.name == '__init__':
            kind = 'constructor'

        self.cursor.execute(
            """
            INSERT INTO functions
            (module_id, class_id, name, kind, line_start, line_end,
             docstring, cyclomatic_complexity, is_async)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (module_id, class_id, node.name, kind, line_start, line_end,
             docstring, complexity, is_async)
        )
        function_id = self.cursor.lastrowid

        # Extract decorators
        for decorator in node.decorator_list:
            decorator_name = self._extract_name_from_node(decorator)
            if decorator_name:
                # Get arguments if present (for decorators like @app.route('/path'))
                args_str = None
                if isinstance(decorator, ast.Call):
                    args_str = ast.unparse(decorator) if hasattr(ast, 'unparse') else str(decorator)

                self.cursor.execute(
                    """
                    INSERT INTO decorators
                    (target_type, target_id, decorator_name, arguments, line_number)
                    VALUES ('function', ?, ?, ?, ?)
                    """,
                    (function_id, decorator_name, args_str, line_start)
                )

        # Extract type hints for parameters and return type
        for arg in node.args.args:
            if arg.annotation:
                type_str = self._extract_type_annotation(arg.annotation)
                if type_str:
                    self.cursor.execute(
                        """
                        INSERT INTO type_hints
                        (function_id, hint_type, parameter_name, type_annotation)
                        VALUES (?, 'parameter', ?, ?)
                        """,
                        (function_id, arg.arg, type_str)
                    )

        # Extract return type hint
        if node.returns:
            type_str = self._extract_type_annotation(node.returns)
            if type_str:
                self.cursor.execute(
                    """
                    INSERT INTO type_hints
                    (function_id, hint_type, type_annotation)
                    VALUES (?, 'return', ?)
                    """,
                    (function_id, type_str)
                )

        return function_id

    def _extract_name_from_node(self, node: ast.AST) -> Optional[str]:
        """Extract a name string from an AST node (Name, Attribute, Call, etc.)."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            # For things like "os.path.join", recursively build the full name
            value_name = self._extract_name_from_node(node.value)
            if value_name:
                return f"{value_name}.{node.attr}"
            return node.attr
        elif isinstance(node, ast.Call):
            # For decorator calls like @decorator(), extract the function being called
            return self._extract_name_from_node(node.func)
        elif isinstance(node, ast.Subscript):
            # For things like List[str], Dict[str, int]
            return self._extract_name_from_node(node.value)
        return None

    def _extract_type_annotation(self, node: ast.AST) -> Optional[str]:
        """Extract type annotation as a string from an AST node."""
        try:
            # Python 3.9+ has ast.unparse
            if hasattr(ast, 'unparse'):
                return ast.unparse(node)
            # Fallback for older Python versions
            elif isinstance(node, ast.Name):
                return node.id
            elif isinstance(node, ast.Attribute):
                value_name = self._extract_type_annotation(node.value)
                if value_name:
                    return f"{value_name}.{node.attr}"
                return node.attr
            elif isinstance(node, ast.Subscript):
                # Handle generics like List[str]
                base = self._extract_type_annotation(node.value)
                # Note: ast.Index was removed in Python 3.9
                if hasattr(node.slice, 'value'):
                    slice_val = self._extract_type_annotation(node.slice.value)
                else:
                    slice_val = self._extract_type_annotation(node.slice)
                if base and slice_val:
                    return f"{base}[{slice_val}]"
                return base
            elif isinstance(node, ast.Tuple):
                # Handle Tuple types
                elements = [self._extract_type_annotation(elt) for elt in node.elts]
                return ", ".join(e for e in elements if e)
            elif isinstance(node, ast.Constant):
                # For string literals in type hints
                return str(node.value)
            else:
                return str(type(node).__name__)
        except Exception:
            return None
