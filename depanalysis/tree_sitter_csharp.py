"""
Tree-sitter-based C# parser for structural analysis.

Parses C# files using tree-sitter to extract namespaces, classes, methods,
properties, and their relationships, populating the structure.db database.
"""
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from tree_sitter import Language, Node, Tree
import tree_sitter_c_sharp

from .tree_sitter_base import TreeSitterParser


class TreeSitterCSharpParser(TreeSitterParser):
    """Analyzes C# code structure using tree-sitter."""

    def __init__(self, repo_path: Path, db_connection: sqlite3.Connection):
        """Initialize C# parser."""
        super().__init__(repo_path, db_connection, "csharp")

    def _load_language(self) -> Language:
        """Load tree-sitter C# language."""
        return Language(tree_sitter_c_sharp.language())

    def _get_file_extensions(self) -> List[str]:
        """Get C# file extensions."""
        return [".cs"]

    def _should_skip_directory(self, dir_name: str) -> bool:
        """Check if directory should be skipped."""
        skip_dirs = {".git", "bin", "obj", "packages", ".vs", "node_modules",
                    "__pycache__", "TestResults", "Debug", "Release"}
        return dir_name in skip_dirs

    def _analyze_tree(self, tree: Tree, module_id: int, content: str, stats: dict) -> None:
        """Analyze C# parse tree."""
        root_node = tree.root_node

        # Extract namespace for context
        namespace = self._extract_namespace(root_node, content)

        # Track current context
        context = {
            "class_id": None,
            "function_id": None,
            "namespace": namespace
        }

        # Traverse and analyze nodes
        self._analyze_node(root_node, module_id, content, stats, context)

    def _analyze_node(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Recursively analyze tree-sitter nodes."""

        # Handle using directives
        if node.type == "using_directive":
            self._handle_using_directive(node, module_id, content, stats)

        # Handle class declarations
        elif node.type == "class_declaration":
            self._handle_class_declaration(node, module_id, content, stats, context)
            return

        # Handle interface declarations
        elif node.type == "interface_declaration":
            self._handle_interface_declaration(node, module_id, content, stats, context)
            return

        # Handle struct declarations
        elif node.type == "struct_declaration":
            self._handle_struct_declaration(node, module_id, content, stats, context)
            return

        # Handle enum declarations
        elif node.type == "enum_declaration":
            self._handle_enum_declaration(node, module_id, content, stats, context)
            return

        # Handle method declarations
        elif node.type == "method_declaration" and context["class_id"] is not None:
            self._handle_method_declaration(node, module_id, content, stats, context)
            return

        # Handle constructor declarations
        elif node.type == "constructor_declaration" and context["class_id"] is not None:
            self._handle_constructor_declaration(node, module_id, content, stats, context)
            return

        # Handle property declarations
        elif node.type == "property_declaration" and context["class_id"] is not None:
            self._handle_property_declaration(node, module_id, content, stats, context)

        # Handle field declarations
        elif node.type == "field_declaration" and context["class_id"] is not None:
            self._handle_field_declaration(node, module_id, content, stats, context)

        # Recursively analyze children
        for child in node.children:
            self._analyze_node(child, module_id, content, stats, context)

    def _extract_namespace(self, node: Node, content: str) -> Optional[str]:
        """Extract namespace from the file."""
        # Look for namespace declaration
        for child in node.children:
            if child.type == "namespace_declaration" or child.type == "file_scoped_namespace_declaration":
                name_node = self.find_child_by_field(child, "name")
                if name_node:
                    return self.get_node_text(name_node, content)
        return None

    def _handle_using_directive(self, node: Node, module_id: int, content: str, stats: dict) -> None:
        """Handle using directives (imports)."""
        # Get the namespace being imported
        name_node = self.find_child_by_field(node, "name")
        if name_node:
            namespace_name = self.get_node_text(name_node, content)

            # Check for alias
            alias_node = self.find_child_by_field(node, "alias")
            alias = self.get_node_text(alias_node, content) if alias_node else None

            self._insert_import(
                module_id,
                namespace_name,
                namespace_name.split('.')[-1],
                "using",
                self.get_line_number(node),
                alias=alias
            )
            stats["imports_found"] += 1

    def _handle_class_declaration(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Handle class declarations."""
        # Get class name
        name_node = self.find_child_by_field(node, "name")
        if not name_node:
            return

        class_name = self.get_node_text(name_node, content)

        # Build fully qualified name
        if context["namespace"]:
            full_name = f"{context['namespace']}.{class_name}"
        else:
            full_name = class_name

        # Determine class kind (abstract, sealed, static, etc.)
        kind = "class"
        modifiers = self._extract_modifiers(node, content)
        if "abstract" in modifiers:
            kind = "abstract_class"
        elif "static" in modifiers:
            kind = "static_class"
        elif "sealed" in modifiers:
            kind = "sealed_class"

        # Insert class
        class_id = self._insert_class(
            module_id,
            full_name,
            kind,
            self.get_line_number(node),
            self.get_end_line_number(node)
        )
        stats["classes_found"] += 1

        # Extract base list (inheritance)
        base_list_node = self.find_child_by_field(node, "bases")
        if base_list_node:
            self._extract_inheritance(base_list_node, class_id, content, stats)

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

        # Build fully qualified name
        if context["namespace"]:
            full_name = f"{context['namespace']}.{interface_name}"
        else:
            full_name = interface_name

        # Insert as class with kind='interface'
        class_id = self._insert_class(
            module_id,
            full_name,
            "interface",
            self.get_line_number(node),
            self.get_end_line_number(node)
        )
        stats["classes_found"] += 1

        # Extract base list
        base_list_node = self.find_child_by_field(node, "bases")
        if base_list_node:
            self._extract_inheritance(base_list_node, class_id, content, stats)

    def _handle_struct_declaration(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Handle struct declarations."""
        # Get struct name
        name_node = self.find_child_by_field(node, "name")
        if not name_node:
            return

        struct_name = self.get_node_text(name_node, content)

        # Build fully qualified name
        if context["namespace"]:
            full_name = f"{context['namespace']}.{struct_name}"
        else:
            full_name = struct_name

        # Insert as class with kind='struct'
        class_id = self._insert_class(
            module_id,
            full_name,
            "struct",
            self.get_line_number(node),
            self.get_end_line_number(node)
        )
        stats["classes_found"] += 1

        # Extract base list
        base_list_node = self.find_child_by_field(node, "bases")
        if base_list_node:
            self._extract_inheritance(base_list_node, class_id, content, stats)

        # Analyze struct body
        body_node = self.find_child_by_field(node, "body")
        if body_node:
            old_class_id = context["class_id"]
            context["class_id"] = class_id
            self._analyze_node(body_node, module_id, content, stats, context)
            context["class_id"] = old_class_id

    def _handle_enum_declaration(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Handle enum declarations."""
        # Get enum name
        name_node = self.find_child_by_field(node, "name")
        if not name_node:
            return

        enum_name = self.get_node_text(name_node, content)

        # Build fully qualified name
        if context["namespace"]:
            full_name = f"{context['namespace']}.{enum_name}"
        else:
            full_name = enum_name

        # Insert as class with kind='enum'
        self._insert_class(
            module_id,
            full_name,
            "enum",
            self.get_line_number(node),
            self.get_end_line_number(node)
        )
        stats["classes_found"] += 1

    def _handle_method_declaration(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Handle method declarations."""
        # Get method name
        name_node = self.find_child_by_field(node, "name")
        if not name_node:
            return

        method_name = self.get_node_text(name_node, content)

        # Extract modifiers
        modifiers = self._extract_modifiers(node, content)

        # Determine kind
        kind = "method"
        if "async" in modifiers:
            kind = "async_method"
        elif "static" in modifiers:
            kind = "static_method"
        elif "abstract" in modifiers:
            kind = "abstract_method"

        is_async = "async" in modifiers

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

        # Extract type hints from parameters and return type
        self._extract_method_type_hints(node, function_id, content, stats)

        # Analyze method body
        body_node = self.find_child_by_field(node, "body")
        if body_node:
            old_function_id = context["function_id"]
            context["function_id"] = function_id
            self._analyze_node(body_node, module_id, content, stats, context)
            context["function_id"] = old_function_id

    def _handle_constructor_declaration(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Handle constructor declarations."""
        # Get constructor name
        name_node = self.find_child_by_field(node, "name")
        if not name_node:
            return

        constructor_name = self.get_node_text(name_node, content)

        # Calculate complexity
        complexity = self._calculate_complexity(node)

        # Insert constructor
        function_id = self._insert_function(
            module_id,
            constructor_name,
            "constructor",
            self.get_line_number(node),
            self.get_end_line_number(node),
            class_id=context["class_id"],
            cyclomatic_complexity=complexity,
            is_async=False
        )
        stats["functions_found"] += 1

        # Extract parameter type hints
        params_node = self.find_child_by_field(node, "parameters")
        if params_node:
            self._extract_parameter_type_hints(params_node, function_id, content, stats)

    def _handle_property_declaration(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Handle property declarations."""
        # Get property name
        name_node = self.find_child_by_field(node, "name")
        if not name_node:
            return

        property_name = self.get_node_text(name_node, content)

        # Insert as variable with kind='property'
        var_id = self._insert_variable(
            module_id,
            property_name,
            "property",
            self.get_line_number(node),
            class_id=context["class_id"]
        )
        stats["variables_found"] += 1

        # Extract type
        type_node = self.find_child_by_field(node, "type")
        if type_node:
            type_annotation = self.get_node_text(type_node, content)
            self._insert_type_hint("variable", type_annotation, variable_id=var_id)
            stats["type_hints_found"] += 1

    def _handle_field_declaration(self, node: Node, module_id: int, content: str, stats: dict, context: dict) -> None:
        """Handle field declarations."""
        # Get variable declaration
        var_declaration = self.find_child_by_type(node, "variable_declaration")
        if not var_declaration:
            return

        # Get type
        type_node = self.find_child_by_field(var_declaration, "type")
        type_annotation = self.get_node_text(type_node, content) if type_node else None

        # Extract modifiers
        modifiers = self._extract_modifiers(node, content)

        # Determine kind
        kind = "field"
        if "const" in modifiers:
            kind = "constant"
        elif "readonly" in modifiers:
            kind = "readonly_field"

        # Get variable declarator(s)
        for child in var_declaration.children:
            if child.type == "variable_declarator":
                name_node = self.find_child_by_field(child, "name")
                if name_node:
                    field_name = self.get_node_text(name_node, content)

                    var_id = self._insert_variable(
                        module_id,
                        field_name,
                        kind,
                        self.get_line_number(node),
                        class_id=context["class_id"]
                    )
                    stats["variables_found"] += 1

                    if type_annotation:
                        self._insert_type_hint("variable", type_annotation, variable_id=var_id)
                        stats["type_hints_found"] += 1

    def _extract_modifiers(self, node: Node, content: str) -> set:
        """Extract modifiers from a declaration node."""
        modifiers = set()
        for child in node.children:
            if child.type == "modifier":
                modifier_text = self.get_node_text(child, content)
                modifiers.add(modifier_text)
        return modifiers

    def _extract_inheritance(self, base_list_node: Node, class_id: int, content: str, stats: dict) -> None:
        """Extract and insert inheritance relationships."""
        position = 0
        for child in base_list_node.children:
            if child.type in ("identifier", "qualified_name", "generic_name"):
                base_name = self.get_node_text(child, content)

                # First item is typically base class, rest are interfaces
                # In C#, if it starts with I and is capitalized, it's likely an interface
                if position == 0 and not base_name.startswith("I"):
                    relationship_kind = "inherits"
                else:
                    relationship_kind = "implements"

                self._insert_inheritance(class_id, base_name, relationship_kind, position)
                stats["inheritance_found"] += 1
                position += 1

    def _extract_method_type_hints(self, method_node: Node, function_id: int, content: str, stats: dict) -> None:
        """Extract type hints from method parameters and return type."""
        # Extract parameter types
        params_node = self.find_child_by_field(method_node, "parameters")
        if params_node:
            self._extract_parameter_type_hints(params_node, function_id, content, stats)

        # Extract return type
        return_type_node = self.find_child_by_field(method_node, "type")
        if return_type_node:
            return_type = self.get_node_text(return_type_node, content)
            if return_type != "void":
                self._insert_type_hint("return", return_type, function_id=function_id)
                stats["type_hints_found"] += 1

    def _extract_parameter_type_hints(self, params_node: Node, function_id: int, content: str, stats: dict) -> None:
        """Extract type hints from parameters."""
        for child in params_node.children:
            if child.type == "parameter":
                param_name_node = self.find_child_by_field(child, "name")
                param_type_node = self.find_child_by_field(child, "type")

                if param_name_node and param_type_node:
                    param_name = self.get_node_text(param_name_node, content)
                    param_type = self.get_node_text(param_type_node, content)
                    self._insert_type_hint("parameter", param_type, function_id=function_id, parameter_name=param_name)
                    stats["type_hints_found"] += 1

    def _calculate_complexity(self, node: Node) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1

        def count_branches(n: Node, depth: int) -> bool:
            nonlocal complexity
            if n.type in ("if_statement", "while_statement", "for_statement",
                         "foreach_statement", "switch_section", "catch_clause",
                         "conditional_expression"):
                complexity += 1
            elif n.type == "binary_expression":
                # Count logical operators
                for child in n.children:
                    op_text = self.get_node_text(child, "")
                    if op_text in ("&&", "||"):
                        complexity += 1
            return True

        self.traverse(node, count_branches)
        return complexity
