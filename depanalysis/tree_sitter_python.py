"""
Tree-sitter-based Python parser for structural analysis.

Parses Python files using tree-sitter to extract modules, classes, functions,
and their relationships, populating the structure.db database.
"""
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from tree_sitter import Language, Node, Tree
import tree_sitter_python

from .tree_sitter_base import TreeSitterParser


class TreeSitterPythonParser(TreeSitterParser):
    """Analyzes Python code structure using tree-sitter."""

    def __init__(self, repo_path: Path, db_connection: sqlite3.Connection):
        """Initialize Python parser."""
        super().__init__(repo_path, db_connection, "python")

    def _load_language(self) -> Language:
        """Load tree-sitter Python language."""
        return Language(tree_sitter_python.language())

    def _get_file_extensions(self) -> List[str]:
        """Get Python file extensions."""
        return [".py", ".pyw"]

    def _should_skip_directory(self, dir_name: str) -> bool:
        """Check if directory should be skipped."""
        skip_dirs = {".git", "__pycache__", ".venv", "venv", ".tox", ".pytest_cache",
                    ".mypy_cache", "node_modules", "build", "dist", "*.egg-info"}
        return dir_name in skip_dirs or dir_name.endswith(".egg-info")

    def _analyze_tree(self, tree: Tree, module_id: int, content: str, stats: dict) -> None:
        """Analyze Python parse tree."""
        root_node = tree.root_node

        # Track current context (class and function IDs)
        context = {"class_id": None, "function_id": None}

        # Traverse and analyze nodes
        self._analyze_node(root_node, module_id, content, stats, context)

    def _analyze_node(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Recursively analyze tree-sitter nodes."""

        # Handle imports
        if node.type == "import_statement":
            self._handle_import_statement(node, module_id, content, stats)

        elif node.type == "import_from_statement":
            self._handle_import_from_statement(node, module_id, content, stats)

        # Handle class definitions
        elif node.type == "class_definition":
            self._handle_class_definition(node, module_id, content, stats, context)
            return  # Don't traverse children - handled in class definition

        # Handle function definitions
        elif node.type in ("function_definition", "decorated_definition"):
            if node.type == "decorated_definition":
                # Check if it's a decorated function
                func_node = self.find_child_by_type(node, "function_definition")
                if func_node:
                    self._handle_function_definition(node, module_id, content, stats, context, is_decorated=True)
                    return
            else:
                self._handle_function_definition(node, module_id, content, stats, context)
                return  # Don't traverse children - handled in function definition

        # Handle calls (only inside functions)
        elif node.type == "call" and context["function_id"] is not None:
            self._handle_call(node, content, stats, context["function_id"])

        # Handle class-level variable assignments
        elif node.type == "assignment" and context["class_id"] is not None and context["function_id"] is None:
            self._handle_class_variable(node, module_id, content, stats, context["class_id"])

        # Recursively analyze children
        for child in node.children:
            self._analyze_node(child, module_id, content, stats, context)

    def _handle_import_statement(self, node: Node, module_id: int, content: str, stats: dict) -> None:
        """Handle 'import module' statements."""
        # import a, b, c
        for child in node.children:
            if child.type == "dotted_name" or child.type == "identifier":
                module_name = self.get_node_text(child, content)
                self._insert_import(
                    module_id,
                    module_name,
                    module_name,
                    "import",
                    self.get_line_number(node)
                )
                stats["imports_found"] += 1
            elif child.type == "aliased_import":
                name_node = self.find_child_by_field(child, "name")
                alias_node = self.find_child_by_field(child, "alias")
                if name_node:
                    module_name = self.get_node_text(name_node, content)
                    alias = self.get_node_text(alias_node, content) if alias_node else None
                    self._insert_import(
                        module_id,
                        module_name,
                        module_name,
                        "import",
                        self.get_line_number(node),
                        alias=alias
                    )
                    stats["imports_found"] += 1

    def _handle_import_from_statement(self, node: Node, module_id: int, content: str, stats: dict) -> None:
        """Handle 'from module import name' statements."""
        # Extract module name
        module_node = self.find_child_by_field(node, "module_name")
        if not module_node:
            # Could be relative import (from . import x)
            # Check for relative import dots
            module_name = ""
            is_relative = False
            for child in node.children:
                if child.type == "relative_import":
                    dots = self.get_node_text(child, content)
                    module_name = dots
                    is_relative = True
                elif child.type == "dotted_name":
                    if is_relative:
                        module_name += self.get_node_text(child, content)
                    else:
                        module_name = self.get_node_text(child, content)
        else:
            module_name = self.get_node_text(module_node, content)
            is_relative = module_name.startswith(".")

        # Extract imported names
        for child in node.children:
            if child.type == "dotted_name" and child != module_node:
                import_name = self.get_node_text(child, content)
                self._insert_import(
                    module_id,
                    module_name,
                    import_name,
                    "import",
                    self.get_line_number(node),
                    is_relative=is_relative
                )
                stats["imports_found"] += 1
            elif child.type == "identifier" and self.get_node_text(child, content) not in ("import", "from", "as"):
                import_name = self.get_node_text(child, content)
                self._insert_import(
                    module_id,
                    module_name,
                    import_name,
                    "import",
                    self.get_line_number(node),
                    is_relative=is_relative
                )
                stats["imports_found"] += 1
            elif child.type == "aliased_import":
                name_node = self.find_child_by_field(child, "name")
                alias_node = self.find_child_by_field(child, "alias")
                if name_node:
                    import_name = self.get_node_text(name_node, content)
                    alias = self.get_node_text(alias_node, content) if alias_node else None
                    self._insert_import(
                        module_id,
                        module_name,
                        import_name,
                        "import",
                        self.get_line_number(node),
                        alias=alias,
                        is_relative=is_relative
                    )
                    stats["imports_found"] += 1
            elif child.type == "wildcard_import":
                self._insert_import(
                    module_id,
                    module_name,
                    "*",
                    "import",
                    self.get_line_number(node),
                    is_relative=is_relative,
                    is_wildcard=True
                )
                stats["imports_found"] += 1

    def _handle_class_definition(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Handle class definitions."""
        # Get class name
        name_node = self.find_child_by_field(node, "name")
        if not name_node:
            return

        class_name = self.get_node_text(name_node, content)

        # Get docstring if present
        docstring = self._extract_docstring(node, content)

        # Insert class
        class_id = self._insert_class(
            module_id,
            class_name,
            "class",
            self.get_line_number(node),
            self.get_end_line_number(node),
            docstring
        )
        stats["classes_found"] += 1

        # Extract base classes
        superclasses_node = self.find_child_by_field(node, "superclasses")
        if superclasses_node:
            position = 0
            for child in superclasses_node.children:
                if child.type in ("identifier", "attribute", "subscript"):
                    base_name = self.get_node_text(child, content)
                    self._insert_inheritance(class_id, base_name, "inherits", position)
                    stats["inheritance_found"] += 1
                    position += 1

        # Analyze class body with updated context
        body_node = self.find_child_by_field(node, "body")
        if body_node:
            old_class_id = context["class_id"]
            context["class_id"] = class_id
            self._analyze_node(body_node, module_id, content, stats, context)
            context["class_id"] = old_class_id

    def _handle_function_definition(self, node: Node, module_id: int, content: str, stats: dict, context: dict, is_decorated: bool = False) -> None:
        """Handle function definitions."""
        # If decorated, get the actual function definition
        func_node = node
        decorators = []
        if is_decorated:
            # Extract decorators
            for child in node.children:
                if child.type == "decorator":
                    decorator_name = self._extract_decorator_name(child, content)
                    if decorator_name:
                        decorators.append((decorator_name, self.get_node_text(child, content)))
                elif child.type == "function_definition":
                    func_node = child

        # Get function name
        name_node = self.find_child_by_field(func_node, "name")
        if not name_node:
            return

        func_name = self.get_node_text(name_node, content)

        # Check if async
        is_async = False
        for child in func_node.children:
            if child.type == "async" or self.get_node_text(child, content) == "async":
                is_async = True
                break

        # Calculate complexity
        complexity = self._calculate_complexity(func_node)

        # Get docstring
        docstring = self._extract_docstring(func_node, content)

        # Determine kind
        kind = "function"
        if context["class_id"] is not None:
            if func_name == "__init__":
                kind = "constructor"
            else:
                kind = "method"
        if is_async:
            kind = "async_" + kind

        # Insert function
        function_id = self._insert_function(
            module_id,
            func_name,
            kind,
            self.get_line_number(node),
            self.get_end_line_number(func_node),
            class_id=context["class_id"],
            docstring=docstring,
            cyclomatic_complexity=complexity,
            is_async=is_async
        )
        stats["functions_found"] += 1

        # Insert decorators
        for decorator_name, decorator_text in decorators:
            self._insert_decorator("function", function_id, decorator_name, self.get_line_number(node), decorator_text)
            stats["decorators_found"] += 1

        # Extract type hints from parameters
        params_node = self.find_child_by_field(func_node, "parameters")
        if params_node:
            for param in params_node.children:
                if param.type == "typed_parameter" or param.type == "typed_default_parameter":
                    param_name_node = self.find_child_by_field(param, "name")
                    param_type_node = self.find_child_by_field(param, "type")
                    if param_name_node and param_type_node:
                        param_name = self.get_node_text(param_name_node, content)
                        param_type = self.get_node_text(param_type_node, content)
                        self._insert_type_hint("parameter", param_type, function_id=function_id, parameter_name=param_name)
                        stats["type_hints_found"] += 1

        # Extract return type hint
        return_type_node = self.find_child_by_field(func_node, "return_type")
        if return_type_node:
            return_type = self.get_node_text(return_type_node, content)
            self._insert_type_hint("return", return_type, function_id=function_id)
            stats["type_hints_found"] += 1

        # Analyze function body with updated context
        body_node = self.find_child_by_field(func_node, "body")
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

    def _handle_class_variable(self, node: Node, module_id: int, content: str, stats: dict, class_id: int) -> None:
        """Handle class-level variable assignments."""
        # Get variable name from left side of assignment
        left_node = self.find_child_by_field(node, "left")
        if left_node and left_node.type == "identifier":
            var_name = self.get_node_text(left_node, content)

            # Check for type annotation
            type_node = self.find_child_by_field(node, "type")
            type_annotation = self.get_node_text(type_node, content) if type_node else None

            var_id = self._insert_variable(module_id, var_name, "field", self.get_line_number(node), class_id=class_id)
            stats["variables_found"] += 1

            if type_annotation:
                self._insert_type_hint("variable", type_annotation, variable_id=var_id)
                stats["type_hints_found"] += 1

    def _extract_docstring(self, node: Node, content: str) -> Optional[str]:
        """Extract docstring from a function or class definition."""
        body_node = self.find_child_by_field(node, "body")
        if body_node:
            # Check if first statement is a string
            for child in body_node.children:
                if child.type == "expression_statement":
                    expr_child = child.children[0] if child.children else None
                    if expr_child and expr_child.type == "string":
                        docstring = self.get_node_text(expr_child, content)
                        # Remove quotes
                        if docstring.startswith('"""') or docstring.startswith("'''"):
                            return docstring[3:-3].strip()
                        elif docstring.startswith('"') or docstring.startswith("'"):
                            return docstring[1:-1].strip()
                        return docstring
                    break
        return None

    def _extract_decorator_name(self, decorator_node: Node, content: str) -> Optional[str]:
        """Extract decorator name from a decorator node."""
        for child in decorator_node.children:
            if child.type == "identifier":
                return self.get_node_text(child, content)
            elif child.type == "attribute":
                return self.get_node_text(child, content)
            elif child.type == "call":
                func_node = self.find_child_by_field(child, "function")
                if func_node:
                    return self.get_node_text(func_node, content)
        return None

    def _calculate_complexity(self, node: Node) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1

        def count_branches(n: Node, depth: int) -> bool:
            nonlocal complexity
            if n.type in ("if_statement", "while_statement", "for_statement",
                         "except_clause", "with_statement", "assert_statement",
                         "conditional_expression"):
                complexity += 1
            elif n.type == "boolean_operator":
                # Count each additional condition
                complexity += len(n.children) - 1
            return True

        self.traverse(node, count_branches)
        return complexity
