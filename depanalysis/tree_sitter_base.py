"""
Base tree-sitter parser for multi-language structural analysis.

Provides common functionality for all tree-sitter-based parsers including:
- File hash tracking for incremental updates
- Tree-sitter grammar loading
- Common node traversal utilities
- Database interaction patterns
"""
import hashlib
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List, Set

try:
    from tree_sitter import Language, Parser, Node, Tree
except ImportError:
    raise ImportError(
        "tree-sitter is not installed. Please install it with: "
        "pip install tree-sitter tree-sitter-python tree-sitter-javascript "
        "tree-sitter-typescript tree-sitter-c-sharp tree-sitter-java "
        "tree-sitter-rust tree-sitter-cpp tree-sitter-go"
    )


class TreeSitterParser(ABC):
    """Base class for tree-sitter-based language parsers."""

    def __init__(self, repo_path: Path, db_connection: sqlite3.Connection, language_name: str):
        """
        Initialize tree-sitter parser.

        Args:
            repo_path: Path to the repository root
            db_connection: SQLite connection to structure.db
            language_name: Name of the language (e.g., 'python', 'typescript')
        """
        self.repo_path = Path(repo_path)
        self.conn = db_connection
        self.cursor = self.conn.cursor()
        self.language_name = language_name

        # Get or create language ID
        self.language_id = self._get_or_create_language_id(language_name)

        # Initialize tree-sitter parser with language (API v0.22+)
        self.language = self._load_language()
        self.parser = Parser(self.language)

    @abstractmethod
    def _load_language(self) -> Language:
        """
        Load the tree-sitter language grammar.

        Must be implemented by subclasses to load the appropriate language.

        Returns:
            Tree-sitter Language object
        """
        pass

    @abstractmethod
    def _get_file_extensions(self) -> List[str]:
        """
        Get file extensions to parse for this language.

        Returns:
            List of file extensions (e.g., ['.py', '.pyw'])
        """
        pass

    @abstractmethod
    def _should_skip_directory(self, dir_name: str) -> bool:
        """
        Check if a directory should be skipped during analysis.

        Args:
            dir_name: Name of the directory

        Returns:
            True if directory should be skipped
        """
        pass

    @abstractmethod
    def _analyze_tree(self, tree: Tree, module_id: int, content: str, stats: dict) -> None:
        """
        Analyze a tree-sitter parse tree and extract structural information.

        Must be implemented by subclasses to handle language-specific node types.

        Args:
            tree: Tree-sitter parse tree
            module_id: Database ID of the module being analyzed
            content: Source code content
            stats: Statistics dictionary to update
        """
        pass

    def _get_or_create_language_id(self, language: str) -> int:
        """Get the ID for a language from the database, creating if needed."""
        self.cursor.execute("SELECT id FROM languages WHERE name = ?", (language,))
        result = self.cursor.fetchone()
        if result:
            return result[0]

        # Create if not found
        self.cursor.execute("INSERT INTO languages (name) VALUES (?)", (language,))
        return self.cursor.lastrowid

    def analyze(self) -> dict:
        """
        Perform full structural analysis of the repository.

        Returns:
            Dictionary with analysis statistics
        """
        stats = {
            "files_parsed": 0,
            "files_skipped": 0,
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

        # Walk through all files matching the language's extensions
        for extension in self._get_file_extensions():
            for file_path in self.repo_path.rglob(f"*{extension}"):
                # Skip excluded directories
                if any(self._should_skip_directory(part) for part in file_path.parts):
                    stats["files_skipped"] += 1
                    continue

                try:
                    self._analyze_file(file_path, stats)
                    stats["files_parsed"] += 1
                except Exception as e:
                    # Silently skip files with errors
                    stats["errors"] += 1

        self.conn.commit()
        return stats

    def _analyze_file(self, file_path: Path, stats: dict) -> None:
        """Analyze a single source file."""
        # Calculate relative path for storage
        rel_path = str(file_path.relative_to(self.repo_path))

        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return  # Skip binary or weird encoding files

        # Calculate hash
        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Check if file has changed since last parse
        self.cursor.execute(
            "SELECT file_hash FROM modules WHERE language_id = ? AND path = ?",
            (self.language_id, rel_path)
        )
        result = self.cursor.fetchone()
        if result and result[0] == file_hash:
            # File unchanged, skip parsing
            stats["files_skipped"] += 1
            return

        # Parse with tree-sitter
        tree = self.parser.parse(bytes(content, "utf-8"))

        # Insert or update module
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO modules
            (language_id, path, name, file_hash, last_parsed)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (self.language_id, rel_path, file_path.stem, file_hash)
        )
        module_id = self.cursor.lastrowid

        # Analyze the tree (language-specific implementation)
        self._analyze_tree(tree, module_id, content, stats)

    # Helper methods for extracting information from tree-sitter nodes

    def get_node_text(self, node: Node, content: str) -> str:
        """Extract text content from a node."""
        return content[node.start_byte:node.end_byte]

    def get_line_number(self, node: Node) -> int:
        """Get the line number of a node (1-indexed)."""
        return node.start_point[0] + 1

    def get_end_line_number(self, node: Node) -> int:
        """Get the end line number of a node (1-indexed)."""
        return node.end_point[0] + 1

    def find_child_by_type(self, node: Node, child_type: str) -> Optional[Node]:
        """Find first child node of a specific type."""
        for child in node.children:
            if child.type == child_type:
                return child
        return None

    def find_children_by_type(self, node: Node, child_type: str) -> List[Node]:
        """Find all child nodes of a specific type."""
        return [child for child in node.children if child.type == child_type]

    def find_child_by_field(self, node: Node, field_name: str) -> Optional[Node]:
        """Find child node by field name."""
        return node.child_by_field_name(field_name)

    def traverse(self, node: Node, visit_func, depth: int = 0):
        """
        Recursively traverse tree-sitter nodes.

        Args:
            node: Current node
            visit_func: Callback function(node, depth) -> bool
                       Return True to continue traversing children
            depth: Current depth in the tree
        """
        should_continue = visit_func(node, depth)
        if should_continue:
            for child in node.children:
                self.traverse(child, visit_func, depth + 1)

    # Database helper methods

    def _insert_import(
        self,
        module_id: int,
        to_module: str,
        import_name: str,
        import_kind: str,
        line_number: int,
        alias: Optional[str] = None,
        is_relative: bool = False,
        is_dynamic: bool = False,
        is_wildcard: bool = False
    ) -> int:
        """Insert import record and return its ID."""
        self.cursor.execute(
            """
            INSERT INTO imports
            (from_module_id, to_module, import_name, alias, import_kind,
             is_relative, is_dynamic, is_wildcard, line_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (module_id, to_module, import_name, alias, import_kind,
             is_relative, is_dynamic, is_wildcard, line_number)
        )
        return self.cursor.lastrowid

    def _insert_class(
        self,
        module_id: int,
        name: str,
        kind: str,
        line_start: int,
        line_end: int,
        docstring: Optional[str] = None
    ) -> int:
        """Insert class record and return its ID."""
        self.cursor.execute(
            """
            INSERT INTO classes
            (module_id, name, kind, line_start, line_end, docstring)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (module_id, name, kind, line_start, line_end, docstring)
        )
        return self.cursor.lastrowid

    def _insert_function(
        self,
        module_id: int,
        name: str,
        kind: str,
        line_start: int,
        line_end: int,
        class_id: Optional[int] = None,
        docstring: Optional[str] = None,
        cyclomatic_complexity: int = 1,
        is_async: bool = False
    ) -> int:
        """Insert function record and return its ID."""
        self.cursor.execute(
            """
            INSERT INTO functions
            (module_id, class_id, name, kind, line_start, line_end,
             docstring, cyclomatic_complexity, is_async)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (module_id, class_id, name, kind, line_start, line_end,
             docstring, cyclomatic_complexity, is_async)
        )
        return self.cursor.lastrowid

    def _insert_inheritance(
        self,
        class_id: int,
        base_class_name: str,
        relationship_kind: str,
        position: int = 0
    ) -> int:
        """Insert inheritance record and return its ID."""
        self.cursor.execute(
            """
            INSERT INTO inheritance
            (class_id, base_class_name, relationship_kind, position)
            VALUES (?, ?, ?, ?)
            """,
            (class_id, base_class_name, relationship_kind, position)
        )
        return self.cursor.lastrowid

    def _insert_decorator(
        self,
        target_type: str,
        target_id: int,
        decorator_name: str,
        line_number: int,
        arguments: Optional[str] = None
    ) -> int:
        """Insert decorator record and return its ID."""
        self.cursor.execute(
            """
            INSERT INTO decorators
            (target_type, target_id, decorator_name, arguments, line_number)
            VALUES (?, ?, ?, ?, ?)
            """,
            (target_type, target_id, decorator_name, arguments, line_number)
        )
        return self.cursor.lastrowid

    def _insert_type_hint(
        self,
        hint_type: str,
        type_annotation: str,
        function_id: Optional[int] = None,
        variable_id: Optional[int] = None,
        parameter_name: Optional[str] = None
    ) -> int:
        """Insert type hint record and return its ID."""
        self.cursor.execute(
            """
            INSERT INTO type_hints
            (function_id, variable_id, hint_type, parameter_name, type_annotation)
            VALUES (?, ?, ?, ?, ?)
            """,
            (function_id, variable_id, hint_type, parameter_name, type_annotation)
        )
        return self.cursor.lastrowid

    def _insert_variable(
        self,
        module_id: int,
        name: str,
        kind: str,
        line_number: int,
        class_id: Optional[int] = None,
        function_id: Optional[int] = None
    ) -> int:
        """Insert variable record and return its ID."""
        self.cursor.execute(
            """
            INSERT INTO variables
            (module_id, class_id, function_id, name, kind, line_number)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (module_id, class_id, function_id, name, kind, line_number)
        )
        return self.cursor.lastrowid

    def _insert_call(
        self,
        from_function_id: int,
        to_name: str,
        call_kind: str,
        line_number: int
    ) -> int:
        """Insert function call record and return its ID."""
        self.cursor.execute(
            """
            INSERT INTO calls
            (from_function_id, to_name, call_kind, line_number)
            VALUES (?, ?, ?, ?)
            """,
            (from_function_id, to_name, call_kind, line_number)
        )
        return self.cursor.lastrowid
