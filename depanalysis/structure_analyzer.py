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
            new_class_id = self._insert_class(module_id, node)
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

    def _insert_class(self, module_id: int, node: ast.ClassDef) -> int:
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
        return self.cursor.lastrowid

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
        return self.cursor.lastrowid
