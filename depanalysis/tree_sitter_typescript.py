"""
Tree-sitter-based TypeScript/JavaScript parser for structural analysis.

Parses TypeScript and JavaScript files using tree-sitter to extract modules,
classes, functions, and their relationships, populating the structure.db database.
"""
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from tree_sitter import Language, Node, Tree
import tree_sitter_typescript
import tree_sitter_javascript

from .tree_sitter_base import TreeSitterParser


class TreeSitterTypeScriptParser(TreeSitterParser):
    """Analyzes TypeScript code structure using tree-sitter."""

    def __init__(self, repo_path: Path, db_connection: sqlite3.Connection):
        """Initialize TypeScript parser."""
        super().__init__(repo_path, db_connection, "typescript")

    def _load_language(self) -> Language:
        """Load tree-sitter TypeScript language."""
        return Language(tree_sitter_typescript.language_typescript())

    def _get_file_extensions(self) -> List[str]:
        """Get TypeScript file extensions."""
        return [".ts", ".tsx"]

    def _should_skip_directory(self, dir_name: str) -> bool:
        """Check if directory should be skipped."""
        skip_dirs = {".git", "node_modules", "dist", "build", ".next", "coverage",
                    ".cache", "out", "__pycache__", ".tsbuildinfo"}
        return dir_name in skip_dirs

    def _analyze_tree(self, tree: Tree, module_id: int, content: str, stats: dict) -> None:
        """Analyze TypeScript parse tree."""
        root_node = tree.root_node

        # Track current context
        context = {"class_id": None, "function_id": None}

        # Traverse and analyze nodes
        self._analyze_node(root_node, module_id, content, stats, context)

    def _analyze_node(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Recursively analyze tree-sitter nodes."""

        # Handle imports
        if node.type == "import_statement":
            self._handle_import_statement(node, module_id, content, stats)

        # Handle class declarations
        elif node.type == "class_declaration":
            self._handle_class_declaration(node, module_id, content, stats, context)
            return

        # Handle interface declarations (treat as classes with kind='interface')
        elif node.type == "interface_declaration":
            self._handle_interface_declaration(node, module_id, content, stats, context)
            return

        # Handle function declarations
        elif node.type == "function_declaration":
            self._handle_function_declaration(node, module_id, content, stats, context)
            return

        # Handle method definitions (inside classes)
        elif node.type == "method_definition" and context["class_id"] is not None:
            self._handle_method_definition(node, module_id, content, stats, context)
            return

        # Handle arrow functions and function expressions (lexical declarations)
        elif node.type == "lexical_declaration":
            self._handle_lexical_declaration(node, module_id, content, stats, context)

        # Handle calls (only inside functions)
        elif node.type == "call_expression" and context["function_id"] is not None:
            self._handle_call(node, content, stats, context["function_id"])

        # Recursively analyze children
        for child in node.children:
            self._analyze_node(child, module_id, content, stats, context)

    def _handle_import_statement(self, node: Node, module_id: int, content: str, stats: dict) -> None:
        """Handle import statements."""
        # Extract the module source (the string being imported from)
        source_node = self.find_child_by_field(node, "source")
        if not source_node:
            return

        module_path = self.get_node_text(source_node, content).strip('"\'')
        is_relative = module_path.startswith('./')  or module_path.startswith('../')

        # Handle different import types
        import_clause = self.find_child_by_type(node, "import_clause")
        if import_clause:
            # Named imports: import { a, b } from 'module'
            named_imports = self.find_child_by_type(import_clause, "named_imports")
            if named_imports:
                for child in named_imports.children:
                    if child.type == "import_specifier":
                        name_node = self.find_child_by_field(child, "name")
                        alias_node = self.find_child_by_field(child, "alias")
                        if name_node:
                            import_name = self.get_node_text(name_node, content)
                            alias = self.get_node_text(alias_node, content) if alias_node else None
                            self._insert_import(
                                module_id, module_path, import_name, "import",
                                self.get_line_number(node), alias=alias, is_relative=is_relative
                            )
                            stats["imports_found"] += 1

            # Namespace import: import * as name from 'module'
            namespace_import = self.find_child_by_type(import_clause, "namespace_import")
            if namespace_import:
                name_node = self.find_child_by_type(namespace_import, "identifier")
                if name_node:
                    alias = self.get_node_text(name_node, content)
                    self._insert_import(
                        module_id, module_path, "*", "import",
                        self.get_line_number(node), alias=alias, is_relative=is_relative, is_wildcard=True
                    )
                    stats["imports_found"] += 1

            # Default import: import name from 'module'
            default_import = self.find_child_by_type(import_clause, "identifier")
            if default_import:
                import_name = self.get_node_text(default_import, content)
                self._insert_import(
                    module_id, module_path, "default", "import",
                    self.get_line_number(node), alias=import_name, is_relative=is_relative
                )
                stats["imports_found"] += 1

    def _handle_class_declaration(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Handle class declarations."""
        # Get class name
        name_node = self.find_child_by_field(node, "name")
        if not name_node:
            return

        class_name = self.get_node_text(name_node, content)

        # Determine class kind (abstract, regular)
        kind = "class"
        for child in node.children:
            if self.get_node_text(child, content) == "abstract":
                kind = "abstract_class"
                break

        # Insert class
        class_id = self._insert_class(
            module_id,
            class_name,
            kind,
            self.get_line_number(node),
            self.get_end_line_number(node)
        )
        stats["classes_found"] += 1

        # Extract heritage (extends and implements)
        heritage_node = self.find_child_by_field(node, "heritage")
        if heritage_node:
            for child in heritage_node.children:
                if child.type == "extends_clause":
                    # Extract base class
                    for type_node in child.children:
                        if type_node.type in ("identifier", "member_expression", "generic_type"):
                            base_name = self.get_node_text(type_node, content)
                            self._insert_inheritance(class_id, base_name, "extends", 0)
                            stats["inheritance_found"] += 1
                            break
                elif child.type == "implements_clause":
                    # Extract interfaces
                    position = 0
                    for type_node in child.children:
                        if type_node.type in ("identifier", "generic_type"):
                            interface_name = self.get_node_text(type_node, content)
                            self._insert_inheritance(class_id, interface_name, "implements", position)
                            stats["inheritance_found"] += 1
                            position += 1

        # Analyze class body with updated context
        body_node = self.find_child_by_field(node, "body")
        if body_node:
            old_class_id = context["class_id"]
            context["class_id"] = class_id
            self._analyze_node(body_node, module_id, content, stats, context)
            context["class_id"] = old_class_id

    def _handle_interface_declaration(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Handle interface declarations."""
        # Get interface name
        name_node = self.find_child_by_field(node, "name")
        if not name_node:
            return

        interface_name = self.get_node_text(name_node, content)

        # Insert as class with kind='interface'
        class_id = self._insert_class(
            module_id,
            interface_name,
            "interface",
            self.get_line_number(node),
            self.get_end_line_number(node)
        )
        stats["classes_found"] += 1

        # Extract extended interfaces
        extends_node = self.find_child_by_field(node, "extends")
        if extends_node:
            position = 0
            for child in extends_node.children:
                if child.type in ("identifier", "generic_type"):
                    base_interface = self.get_node_text(child, content)
                    self._insert_inheritance(class_id, base_interface, "extends", position)
                    stats["inheritance_found"] += 1
                    position += 1

    def _handle_function_declaration(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Handle function declarations."""
        # Get function name
        name_node = self.find_child_by_field(node, "name")
        if not name_node:
            return

        func_name = self.get_node_text(name_node, content)

        # Check if async
        is_async = False
        for child in node.children:
            if self.get_node_text(child, content) == "async":
                is_async = True
                break

        # Calculate complexity
        complexity = self._calculate_complexity(node)

        # Determine kind
        kind = "async_function" if is_async else "function"

        # Insert function
        function_id = self._insert_function(
            module_id,
            func_name,
            kind,
            self.get_line_number(node),
            self.get_end_line_number(node),
            class_id=context["class_id"],
            cyclomatic_complexity=complexity,
            is_async=is_async
        )
        stats["functions_found"] += 1

        # Extract type annotations if TypeScript
        self._extract_function_type_hints(node, function_id, content, stats)

        # Analyze function body with updated context
        body_node = self.find_child_by_field(node, "body")
        if body_node:
            old_function_id = context["function_id"]
            context["function_id"] = function_id
            self._analyze_node(body_node, module_id, content, stats, context)
            context["function_id"] = old_function_id

    def _handle_method_definition(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Handle method definitions inside classes."""
        # Get method name
        name_node = self.find_child_by_field(node, "name")
        if not name_node:
            return

        method_name = self.get_node_text(name_node, content)

        # Check if async
        is_async = False
        for child in node.children:
            if self.get_node_text(child, content) == "async":
                is_async = True
                break

        # Determine kind
        kind = "constructor" if method_name == "constructor" else "method"
        if is_async:
            kind = "async_method"

        # Calculate complexity
        complexity = self._calculate_complexity(node)

        # Insert method
        function_id = self._insert_function(
            module_id,
            method_name,
            kind,
            self.get_line_number(node),
            self.get_end_line_number(node),
            class_id=context["class_id"],
            cyclomatic_complexity=complexity,
            is_async=is_async
        )
        stats["functions_found"] += 1

        # Extract type annotations if TypeScript
        self._extract_function_type_hints(node, function_id, content, stats)

        # Analyze method body with updated context
        body_node = self.find_child_by_field(node, "body")
        if body_node:
            old_function_id = context["function_id"]
            context["function_id"] = function_id
            self._analyze_node(body_node, module_id, content, stats, context)
            context["function_id"] = old_function_id

    def _handle_lexical_declaration(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Handle lexical declarations (const, let) that might be arrow functions."""
        # Look for variable declarators
        for child in node.children:
            if child.type == "variable_declarator":
                name_node = self.find_child_by_field(child, "name")
                value_node = self.find_child_by_field(child, "value")

                if name_node and value_node:
                    # Check if value is an arrow function or function expression
                    if value_node.type in ("arrow_function", "function_expression"):
                        func_name = self.get_node_text(name_node, content)

                        # Check if async
                        is_async = False
                        for val_child in value_node.children:
                            if self.get_node_text(val_child, content) == "async":
                                is_async = True
                                break

                        # Calculate complexity
                        complexity = self._calculate_complexity(value_node)

                        kind = "async_function" if is_async else "function"

                        # Insert function
                        function_id = self._insert_function(
                            module_id,
                            func_name,
                            kind,
                            self.get_line_number(child),
                            self.get_end_line_number(value_node),
                            class_id=context["class_id"],
                            cyclomatic_complexity=complexity,
                            is_async=is_async
                        )
                        stats["functions_found"] += 1

                        # Extract type annotations if TypeScript
                        self._extract_function_type_hints(value_node, function_id, content, stats)

                        # Analyze function body
                        body_node = self.find_child_by_field(value_node, "body")
                        if body_node:
                            old_function_id = context["function_id"]
                            context["function_id"] = function_id
                            self._analyze_node(body_node, module_id, content, stats, context)
                            context["function_id"] = old_function_id

    def _handle_call(self, node: Node, content: str, stats: dict, function_id: int) -> None:
        """Handle function calls."""
        # Get the function being called
        func_node = self.find_child_by_field(node, "function")
        if func_node:
            call_name = self.get_node_text(func_node, content)
            self._insert_call(function_id, call_name, "call", self.get_line_number(node))
            stats["calls_found"] += 1

    def _extract_function_type_hints(self, func_node: Node, function_id: int, content: str, stats: dict) -> None:
        """Extract TypeScript type annotations from function."""
        # Extract parameter types
        params_node = self.find_child_by_field(func_node, "parameters")
        if params_node:
            for param in params_node.children:
                if param.type in ("required_parameter", "optional_parameter"):
                    param_name_node = self.find_child_by_field(param, "pattern")
                    param_type_node = self.find_child_by_field(param, "type")

                    if param_name_node and param_type_node:
                        # Get the type annotation node
                        type_annotation = self.find_child_by_type(param_type_node, "type_annotation")
                        if type_annotation and type_annotation.children:
                            param_name = self.get_node_text(param_name_node, content)
                            param_type = self.get_node_text(type_annotation.children[0], content)
                            self._insert_type_hint("parameter", param_type, function_id=function_id, parameter_name=param_name)
                            stats["type_hints_found"] += 1

        # Extract return type
        return_type_node = self.find_child_by_field(func_node, "return_type")
        if return_type_node:
            # Get the actual type (skip the ':' token)
            for child in return_type_node.children:
                if child.type != ":":
                    return_type = self.get_node_text(child, content)
                    self._insert_type_hint("return", return_type, function_id=function_id)
                    stats["type_hints_found"] += 1
                    break

    def _calculate_complexity(self, node: Node) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1

        def count_branches(n: Node, depth: int) -> bool:
            nonlocal complexity
            if n.type in ("if_statement", "while_statement", "for_statement",
                         "for_in_statement", "switch_case", "catch_clause",
                         "ternary_expression"):
                complexity += 1
            elif n.type == "binary_expression":
                # Count logical operators
                operator_node = self.find_child_by_type(n, "||") or self.find_child_by_type(n, "&&")
                if operator_node:
                    complexity += 1
            return True

        self.traverse(node, count_branches)
        return complexity


class TreeSitterJavaScriptParser(TreeSitterParser):
    """Analyzes JavaScript code structure using tree-sitter."""

    def __init__(self, repo_path: Path, db_connection: sqlite3.Connection):
        """Initialize JavaScript parser."""
        super().__init__(repo_path, db_connection, "javascript")
        # Reuse TypeScript parser logic by composition
        self._ts_parser = TreeSitterTypeScriptParser.__new__(TreeSitterTypeScriptParser)
        self._ts_parser.repo_path = repo_path
        self._ts_parser.conn = db_connection
        self._ts_parser.cursor = self.cursor
        self._ts_parser.language_name = "javascript"
        self._ts_parser.language_id = self.language_id

    def _load_language(self) -> Language:
        """Load tree-sitter JavaScript language."""
        return Language(tree_sitter_javascript.language())

    def _get_file_extensions(self) -> List[str]:
        """Get JavaScript file extensions."""
        return [".js", ".jsx", ".mjs", ".cjs"]

    def _should_skip_directory(self, dir_name: str) -> bool:
        """Check if directory should be skipped."""
        skip_dirs = {".git", "node_modules", "dist", "build", ".next", "coverage",
                    ".cache", "out", "__pycache__"}
        return dir_name in skip_dirs

    def _analyze_tree(self, tree: Tree, module_id: int, content: str, stats: dict) -> None:
        """Analyze JavaScript parse tree (reuse TypeScript logic)."""
        # Delegate to TypeScript parser (JavaScript is subset of TypeScript)
        self._ts_parser._analyze_tree(tree, module_id, content, stats)
